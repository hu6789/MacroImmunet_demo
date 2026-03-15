# runner_ein/masters/naive_tcell_master.py
"""
NaiveTCellMaster
----------------
Lightweight Naive T cell master for runner_ein demo.

Responsibilities:
- scan space for pMHC / antigen-presenting hotspots (via env.collect_pMHC_near or local field)
- for nearby naive T cells, compute simple affinity (via env.compute_affinity) and emit intents:
  - tcr_activation (informational)
  - percell_evaluate (if percell enabled) -> lets percell decide (Th2, CTL, ...)
  - differentiate (master-level fallback decision)
  - proliferate (probabilistic intent)

Design:
- defensive / robust when helper functions are missing from env
- small and focused to plug into orchestrator_demo
"""
from typing import Any, Dict, List, Optional, Tuple
import math
import random


class BaseMaster:
    def __init__(self, space: Any, env: Any, params: Optional[Dict] = None):
        self.space = space
        self.env = env
        self.params = params or {}
        # mode can be 'idle','survey','activated','infection'
        self.mode = self.params.get("mode", "survey")

    def emit_tick(self, n_intents: int = 0):
        try:
            if hasattr(self.env, "emit_event"):
                self.env.emit_event("master_tick", {"master": self.__class__.__name__, "n_intents": n_intents})
        except Exception:
            pass


