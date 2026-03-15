# behaviors_impl/dc.py
"""
DC related helper implementations.

Exports:
 - DC_upregulate_costim(cell, env, params=None, payload=None, rng=None, **kw)
 - DCUpregulateBehavior class adapter (if needed)
"""
from typing import Any, Dict
import math
import traceback

def _resolve_payload(params, payload, kw):
    if isinstance(payload, dict) and payload:
        return payload
    if isinstance(params, dict) and isinstance(params.get("payload"), dict):
        return params.get("payload")
    if kw and isinstance(kw.get("payload"), dict):
        return kw.get("payload")
    return {}

def DC_upregulate_costim(cell, env, params=None, payload=None, rng=None, **kw):
    """
    Increase cell.co_stim and optionally emit a secrete intent for IL12.

    Returns a list of action dicts (for test compatibility).
    """
    params = params or {}
    pld = _resolve_payload(params, payload, kw) or {}

    # resolve increments and flags (prefer payload overrides)
    try:
        inc = float(pld.get("costim_increase", params.get("costim_increase", 0.5)))
    except Exception:
        inc = float(params.get("costim_increase", 0.5))
    secrete_flag = pld.get("secrete_il12", params.get("secrete_il12", True))
    try:
        il12_rate = float(pld.get("il12_rate", params.get("il12_rate", 0.2)))
    except Exception:
        il12_rate = float(params.get("il12_rate", 0.2))
    try:
        il12_duration = int(pld.get("il12_duration", params.get("il12_duration", 24)))
    except Exception:
        il12_duration = int(params.get("il12_duration", 24))

    # safe-get and update co_stim
    prev = None
    try:
        prev = getattr(cell, "co_stim", None)
        if prev is None:
            prev = 0.0
            try:
                cell.co_stim = 0.0
            except Exception:
                pass
        new = prev + inc
        try:
            cell.co_stim = new
        except Exception:
            # be defensive; try to set via __dict__
            try:
                cell.__dict__["co_stim"] = new
            except Exception:
                pass
    except Exception:
        # don't raise to tests
        try:
            env.log_event("dc_upregulate_error", {"cell_id": getattr(cell, "id", None), "err": traceback.format_exc()})
        except Exception:
            pass
        return []

    actions = [{"name": "co_stim_upregulated", "payload": {"prev": prev, "new": getattr(cell, "co_stim", None)}}]

    # optionally emit secrete intent for IL12
    if secrete_flag:
        intent_payload = {
            "molecule": "IL12",
            "rate_per_tick": il12_rate,
            "duration_ticks": il12_duration,
            "source_cell": getattr(cell, "id", None)
        }
        try:
            if hasattr(env, "emit_intent"):
                env.emit_intent("secrete", intent_payload)
            elif hasattr(env, "emit_event"):
                # fallback if engine exposes event only
                env.emit_event("secrete", intent_payload)
            actions.append({"name": "secrete_intent_emitted", "payload": intent_payload})
        except Exception:
            # never raise
            try:
                env.log_event("dc_upregulate_emit_failed", {"cell_id": getattr(cell, "id", None)})
            except Exception:
                pass

    return actions

# Optional adapter class to match other behavior modules
class DCUpregulateBehavior:
    def __init__(self, **kwargs):
        self.params = kwargs or {}

    def execute(self, cell, env, params=None, payload=None, rng=None, **kw):
        merged = {}
        merged.update(self.params or {})
        if isinstance(params, dict):
            merged.update(params)
        return DC_upregulate_costim(cell, env, params=merged, payload=payload, rng=rng, **kw)

