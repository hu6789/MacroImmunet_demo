"""
Tiny helpers to emulate the older shared.space_query API that tests/masters
sometimes import. Kept minimal and deterministic for tests.
"""
import math
from typing import List, Dict, Tuple, Optional

Coord = Tuple[float, float]

def distance(a: Coord, b: Coord) -> float:
    try:
        return math.hypot(a[0]-b[0], a[1]-b[1])
    except Exception:
        return float('inf')

def get_neighbor_cells(summary: Dict, coord: Coord, radius: float=1.5) -> List[Dict]:
    """
    Accepts summary (may contain 'cells' or 'neighbors' keys).
    Returns list of neighbor dicts whose 'coord' is within radius.
    """
    candidates = []
    for k in ("neighbors", "nearby_cells", "neighbor_cells", "cells"):
        if k in summary and isinstance(summary[k], list):
            candidates = summary[k]
            break
    out = []
    for c in candidates:
        cc = c.get("coord") or c.get("position")
        if cc is None:
            continue
        try:
            if distance(coord, cc) <= float(radius):
                out.append(c)
        except Exception:
            continue
    return out
