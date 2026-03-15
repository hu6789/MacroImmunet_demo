# behaviors_impl/diff.py
"""
IL-12 driven differentiation helper.
Exports:
 - IL12_driven_diff_v1(cell, env, params=None, payload=None, rng=None, **kw)
"""
from typing import Any, Dict
import math
import traceback

def _safe_get(cell, name, default=0.0):
    v = getattr(cell, name, None)
    if v is None:
        try:
            v = cell.__dict__.get(name, default)
        except Exception:
            v = default
    return v if v is not None else default

def _resolve_payload(params, payload, kw):
    if isinstance(payload, dict) and payload:
        return payload
    if isinstance(params, dict) and isinstance(params.get("payload"), dict):
        return params.get("payload")
    if kw and isinstance(kw.get("payload"), dict):
        return kw.get("payload")
    return {}

def _hill(x, K=0.4, n=2.0):
    try:
        x = float(x)
        K = float(K)
        n = float(n)
        num = x ** n
        den = (K ** n) + num
        if den == 0.0:
            return 0.0
        return num / den
    except Exception:
        return 0.0

def IL12_driven_diff_v1(cell, env, params=None, payload=None, rng=None, **kw):
    """
    Compute p = base_multiplier * hill(IL12_local, K, n) * affinity
    and emit change_state intent with probability p targeting Effector_Th1.
    """
    params = params or {}
    pld = _resolve_payload(params, payload, kw) or {}

    K = float(params.get("K", 0.4))
    n = float(params.get("n", 2.0))
    base = float(params.get("base_multiplier", 0.8))
    emit_numeric = bool(params.get("emit_numeric_probability", True))

    # resolve IL12_local and affinity from payload or cell internal
    il12_local = pld.get("IL12_local", None)
    if il12_local is None:
        il12_local = _safe_get(cell, "IL12_local", 0.0)
    try:
        il12_val = float(il12_local or 0.0)
    except Exception:
        il12_val = 0.0

    affinity = pld.get("affinity", None)
    if affinity is None:
        affinity = _safe_get(cell, "affinity", 0.0)
    try:
        affinity_val = float(affinity or 0.0)
    except Exception:
        affinity_val = 0.0

    # compute hill and final probability
    hill_val = _hill(il12_val, K=K, n=n)
    p_raw = base * hill_val * affinity_val
    p = max(0.0, min(1.0, float(p_raw)))

    # Emit intent if requested (even if p == 0, for observability tests might expect call)
    payload_out = {
        "target_state": "Effector_Th1",
        "probability": p,
        "cause": "IL12_driven",
        "cell_id": getattr(cell, "id", None),
        "tick": getattr(env, "tick", None)
    }

    try:
        if hasattr(env, "emit_intent"):
            env.emit_intent("change_state", payload_out)
        elif hasattr(env, "emit_event"):
            env.emit_event("change_state", payload_out)
    except Exception:
        try:
            env.log_event("IL12_emit_failed", {"cell_id": getattr(cell, "id", None)})
        except Exception:
            pass

    # return actions (compatibility)
    return [{"name": "change_state_emitted", "payload": payload_out}] if emit_numeric else []

