# cell_master/selector.py
"""
Helpers to select candidate cells / labels from a Space region.

Extended: supports bbox / owner / capacity filters and backwards-compatible
parameter names (min_capacity, capacity_key). Also supports sample_count alias
and allows rng to be int seed or random.Random.
"""

from typing import List, Optional, Tuple, Any
from copy import deepcopy
import math
import random

Coord = Tuple[float, float]


def _distance(a: Coord, b: Coord) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _in_bbox(coord: Coord, bbox: Tuple[float, float, float, float]) -> bool:
    if coord is None:
        return False
    try:
        x, y = coord
        xmin, ymin, xmax, ymax = bbox
        return xmin <= x <= xmax and ymin <= y <= ymax
    except Exception:
        return False


def _try_float(v):
    try:
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        return float(str(v))
    except Exception:
        return None


def _extract_capacity(label: dict, preferred_key: Optional[str] = None) -> Optional[float]:
    """
    Try to extract a numeric 'capacity' or load-like value from label.
    If preferred_key is provided, try that key first (top-level then meta).
    Otherwise search a set of common keys.
    Return None if no numeric value found.
    """
    if not label:
        return None

    # helper to probe a key in both top-level and meta
    def probe_key(k):
        # top-level
        v = label.get(k)
        vf = _try_float(v)
        if vf is not None:
            return vf
        # meta
        meta = label.get("meta", {}) or {}
        v2 = meta.get(k)
        v2f = _try_float(v2)
        if v2f is not None:
            return v2f
        return None

    # if a preferred key is given, try it first
    if preferred_key:
        val = probe_key(preferred_key)
        if val is not None:
            return val

    # common keys to try (order of preference)
    common_keys = (
        "capacity",
        "max_capacity",
        "capacity_max",
        "antigen_load_capacity",
        "load_capacity",
        "antigen_load",
        "load",
        "max_load",
    )
    for k in common_keys:
        val = probe_key(k)
        if val is not None:
            return val

    # nothing found
    return None


def select_by_canonical(space: Any, region_id: str, canonical: str) -> List[dict]:
    """
    Return labels in region whose canonical classification equals `canonical`.
    Prefers space.get_labels_by_canonical if present.
    """
    if canonical is None:
        return []
    try:
        if hasattr(space, "get_labels_by_canonical"):
            return deepcopy(space.get_labels_by_canonical(region_id, canonical) or [])
    except Exception:
        pass

    out = []
    try:
        labels = space.get_labels(region_id)
    except Exception:
        labels = []
    for l in labels:
        c = None
        if isinstance(l.get("name", None), str) and l.get("name", None).upper() == canonical:
            c = canonical
        if c is None:
            if isinstance(l.get("meta", None), dict):
                c = l["meta"].get("canonical") or l["meta"].get("canonical_name")
        if c is None:
            name = l.get("name") or l.get("label") or ""
            if str(name).upper() == canonical:
                c = canonical
        if c == canonical:
            out.append(deepcopy(l))
    return out


def select_in_radius(space: Any, region_id: str, center: Coord, radius: float) -> List[dict]:
    """
    Return labels within radius of center.
    Prefers space.get_labels_in_radius if present (and trusts it).
    Falls back to scanning all labels with coord attribute.
    """
    if center is None or radius is None:
        return []

    try:
        if hasattr(space, "get_labels_in_radius"):
            return deepcopy(space.get_labels_in_radius(region_id, center, radius) or [])
    except Exception:
        pass

    out = []
    try:
        labels = space.get_labels(region_id)
    except Exception:
        labels = []

    for l in labels:
        c = l.get("coord") or l.get("position") or None
        if c is None:
            continue
        try:
            if _distance(center, c) <= float(radius):
                out.append(deepcopy(l))
        except Exception:
            continue
    return out


