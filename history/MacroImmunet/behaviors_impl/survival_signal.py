# behaviors_impl/survival_signal.py
import math
from typing import Any, Dict, List

def survival_signal_v1(cell, env, params=None, payload=None, **kw) -> List[Dict]:
    """
    Read Field_IL2 and Field_IL15 (using read_field_fn env.read_field),
    update cell.survival_score with exponential decay integrator and recompute apoptosis_threshold.
    Emit event 'survival_boosted'.
    """
    params = params or {}
    half_life = float(params.get("half_life_of_signal_effect_ticks", 240))
    boost_factor = float(params.get("boost_factor", 0.5))
    max_survival = float(params.get("max_survival_score", 10.0))
    min_apoptosis_threshold = float(params.get("min_apoptosis_threshold", 0.01))

    # read functions
    read_field = getattr(env, "read_field", None)
    coord = getattr(cell, "coord", None)

    il2 = 0.0
    il15 = 0.0
    try:
        if callable(read_field):
            il2 = float(read_field(coord, "Field_IL2") or 0.0)
            il15 = float(read_field(coord, "Field_IL15") or 0.0)
    except Exception:
        il2 = 0.0
        il15 = 0.0

    aggregated = il2 + il15

    # init survival_score
    try:
        cur = float(getattr(cell, "survival_score", 0.0) or 0.0)
    except Exception:
        cur = 0.0

    decay = math.exp(-1.0 / max(1.0, half_life))
    new_score = cur * decay + boost_factor * aggregated
    if new_score > max_survival:
        new_score = max_survival

    # write back
    try:
        cell.survival_score = new_score
    except Exception:
        pass

    # compute apoptosis threshold
    base_thresh = float(getattr(cell, "base_apoptosis_threshold", getattr(cell, "apoptosis_threshold", 0.1) or 0.1))
    modifier = min(0.9, new_score)
    apoptosis_threshold = max(min_apoptosis_threshold, base_thresh * (1.0 - modifier))
    try:
        cell.apoptosis_threshold = apoptosis_threshold
    except Exception:
        pass

    # emit event
    payload = {"cell_id": getattr(cell, "id", None), "survival_score": new_score, "apoptosis_threshold": apoptosis_threshold, "tick": getattr(env, "tick", None)}
    try:
        if hasattr(env, "emit_event"):
            env.emit_event("survival_boosted", payload)
    except Exception:
        pass

    # return actions for compatibility
    return [{"name": "survival_boosted", "payload": payload}]

