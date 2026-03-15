# runner_ein/masters/tcell_master.py
"""
TCellMaster: scan for pMHC near T cells, compute affinities, and emit intents.

Intents produced (examples):
 - {"action":"tcr_activation", "space":..., "coord":(x,y), "cell_id":..., "best_affinity":0.85, "pmhc_summary":{...}, "score":0.85}
 - {"action":"percell_evaluate", "space":..., "coord":(x,y), "cell_id":..., "percell_type":"Th2", "best_affinity":..., "pmhc_summary":{...}, "score":...}
 - {"action":"differentiate", "space":..., "coord":(x,y), "cell_id":..., "target_state":"Effector_Th1", "probability":0.9, "score":...}
 - {"action":"proliferate", "space":..., "coord":(x,y), "cell_id":..., "probability":0.5, "score":...}

This master is intentionally lightweight: it does not mutate cells; it emits intents
that the orchestrator/runner can handle.
"""
from typing import List, Dict, Any

class TCellMaster:
    def __init__(self, space, env, params=None):
        self.space = space
        self.env = env
        self.params = params or {}
        # runtime mode (can be "idle", "surveillance", "activated")
        self.mode = self.params.get("mode", "surveillance")

    def tick(self) -> List[Dict[str, Any]]:
        """
        Perform a scan pass and return a list of intents.
        """
        intents = []
        cell_types = self.params.get("cell_types", ["Naive_CD4", "Naive_CD8"])
        affinity_threshold = float(self.params.get("affinity_threshold", 0.3))
        scan_radius = int(self.params.get("scan_radius", 1))
        enable_procell = bool(self.params.get("use_percell", True))
        enable_prolif = bool(self.params.get("enable_proliferation_intent", True))

        all_cells = []
        # gather candidate cells from space helper
        for ct in cell_types:
            try:
                got = self.space.get_cells_of_type(ct)
            except Exception:
                got = []
            if got:
                all_cells.extend(got)

        # iterate cells and evaluate local pMHCs
        for cell in all_cells:
            coord = getattr(cell, "coord", None) or getattr(cell, "position", None)
            if coord is None:
                continue

            collect_fn = getattr(self.env, "collect_pMHC_near", None)
            compute_aff = getattr(self.env, "compute_affinity", None)

            pmhcs = []
            try:
                if callable(collect_fn):
                    pmhcs = collect_fn(coord, radius=scan_radius) or []
            except Exception:
                pmhcs = []

            best_aff = 0.0
            best_summary = None

            # cell may carry a tcr_repertoire attribute (list of clonotypes)
            tcrs = getattr(cell, "tcr_repertoire", []) or []

            for pm in pmhcs:
                # compare against repertoire
                for tcr in tcrs or [None]:
                    aff = 0.0
                    try:
                        if callable(compute_aff):
                            try:
                                aff = float(compute_aff(pm, tcr))
                            except TypeError:
                                # try other common signature
                                try:
                                    aff = float(compute_aff(tcr, pm))
                                except Exception:
                                    aff = 0.0
                            except Exception:
                                aff = 0.0
                        else:
                            # fallback heuristic
                            pid = pm.get("peptide_id") if isinstance(pm, dict) else None
                            t_match = None
                            if isinstance(tcr, dict):
                                # support field name variants
                                t_match = tcr.get("target_peptide") or next(iter(tcr.get("specificity", [])), None)
                            aff = 1.0 if (t_match and pid and pid == t_match) else 0.0
                    except Exception:
                        aff = 0.0

                    if aff > best_aff:
                        best_aff = float(aff)
                        best_summary = {
                            "pMHC_id": pm.get("pMHC_id"),
                            "peptide_id": pm.get("peptide_id"),
                            "mhc_type": pm.get("mhc_type"),
                        }
                        # small optimization: break if very high
                        if best_aff >= float(self.params.get("early_stop_threshold", 0.95)):
                            break
                if best_aff >= float(self.params.get("early_stop_threshold", 0.95)):
                    break

            # if nothing passes minimal threshold, skip generation of activation intents
            if best_aff < affinity_threshold:
                # still optionally record a weak "scan" intent for observability
                continue

            score = best_aff
            # emit tcr_activation intent
            intents.append({
                "space": getattr(self.space, "id", None),
                "coord": coord,
                "action": "tcr_activation",
                "cell_id": getattr(cell, "id", None),
                "best_affinity": best_aff,
                "pmhc_summary": best_summary,
                "score": score
            })

            # optionally emit percell evaluation intent (hand off to percell logic like Th2)
            if enable_procell:
                percell_type = None
                # heuristics: if cell.cell_type exists, use mapping (Naive_CD4 -> Th2 candidate)
                ctype = getattr(cell, "type", None) or getattr(cell, "cell_type", None) or ""
                if "cd4" in str(ctype).lower():
                    percell_type = "Th2" if self.params.get("prefer_th2_percell", True) else "Th1"
                elif "cd8" in str(ctype).lower():
                    percell_type = "CTL"
                else:
                    percell_type = self.params.get("default_percell_type", "Th2")

                intents.append({
                    "space": getattr(self.space, "id", None),
                    "coord": coord,
                    "action": "percell_evaluate",
                    "cell_id": getattr(cell, "id", None),
                    "percell_type": percell_type,
                    "best_affinity": best_aff,
                    "pmhc_summary": best_summary,
                    "score": score
                })

            # optionally emit a differentiate intent (master-level decision or suggestion)
            # this is a lightweight intent; detailed rules should be enforced by differentiate behavior.
            # choose a plausible target based on MHC type
            mhc = (best_summary or {}).get("mhc_type", "") if best_summary else ""
            target_state = None
            if "MHC_I" in str(mhc) or "I" == str(mhc):
                target_state = "Effector_CTL"
            else:
                # assume CD4 -> Th1/Th2 decision could be driven by cytokines (env fields)
                # here we preferentially suggest Th1 if IL12 is present above threshold
                il12_field = getattr(self.space, "fields", {}).get("Field_IL12", None)
                il12_val = 0.0
                if il12_field:
                    x,y = coord
                    try:
                        il12_val = float(il12_field[y][x])
                    except Exception:
                        il12_val = 0.0
                if il12_val >= float(self.params.get("il12_threshold", 0.2)):
                    target_state = "Effector_Th1"
                else:
                    target_state = "Effector_Th2"

            intents.append({
                "space": getattr(self.space, "id", None),
                "coord": coord,
                "action": "differentiate",
                "cell_id": getattr(cell, "id", None),
                "target_state": target_state,
                "probability": float(self.params.get("differentiation_prob", 0.8)),
                "score": score
            })

            # optionally generate proliferation intent
            if enable_prolif:
                prob = float(self.params.get("proliferation_prob_base", 0.5)) * min(1.0, best_aff * 1.0)
                intents.append({
                    "space": getattr(self.space, "id", None),
                    "coord": coord,
                    "action": "proliferate",
                    "cell_id": getattr(cell, "id", None),
                    "probability": prob,
                    "score": score
                })

        # emit a summarized event for observability
        try:
            if hasattr(self.env, "emit_event"):
                self.env.emit_event("master_tick", {"master": "TCellMaster", "n_intents": len(intents)})
        except Exception:
            pass

        return intents

