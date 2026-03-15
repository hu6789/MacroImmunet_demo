# behaviors_impl/regulation.py
from typing import Any, Dict, List

def up_down_regulate_v1(cell, env, params=None, payload=None, **kw) -> List[Dict]:
    """
    Apply a fold change to an internal variable (cell.internal or attribute).
    If env.schedule_task exists, schedule a revert after duration_ticks (we only request scheduling).
    Returns actions for compatibility.
    """
    params = params or {}
    pld = payload or {}

    target = pld.get("target", params.get("target"))
    if not target:
        # nothing to do
        return []

    fold = float(pld.get("fold_change", params.get("fold_change", 1.0)))
    duration = int(pld.get("duration_ticks", params.get("duration_ticks", 24)))

    # ensure cell.internal exists
    try:
        internal = getattr(cell, "internal", None)
        if internal is None:
            cell.internal = {}
            internal = cell.internal
    except Exception:
        # if cannot set attribute, abort gracefully
        return []

    # apply fold change (store previous if present)
    prev = internal.get(target, None)
    try:
        # apply multiplicative fold if numeric, else set to fold
        if isinstance(prev, (int, float)):
            internal[target] = prev * fold
        else:
            internal[target] = fold
    except Exception:
        internal[target] = fold

    # schedule revert if env provides schedule_task / schedule
    scheduled = False
    try:
        if hasattr(env, "schedule_task"):
            # We add a small request object so caller/test can assert scheduling happened
            env.schedule_task({"action": "revert_internal", "cell_id": getattr(cell, "id", None),
                               "target": target, "prev": prev, "delay": duration})
            scheduled = True
        elif hasattr(env, "schedule"):
            env.schedule({"action": "revert_internal", "cell_id": getattr(cell, "id", None),
                          "target": target, "prev": prev, "delay": duration})
            scheduled = True
    except Exception:
        scheduled = False

    # optionally emit an event for observability
    payload_out = {"cell_id": getattr(cell, "id", None), "target": target, "fold_change": fold, "duration_ticks": duration, "scheduled": scheduled}
    try:
        if hasattr(env, "emit_event"):
            env.emit_event("internal_regulated", payload_out)
    except Exception:
        pass

    return [{"name": "internal_regulated", "payload": payload_out}]

