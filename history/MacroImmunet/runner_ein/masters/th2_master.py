t# runner_ein/masters/th2_master.py
"""
Th2Master
---------
Master that scans naive CD4 T cells and issues intents that will be handled
by the Th2 per-cell decision module (runner_ein.percell.th2_percell).

Behavior:
 - Emit informational tcr_activation intent when a pMHC is detected.
 - If affinity >= affinity_threshold and use_percell=True -> emit percell_evaluate
   intent with percell_type 'Th2' (percell will handle differentiation logic).
 - If use_percell=False -> emit master-level differentiate intent (Effector_Th2).
 - Optionally emit proliferation intent.
"""

from typing import Any, Dict, List, Optional, Tuple
import traceback


class Th2Master:
    def __init__(self, space: Any, env: Any, params: Optional[Dict] = None):
        self.space = space
        self.env = env
        self.params = params or {}

        # config
        self.cell_types = self.params.get("cell_types", ["Naive_CD4"])
        self.affinity_threshold = float(self.params.get("affinity_threshold", 0.3))
        self.scan_radius = int(self.params.get("scan_radius", 1))
        self.use_percell = bool(self.params.get("use_percell", True))
        self.percell_type = self.params.get("percell_type", "Th2")
        self.percell_params = (self.params.get("percell", {}) or {}).get(self.percell_type, {})
        self.base_diff_prob = float(self.params.get("base_differentiation_prob", 0.2))
        self.enable_proliferation_intent = bool(self.params.get("enable_proliferation_intent", True))
        self.field_il12 = self.params.get("field_il12", "Field_IL12")
        self.field_il4 = self.params.get("field_il4", "Field_IL4")

    def emit_tick(self, n_intents: int = 0):
        try:
            if hasattr(self.env, "emit_event"):
                self.env.emit_event("master_tick", {"master": self.__class__.__name__, "n_intents": n_intents})
        except Exception:
            pass

    def tick(self) -> List[Dict]:
        intents: List[Dict] = []
        try:
            candidates = self._gather_cells()
            for c in candidates:
                coord = getattr(c, "coord", None)
                if coord is None:
                    continue

                pmhcs = self._collect_pmhc(coord)
                if not pmhcs:
                    continue

                best_pm, best_aff = self._best_affinity_for_cell(c, pmhcs)
                if best_pm is None or best_aff <= 0.0:
                    continue

                score = float(best_aff)

                # informational activation event
                intents.append({
                    "space": getattr(self.space, "id", None),
                    "coord": coord,
                    "action": "tcr_activation",
                    "cell_id": getattr(c, "id", None),
                    "best_affinity": score,
                    "pmhc_summary": best_pm,
                    "score": score,
                })

                # if affinity high enough, create percell evaluate intent (preferred)
                if score >= self.affinity_threshold:
                    if self.use_percell:
                        # suggest percell evaluation; orchestrator/scheduler will call percell
                        intent = {
                            "space": getattr(self.space, "id", None),
                            "coord": coord,
                            "action": "percell_evaluate",
                            "cell_id": getattr(c, "id", None),
                            "percell_type": self.percell_type,
                            "best_affinity": score,
                            "pmhc_summary": best_pm,
                            "score": score,
                            # attach any percell-specific params so scheduler/demo can read them
                            "params": self.percell_params or {},
                        }
                        intents.append(intent)
                    else:
                        # fallback to master-level differentiate
                        prob = self._compute_th2_probability(coord, c, best_pm, score)
                        intents.append({
                            "space": getattr(self.space, "id", None),
                            "coord": coord,
                            "action": "differentiate",
                            "cell_id": getattr(c, "id", None),
                            "target_state": "Effector_Th2",
                            "probability": prob,
                            "score": score,
                        })

                    # proliferation intent (optional)
                    if self.enable_proliferation_intent:
                        p = float(self.params.get("default_proliferation_prob", 0.5)) * min(1.0, score)
                        intents.append({
                            "space": getattr(self.space, "id", None),
                            "coord": coord,
                            "action": "proliferate",
                            "cell_id": getattr(c, "id", None),
                            "probability": p,
                            "score": score,
                        })

            self.emit_tick(len(intents))
        except Exception as e:
            if hasattr(self.env, "emit_event"):
                self.env.emit_event("master_error", {"master": self.__class__.__name__, "error": str(e), "trace": traceback.format_exc()})
        return intents

    def _gather_cells(self) -> List[Any]:
        out: List[Any] = []
        get_cells = getattr(self.space, "get_cells_of_type", None)
        if callable(get_cells):
            for t in self.cell_types:
                try:
                    found = get_cells(t)
                    if found:
                        out.extend(found)
                except Exception:
                    pass
        # fallback to scanning space.cells
        if not out and hasattr(self.space, "cells") and isinstance(self.space.cells, dict):
            for c in self.space.cells.values():
                t = getattr(c, "type", None) or getattr(c, "cell_type", None)
                if t and any(tt.lower() in str(t).lower() for tt in self.cell_types):
                    out.append(c)
                else:
                    cid = getattr(c, "id", "")
                    for tt in self.cell_types:
                        if tt.lower() in cid.lower():
                            out.append(c)
                            break
        return out

    def _collect_pmhc(self, coord: Tuple[int, int]) -> List[Dict]:
        collector = getattr(self.env, "collect_pMHC_near", None)
        if callable(collector):
            try:
                return collector(coord, radius=self.scan_radius)
            except Exception:
                pass

        # fallback to antigen density
        try:
            x, y = coord
            if getattr(self.space, "fields", None) and "Field_Antigen_Density" in self.space.fields:
                ag = float(self.space.fields["Field_Antigen_Density"][y][x])
                if ag >= float(self.params.get("antigen_pmhc_threshold", 1.0)):
                    return [{"pMHC_id": "pm_demo", "peptide_id": "PepX", "mhc_type": "MHC_II"}]
        except Exception:
            pass
        return []

    def _best_affinity_for_cell(self, cell: Any, pmhcs: List[Dict]) -> Tuple[Optional[Dict], float]:
        best = None
        best_score = 0.0
        comp = getattr(self.env, "compute_affinity", None)
        for pm in pmhcs:
            score = 0.0
            if callable(comp):
                try:
                    tcrs = getattr(cell, "tcr_repertoire", []) or []
                    tcr = tcrs[0] if tcrs else None
                    if tcr is not None:
                        score = float(comp(pm, tcr))
                except Exception:
                    score = 0.0
            else:
                pep = pm.get("peptide_id") if isinstance(pm, dict) else None
                tcrs = getattr(cell, "tcr_repertoire", []) or []
                for t in tcrs:
                    try:
                        if isinstance(t, dict) and pep in (t.get("specificity") or set()):
                            score = max(score, 0.85)
                    except Exception:
                        pass
            if score > best_score:
                best_score = score
                best = pm
        return best, best_score

    def _peek_field_at(self, coord: Tuple[int, int], field_name: str) -> Optional[float]:
        try:
            x, y = coord
            if hasattr(self.space, "fields") and field_name in self.space.fields:
                return float(self.space.fields[field_name][y][x])
        except Exception:
            pass
        return None

    def _compute_th2_probability(self, coord: Tuple[int, int], cell: Any, pm: Dict, affinity: float) -> float:
        # base + affinity boost, modulated by IL4/IL12
        p = float(self.base_diff_prob) + 0.5 * affinity
        il12 = self._peek_field_at(coord, self.field_il12) or 0.0
        il4 = self._peek_field_at(coord, self.field_il4) or 0.0
        # IL4 favors Th2: increase probability when IL4 > IL12
        bias = (il4 - il12)
        p = p * (1.0 + 0.5 * bias)
        p = max(0.0, min(1.0, p))
        return p

