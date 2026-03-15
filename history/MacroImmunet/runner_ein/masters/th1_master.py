# runner_ein/masters/th1_master.py
"""
Th1Master — master-level naive CD4 -> Th1 biased decisions.
This master scans for naive CD4 cells (or uses provided cell_types) and
emits intents for tcr_activation, differentiate (master-level Th1 bias),
and optional proliferation intents.

Designed to be small and robust so it plugs into orchestrator_demo easily.
"""

from typing import Any, Dict, List, Optional, Tuple
import random

# If you have a common base, you can import it; otherwise this file is self-contained.
class Th1Master:
    def __init__(self, space: Any, env: Any, params: Optional[Dict] = None):
        self.space = space
        self.env = env
        self.params = params or {}
        self.cell_types = self.params.get("cell_types", ["Naive_CD4"])
        self.affinity_threshold = float(self.params.get("affinity_threshold", 0.3))
        self.scan_radius = int(self.params.get("scan_radius", 1))
        # base probability and IL12 weight
        self.base_diff_prob = float(self.params.get("base_differentiation_prob", 0.2))
        self.il12_weight = float(self.params.get("il12_weight", 0.5))
        self.enable_proliferation_intent = bool(self.params.get("enable_proliferation_intent", True))

    def emit_tick(self, n_intents: int = 0):
        try:
            if hasattr(self.env, "emit_event"):
                self.env.emit_event("master_tick", {"master": self.__class__.__name__, "n_intents": n_intents})
        except Exception:
            pass

    def tick(self) -> List[Dict]:
        intents: List[Dict] = []
        cells = self._gather_cells()
        for c in cells:
            coord = getattr(c, "coord", None)
            if coord is None:
                continue

            pmhcs = self._collect_pmhc(coord)
            if not pmhcs:
                continue

            best_pm, best_aff = self._best_affinity_for_cell(c, pmhcs)
            if best_pm is None:
                continue

            score = float(best_aff)
            intents.append({
                "space": getattr(self.space, "id", None),
                "coord": coord,
                "action": "tcr_activation",
                "cell_id": getattr(c, "id", None),
                "best_affinity": score,
                "pmhc_summary": best_pm,
                "score": score,
            })

            if score >= self.affinity_threshold:
                # master-level Th1 biased differentiation probability
                il12 = self._peek_field_at(coord, "Field_IL12") or 0.0
                # compute prob = base + scaling*affinity + il12 influence
                prob = self.base_diff_prob + 0.6 * score + self.il12_weight * (il12 / (1.0 + il12))
                prob = max(0.0, min(1.0, prob))

                intents.append({
                    "space": getattr(self.space, "id", None),
                    "coord": coord,
                    "action": "differentiate",
                    "cell_id": getattr(c, "id", None),
                    "target_state": "Effector_Th1",
                    "probability": prob,
                    "score": score,
                })

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
        return intents

    # --- helpers (similar to NaiveTCellMaster heuristics) ---
    def _gather_cells(self):
        out = []
        get_cells = getattr(self.space, "get_cells_of_type", None)
        if callable(get_cells):
            for t in self.cell_types:
                try:
                    found = get_cells(t)
                    if found:
                        out.extend(found)
                except Exception:
                    pass
        if not out and hasattr(self.space, "cells") and isinstance(self.space.cells, dict):
            for c in self.space.cells.values():
                t = getattr(c, "type", None) or getattr(c, "cell_type", None)
                if t and any(tt in str(t) for tt in self.cell_types):
                    out.append(c)
                else:
                    cid = getattr(c, "id", "")
                    for tt in self.cell_types:
                        if tt.lower() in cid.lower():
                            out.append(c)
                            break
        return out

    def _collect_pmhc(self, coord: Tuple[int,int]) -> List[Dict]:
        collector = getattr(self.env, "collect_pMHC_near", None)
        if callable(collector):
            try:
                return collector(coord, radius=self.scan_radius)
            except Exception:
                pass
        try:
            x,y = coord
            ag = 0.0
            if self.space.fields and "Field_Antigen_Density" in self.space.fields:
                ag = float(self.space.fields["Field_Antigen_Density"][y][x])
            if ag >= float(self.params.get("antigen_pmhc_threshold", 1.0)):
                return [{"pMHC_id":"pm_demo","peptide_id":"PepX","mhc_type":"MHC_II"}]
        except Exception:
            pass
        return []

    def _best_affinity_for_cell(self, cell, pmhcs):
        comp = getattr(self.env, "compute_affinity", None)
        best = None
        best_score = 0.0
        for pm in pmhcs:
            score = 0.0
            if callable(comp):
                try:
                    tcrs = getattr(cell, "tcr_repertoire", []) or []
                    tcr = tcrs[0] if tcrs else None
                    score = float(comp(pm, tcr)) if tcr is not None else 0.0
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

    def _peek_field_at(self, coord, field_name):
        try:
            x,y = coord
            if hasattr(self.space, "fields") and field_name in self.space.fields:
                return float(self.space.fields[field_name][y][x])
        except Exception:
            pass
        return None