def _make_rng(rng_arg):
    """
    Normalize rng argument:
      - None -> new random.Random()
      - int -> random.Random(int)
      - random.Random -> pass-through
      - other -> try to use as-is or fall back to random.Random()
    """
    if rng_arg is None:
        return random.Random()
    if isinstance(rng_arg, random.Random):
        return rng_arg
    try:
        if isinstance(rng_arg, int):
            return random.Random(rng_arg)
        # sometimes tests pass a seed-like string/float; attempt to coerce
        if isinstance(rng_arg, (float, str)):
            return random.Random(rng_arg)
    except Exception:
        pass
    # fallback: any object with .sample/.shuffle might work; otherwise new RNG
    try:
        if hasattr(rng_arg, "sample") and hasattr(rng_arg, "shuffle"):
            return rng_arg
    except Exception:
        pass
    return random.Random()


def sample_list(candidates: List[Any], fraction: float = 1.0, max_select: Optional[int] = None,
                rng: Optional[random.Random] = None, sample_count: Optional[int] = None) -> List[Any]:
    """
    Sample a subset from candidates.
    - If sample_count is provided (int), treat it as exact requested count.
    - Otherwise:
      - fraction < 1.0 interpreted as fraction of len(candidates) (rounded to nearest int, min 0)
      - fraction == 1.0 interpreted as "all"
      - fraction > 1.0 interpreted as the requested count (rounded to int)
    - max_select caps the returned list length
    - deterministic when rng is a random.Random with fixed seed or rng is an int seed
    Always returns a list (possibly empty) of items (not deepcopied here).
    """
    if not candidates:
        return []

    rng_obj = _make_rng(rng)
    n = len(candidates)

    # sample_count takes precedence if provided
    k = None
    if sample_count is not None:
        try:
            k = int(sample_count)
        except Exception:
            k = None

    if k is None:
        try:
            f = float(fraction)
        except Exception:
            f = 1.0

        if f < 0.0:
            k = 0
        elif f < 1.0:
            k = int(round(n * f))
        else:
            if abs(f - 1.0) < 1e-9:
                k = n
            else:
                k = int(round(f))

    if k < 0:
        k = 0
    if k > n:
        k = n

    if max_select is not None:
        try:
            cap = int(max_select)
            if cap < k:
                k = max(0, cap)
        except Exception:
            pass

    if k <= 0:
        return []

    if k >= n:
        return list(candidates)

    try:
        chosen = rng_obj.sample(candidates, k)
    except Exception:
        tmp = list(candidates)
        rng_obj.shuffle(tmp)
        chosen = tmp[:k]
    return chosen


