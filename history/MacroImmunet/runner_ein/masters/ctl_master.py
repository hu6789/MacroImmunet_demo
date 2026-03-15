# runner_ein/masters/ctl_master.py
"""
CTLMaster: scan tissue / lymph node for Naive_CD8 cells and produce intents to:
 - report TCR activations (tcr_activation)
 - trigger differentiation to Effector_CTL when affinity + help signals permit
 - optionally request percell evaluation (percell_evaluate) for CTL-specific logic
 - produce proliferation intents as part of activation program

Expectations / adapters:
 - env.collect_pMHC_near(coord, radius) -> list of pMHC dicts (mhc_type, peptide_id, ...)
 - env.compute_affinity(pm, tcr) -> float affinity (0..1)
 - space.get_cells_of_type(name) or space.cells to enumerate cells
 - space.fields contains cytokine fields (Field_IL12, Field_IFNg) which are 2D lists
 - env.emit_event(name, payload) exists for observability
"""
from typing import Any, Dict, List

class CTLMaster:
    def __init__(self, space: Any, env: Any, params: Dict = None):
        self.space = space
        self.env = env
        self.params = params or {}
        self.mode = self.params.get("mode", "survey")

    def _local_help_signal(self, coord, radius=1):
        """Estimate helper cytokine presence (IL-12 / IFNg) around coord using space.fields.
        Returns a simple boolean or a continuous score (sum normalized) depending on params.
        """
        try:
            x0, y0 = coord
        except Exception:
            return 0.0
        score = 0.0
        fields = getattr(self.space, "fields", {}) or {}
        il12 = fields.get("Field_IL12")
        ifng = fields.get("Field_IFNg")
        # sample small neighborhood (square) of radius
        r = int(max(0, radius))
        h = len(il12) if il12 else (len(ifng) if ifng else 0)
        w = len(il12[0]) if il12 and h else (len(ifng[0]) if ifng and h else 0)
        for dy in range(-r, r+1):
            for dx in range(-r, r+1):
                x = x0 + dx
                y = y0 + dy
                if x < 0 or y < 0:
                    continue
                if h and y >= h:
                    continue
                if w and x >= w:
                    continue
                try:
                    if il12:
                        score += float(il12[y][x])
                except Exception:
                    pass
                try:
                    if ifng:
                        score += float(ifng[y][x]) * 0.8
                except Exception:
                    pass
        # normalize by small factor to keep magnitude sensible
        norm = float(self.params.get("help_norm_factor", 10.0))
        return score / norm if norm > 0 else score

    def tick(self) -> List[Dict]:
        intents: List[Dict] = []

        # find Naive CD8 cells: try helper then fallback
        naive_cells = []
        try:
            if hasattr(self.space, "get_cells_of_type"):
                naive_cells = self.space.get_cells_of_type("Naive_CD8") or []
        except Exception:
            naive_cells = []

        if not naive_cells:
            try:
                for c in getattr(self.space, "cells", {}).values():
                    t = getattr(c, "type", None) or getattr(c, "cell_type", None) or (getattr(c, "meta", {}) or {}).get("type")
                    if t and "naive" in str(t).lower() and "cd8" in str(t).lower():
                        naive_cells.append(c)
            except Exception:
                pass

        # parameters
        affinity_threshold = float(self.params.get("affinity_threshold", 0.4))   # CTL often requires higher affinity
        help_threshold = float(self.params.get("help_score_threshold", 0.2))     # required help signal (normalized)
        prefer_percell = bool(self.params.get("prefer_percell", False))         # default: master handles CTL diffs
        percell_type_default = self.params.get("percell_type_default", "CTL")
        proliferation_prob = float(self.params.get("proliferation_prob", 0.6))
        max_peeks = int(self.params.get("max_peeks_per_cell", 4))
        scan_radius = int(self.params.get("scan_radius", 1))

        for cell in naive_cells:
            try:
                coord = getattr(cell, "coord", None)
                if coord is None:
                    continue

                # collect pMHC candidates (expect MHC_I presenters)
                pMHCs = []
                collect_fn = getattr(self.env, "collect_pMHC_near", None)
                if callable(collect_fn):
                    try:
                        pMHCs = collect_fn(coord, radius=scan_radius) or []
                    except Exception:
                        pMHCs = []

                best_aff = 0.0
                best_pm = None
                checked = 0
                repertoire = getattr(cell, "tcr_repertoire", []) or []
                for pm in pMHCs:
                    # ensure MHC_I preference for CTL
                    pm_mhc = pm.get("mhc_type") if isinstance(pm, dict) else None
                    if pm_mhc and "mhc_i" not in str(pm_mhc).lower():
                        # skip non MHC I pMHC for CD8
                        continue
                    for tcr in repertoire:
                        affinity_fn = getattr(self.env, "compute_affinity", None)
                        try:
                            aff = affinity_fn(pm, tcr) if callable(affinity_fn) else 0.0
                        except Exception:
                            aff = 0.0
                        if aff > best_aff:
                            best_aff = aff
                            best_pm = pm
                        checked += 1
                        if checked >= max_peeks:
                            break
                    if checked >= max_peeks:
                        break

                # compute help signal around the cell
                help_score = self._local_help_signal(coord, radius=scan_radius)

                # produce intents when thresholds satisfied
                if best_aff >= 0.0:  # always emit tcr_activation if any pMHC seen (affinity may be 0)
                    intents.append({
                        "space": getattr(self.space, "id", None),
                        "coord": coord,
                        "action": "tcr_activation",
                        "cell_id": getattr(cell, "id", None),
                        "best_affinity": best_aff,
                        "pmhc_summary": best_pm,
                        "score": best_aff
                    })

                # Decide differentiation only if affinity + help pass thresholds
                if best_aff >= affinity_threshold and help_score >= help_threshold:
                    # if we want percell-CTl evaluation, schedule that instead of immediate differentiate
                    if prefer_percell:
                        intents.append({
                            "space": getattr(self.space, "id", None),
                            "coord": coord,
                            "action": "percell_evaluate",
                            "cell_id": getattr(cell, "id", None),
                            "percell_type": percell_type_default,
                            "best_affinity": best_aff,
                            "pmhc_summary": best_pm,
                            "help_score": help_score,
                            "score": best_aff
                        })
                    else:
                        # master-level differentiate + proliferate
                        intents.append({
                            "space": getattr(self.space, "id", None),
                            "coord": coord,
                            "action": "differentiate",
                            "cell_id": getattr(cell, "id", None),
                            "target_state": "Effector_CTL",
                            "probability": float(self.params.get("differentiation_prob", 0.8)),
                            "reason": {"best_affinity": best_aff, "help_score": help_score},
                            "score": best_aff
                        })
                        intents.append({
                            "space": getattr(self.space, "id", None),
                            "coord": coord,
                            "action": "proliferate",
                            "cell_id": getattr(cell, "id", None),
                            "probability": proliferation_prob,
                            "score": best_aff
                        })

            except Exception:
                # fail-fast per cell avoided: continue scanning next cell
                continue

        # observability
        try:
            if hasattr(self.env, "emit_event"):
                self.env.emit_event("master_tick", {"master": "CTLMaster", "n_intents": len(intents)})
        except Exception:
            pass

        return intents

