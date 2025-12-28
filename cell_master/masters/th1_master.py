# cell_master/masters/th1_master.py
"""
Simple Th1 master for demo/tests.

Responsibilities (demo):
 - respond to pMHC hotspots by moving toward them (Intent_move_to)
 - when 'activated' (via cell_meta flag), secrete helper cytokines (e.g. IFN-gamma)
 - when nearby B cells exist, move toward them to provide help
 - otherwise random movement

This implementation is intentionally small and defensive:
 - it prefers explicit Intent classes if available (Intent_secrete), otherwise
   constructs a generic Intent via the Intent constructor.
 - it accepts different keys for neighbor lists (compat with summary shapes).
"""
from typing import List, Optional, Dict, Any
from cell_master.base_master import BaseMaster

# try to import concrete intent types; fall back to Intent if some names missing
from cell_master.intents import Intent, Intent_move_to, Intent_random_move  # type: ignore

# optional specific secrete intent; not all codebases provide it
try:
    from cell_master.intents import Intent_secrete  # type: ignore
except Exception:
    Intent_secrete = None  # type: ignore

_NEIGHBOR_KEYS = ("neighbors", "nearby_cells", "neighbor_cells", "cells")


class Th1Master(BaseMaster):
    """
    Minimal Th1 master.

    step(coord, summary, cell_meta, rng) -> List[Intent-like objects]

    Logic:
     - If pMHC hotspot present -> move_to(hotspot)
     - If cell_meta indicates activation -> secrete cytokine intent
     - If B cells nearby -> move_to(nearest B cell coord)
     - Else -> random move
    """
    def __init__(self, cell_type: str = "Th1"):
        # BaseMaster compatibility: pass only cell_type; behaviour_registry not used here
        try:
            super().__init__(cell_type)
        except TypeError:
            # some BaseMaster variants require (behaviour_registry) arg; tolerate both:
            super().__init__(cell_type, None)  # type: ignore
        # default parameters
        self.help_radius = 2.0

    def step(self, coord: Optional[tuple], summary: Dict[str, Any], cell_meta: Dict[str, Any], rng) -> List[Any]:
        # 1) pMHC hotspot guidance
        if summary and "pMHC_hotspot" in summary and summary.get("pMHC_hotspot") is not None:
            hotspot = summary["pMHC_hotspot"]
            return [Intent_move_to(coord=coord, target=hotspot)]

        # 2) If activated -> secrete cytokine
        activated_keys = ("activated", "th1_activated", "active")
        for k in activated_keys:
            if cell_meta and cell_meta.get(k):
                return [self._make_secrete_intent(coord=coord, payload={"cytokine": "IFN-gamma", "amount": 1.0})]

        # 3) If there are nearby B cells, move to the nearest one to help
        neighbors = None
        for k in _NEIGHBOR_KEYS:
            if summary and k in summary and isinstance(summary[k], list):
                neighbors = summary[k]
                break

        if neighbors:
            # find B cells with coord
            b_cells = [c for c in neighbors if (c.get("type") in ("B", "B_cell", "Bcell") or c.get("canonical", "") == "B") and c.get("coord") is not None]
            if b_cells:
                # choose nearest B cell (Euclidean)
                b_cells.sort(key=lambda x: ((x["coord"][0] - (coord or (0, 0))[0])**2 + (x["coord"][1] - (coord or (0,0))[1])**2))
                target = b_cells[0]
                return [Intent_move_to(coord=coord, target=target.get("coord"))]

        # 4) fallback: random move
        return [Intent_random_move(coord=coord)]

    def _make_secrete_intent(self, coord: Optional[tuple], payload: Dict[str, Any]):
        """
        Make a secrete intent. Prefer concrete Intent_secrete if available,
        otherwise use generic Intent(name='secrete', payload=...).
        """
        if Intent_secrete is not None:
            try:
                return Intent_secrete(coord=coord, payload=payload)
            except Exception:
                # fallback to generic
                pass
        # generic Intent: name 'secrete' keeps semantics clear
        try:
            return Intent(name="secrete", payload=payload, coord=coord)
        except Exception:
            # last resort: dict-like intent (Executor often accepts this)
            return {"name": "secrete", "payload": payload, "coord": coord}


# export
__all__ = ["Th1Master"]