class NaiveTCellMaster(BaseMaster):
    """Master that handles naive T cell scanning + producing intents.

    Params (defaults):
      - cell_types: list of type names this master should manage (default: ['Naive_CD4','Naive_CD8'])
      - affinity_threshold: float (0..1) minimal affinity to consider activation
      - percell_precedence: bool whether percell decision should override master-level differentiate
      - enable_proliferation_intent: bool
      - percell_type_map: dict mapping "Naive_CD4"->"Th2" etc (used to suggest percell type)
      - scan_radius: int radius for pMHC collection (if env supports it)
    """

    def __init__(self, space: Any, env: Any, params: Optional[Dict] = None):
        super().__init__(space, env, params)
        self.cell_types = self.params.get("cell_types", ["Naive_CD4", "Naive_CD8"])
        self.affinity_threshold = float(self.params.get("affinity_threshold", 0.3))
        self.percell_precedence = bool(self.params.get("percell_precedence", True))
        self.enable_proliferation_intent = bool(self.params.get("enable_proliferation_intent", True))
        self.scan_radius = int(self.params.get("scan_radius", 1))
        # mapping to default percell suggestion
        self.percell_type_map = self.params.get("percell_type_map", {"Naive_CD4": "Th2", "Naive_CD8": "CTL"})

    def tick(self) -> List[Dict]:
        """Perform a scan and produce intents.

        Returns list of intent dicts.
        """
        intents: List[Dict] = []

        # collect candidate naive cells from space
        naive_cells = self._gather_cells()

        # for each naive cell, examine local pMHC and compute affinity
        for c in naive_cells:
            coord = getattr(c, "coord", None)
            if coord is None:
                continue

            pmhcs = self._collect_pmhc(coord)
            if not pmhcs:
                continue

            # evaluate pMHCs for this cell repertoire
            best_pm, best_aff = self._best_affinity_for_cell(c, pmhcs)
            if best_pm is None:
                # no match
                continue

            score = float(best_aff)

            # informational tcr_activation intent
            intents.append({
                "space": getattr(self.space, "id", None),
                "coord": coord,
                "action": "tcr_activation",
                "cell_id": getattr(c, "id", None),
                "best_affinity": score,
                "pmhc_summary": best_pm,
                "score": score,
            })

            # if affinity passes threshold, create further intents
            if score >= self.affinity_threshold:
                # percell evaluate intent (if configured)
                percell_type = self._suggest_percell_type_for_cell(c, best_pm)
                if percell_type:
                    intents.append({
                        "space": getattr(self.space, "id", None),
                        "coord": coord,
                        "action": "percell_evaluate",
                        "cell_id": getattr(c, "id", None),
                        "percell_type": percell_type,
                        "best_affinity": score,
                        "pmhc_summary": best_pm,
                        "score": score,
                    })

                # master-level differentiate intent (fallback)
                prob = self._compute_differentiation_probability(coord, c, best_pm, score)
                target = self._suggest_master_target(c, best_pm, score)

                intents.append({
                    "space": getattr(self.space, "id", None),
                    "coord": coord,
                    "action": "differentiate",
                    "cell_id": getattr(c, "id", None),
                    "target_state": target,
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

        # notify
        self.emit_tick(len(intents))
        return intents

    def _gather_cells(self) -> List[Any]:
        out = []
        # prefer space.get_cells_of_type if present
        get_cells = getattr(self.space, "get_cells_of_type", None)
        if callable(get_cells):
            for t in self.cell_types:
                try:
                    found = get_cells(t)
                    if found:
                        out.extend(found)
                except Exception:
                    pass
        # fallback to scanning space.cells dict
        if not out and hasattr(self.space, "cells") and isinstance(self.space.cells, dict):
            for c in self.space.cells.values():
                t = getattr(c, "type", None) or getattr(c, "cell_type", None)
                if t and any(tt in str(t) for tt in self.cell_types):
                    out.append(c)
                else:
                    # heuristics: id contains naive token
                    cid = getattr(c, "id", "")
                    for tt in self.cell_types:
                        if tt.lower() in cid.lower():
                            out.append(c)
                            break
        return out

    def _collect_pmhc(self, coord: Tuple[int, int]) -> List[Dict]:
        # prefer env.collect_pMHC_near
        collector = getattr(self.env, "collect_pMHC_near", None)
        if callable(collector):
            try:
                return collector(coord, radius=self.scan_radius)
            except Exception:
                pass

        # fallback: inspect nearby antigen field (Field_Antigen_Density)
        try:
            x, y = coord
            ag = 0.0
            if self.space.fields and "Field_Antigen_Density" in self.space.fields:
                ag = float(self.space.fields["Field_Antigen_Density"][y][x])
            if ag >= float(self.params.get("antigen_pmhc_threshold", 1.0)):
                return [{"pMHC_id": "pm_demo", "peptide_id": "PepX", "mhc_type": "MHC_II"}]
        except Exception:
            pass
        return []

    def _best_affinity_for_cell(self, cell: Any, pmhcs: List[Dict]) -> Tuple[Optional[Dict], float]:
        # try env.compute_affinity
        best = None
        best_score = 0.0
        comp = getattr(self.env, "compute_affinity", None)
        tcrs = getattr(cell, "tcr_repertoire", []) or []
        tcr = tcrs[0] if tcrs else None
        for pm in pmhcs:
            score = 0.0
            if callable(comp):
                try:
                    score = float(comp(pm, tcr)) if tcr is not None else 0.0
                except Exception:
                    score = 0.0
            else:
                # fallback: match peptide string if present
                pep = pm.get("peptide_id") if isinstance(pm, dict) else None
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

    def _suggest_percell_type_for_cell(self, cell: Any, pm: Dict) -> Optional[str]:
        # by default map Naive_CD4 -> Th2 and Naive_CD8 -> CTL
        t = getattr(cell, "type", None) or getattr(cell, "cell_type", None) or ""
        for k, v in self.percell_type_map.items():
            if k.lower() in str(t).lower():
                return v
        cid = getattr(cell, "id", "") or ""
        if "naive_cd4" in cid.lower() or "cd4" in str(t).lower():
            return "Th2"
        if "naive_cd8" in cid.lower() or "cd8" in str(t).lower():
            return "CTL"
        return None

    def _suggest_master_target(self, cell: Any, pm: Dict, affinity: float) -> str:
        # CD8 -> CTL
        t = getattr(cell, "type", None) or getattr(cell, "cell_type", None) or "Naive"
        if "cd8" in str(t).lower():
            return "Effector_CTL"

        # sense local IL12/IL4 fields if present
        il12 = self._peek_field_at(coord=getattr(cell, "coord", (0, 0)), field_name="Field_IL12")
        il4 = self._peek_field_at(coord=getattr(cell, "coord", (0, 0)), field_name="Field_IL4")
        # simple rule: IL12 dominates -> Th1; IL4 dominates -> Th2; else decide by affinity
        if il12 is not None and il4 is not None:
            if il12 > il4 * 1.2:
                return "Effector_Th1"
            if il4 > il12 * 1.2:
                return "Effector_Th2"
        # fallback: high affinity -> Th1 else Th2
        if affinity >= 0.6:
            return "Effector_Th1"
        return "Effector_Th2"

    def _compute_differentiation_probability(self, coord: Tuple[int, int], cell: Any, pm: Dict, affinity: float) -> float:
        base = float(self.params.get("base_differentiation_prob", 0.2))
        p = base + 0.6 * affinity
        il12 = self._peek_field_at(coord=coord, field_name="Field_IL12") or 0.0
        il4 = self._peek_field_at(coord=coord, field_name="Field_IL4") or 0.0
        p = p * (1.0 + 0.5 * (il12 - il4))
        p = max(0.0, min(1.0, p))
        return p

    def _peek_field_at(self, coord: Tuple[int, int], field_name: str) -> Optional[float]:
        try:
            x, y = coord
            if hasattr(self.space, "fields") and field_name in self.space.fields:
                return float(self.space.fields[field_name][y][x])
        except Exception:
            pass
        return None


# End of file