def select_targets(
    space: Any,
    region_id: str,
    target_cell_type: Optional[str] = None,
    coord: Optional[Coord] = None,
    radius: Optional[float] = None,
    sample_fraction: float = 1.0,
    max_select: Optional[int] = None,
    rng: Optional[Any] = None,
    bbox: Optional[Tuple[float, float, float, float]] = None,
    owner: Optional[str] = None,
    capacity_min: Optional[float] = None,
    capacity_max: Optional[float] = None,
    # backward-compatible aliases:
    min_capacity: Optional[float] = None,
    max_capacity: Optional[float] = None,
    capacity_key: Optional[str] = None,
    # explicit count alias
    sample_count: Optional[int] = None,
) -> List[dict]:
    """
    High-level selection used by cell masters.

    Accepts extra filters: bbox, owner, capacity_min / min_capacity, capacity_key, etc.

    Behavior:
     - If target_cell_type provided and space has get_labels_by_canonical, use that as base set.
     - If coord+radius provided, intersect base set with labels inside radius.
     - If bbox provided, further filter by bbox.
     - If owner provided, filter by label.owner equality.
     - If capacity filters provided, try to extract numeric capacity and filter.
     - Finally apply sample_fraction / max_select / sample_count via sample_list.
    Returns deep-copied list of label dicts.
    """
    rng_obj = _make_rng(rng)

    # respect aliasing: prefer explicit capacity_min/capacity_max, else aliases
    if capacity_min is None and min_capacity is not None:
        capacity_min = min_capacity
    if capacity_max is None and max_capacity is not None:
        capacity_max = max_capacity

    # Start with base candidate set according to type
    if target_cell_type:
        candidates = select_by_canonical(space, region_id, target_cell_type)
    else:
        try:
            candidates = deepcopy(space.get_labels(region_id) or [])
        except Exception:
            candidates = []

    # radius filter (circle)
    if coord is not None and radius is not None:
        try:
            inrad = select_in_radius(space, region_id, coord, radius)
            ids_inrad = {x.get("id") for x in inrad if x.get("id") is not None}
            newc = []
            for c in candidates:
                cid = c.get("id")
                ccoord = c.get("coord") or c.get("position")
                if cid is not None and cid in ids_inrad:
                    newc.append(c)
                else:
                    try:
                        if ccoord and _distance(ccoord, coord) <= radius:
                            newc.append(c)
                    except Exception:
                        continue
            candidates = newc
        except Exception:
            try:
                all_labels = deepcopy(space.get_labels(region_id) or [])
                candidates = [c for c in all_labels if c.get("coord") and _distance(c.get("coord"), coord) <= radius]
            except Exception:
                candidates = []

    # bbox filter (axis-aligned)
    if bbox is not None:
        try:
            candidates = [c for c in candidates if (c.get("coord") or c.get("position")) and _in_bbox((c.get("coord") or c.get("position")), bbox)]
        except Exception:
            try:
                all_labels = deepcopy(space.get_labels(region_id) or [])
                candidates = [c for c in all_labels if (c.get("coord") or c.get("position")) and _in_bbox((c.get("coord") or c.get("position")), bbox)]
            except Exception:
                candidates = []

    # owner filter
    if owner is not None:
        try:
            candidates = [c for c in candidates if c.get("owner") == owner]
        except Exception:
            pass

    # capacity filters (use capacity_key if provided)
    if capacity_min is not None or capacity_max is not None:
        filtered = []
        for c in candidates:
            cap = _extract_capacity(c, preferred_key=capacity_key)
            # if we couldn't extract numeric capacity, keep the candidate (do not drop silently)
            if cap is None:
                filtered.append(c)
                continue
            if capacity_min is not None and cap < float(capacity_min):
                continue
            if capacity_max is not None and cap > float(capacity_max):
                continue
            filtered.append(c)
        candidates = filtered

    # sampling (support explicit sample_count)
    sampled = sample_list(candidates, fraction=sample_fraction, max_select=max_select, rng=rng_obj, sample_count=sample_count)
    return [deepcopy(s) for s in sampled]


# compatibility wrapper
def select_candidates(
    space: Any,
    region_id: str,
    cell_type: Optional[str] = None,
    coord: Optional[Coord] = None,
    radius: Optional[float] = None,
    fraction: float = 1.0,
    max_select: Optional[int] = None,
    rng: Optional[Any] = None,
    bbox: Optional[Tuple[float, float, float, float]] = None,
    owner: Optional[str] = None,
    # legacy param names accepted here too
    min_capacity: Optional[float] = None,
    max_capacity: Optional[float] = None,
    capacity_key: Optional[str] = None,
    # accept new alias used by some callers/tests
    sample_fraction: Optional[float] = None,
    # explicit count alias
    sample_count: Optional[int] = None,
) -> List[dict]:
    """
    Backwards-compatible wrapper around select_targets.

    Accepts both `fraction` (legacy) and `sample_fraction` (new). If sample_fraction
    provided, it takes precedence. Also accepts `sample_count`.
    """
    # decide which sampling fraction to send to select_targets
    sf = sample_fraction if sample_fraction is not None else fraction

    return select_targets(
        space,
        region_id,
        target_cell_type=cell_type,
        coord=coord,
        radius=radius,
        sample_fraction=sf,
        max_select=max_select,
        rng=rng,
        bbox=bbox,
        owner=owner,
        min_capacity=min_capacity,
        max_capacity=max_capacity,
        capacity_key=capacity_key,
        sample_count=sample_count,
    )

