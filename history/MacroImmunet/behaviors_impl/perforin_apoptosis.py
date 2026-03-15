# behaviors_impl/perforin_apoptosis.py
"""
Perforin / apoptosis behavior used in tests.

- Emits intents via env.emit_intent when available:
    - 'perforin_release' for field-based release
    - 'perforin_apoptosis' for direct lysis (intent)
- Also emits 'lysis' event to remain compatible with older tests.
"""

import random

def perforin_apoptosis_v1(cell, env, params=None, payload=None, **kw):
    params = params or {}
    payload = payload or {}
    actions = []

    target_id = payload.get("target_id") or getattr(cell, "current_target", None)
    strength = float(payload.get("strength", params.get("default_strength", 1.0) or 1.0))

    if target_id is None:
        return actions

    # Field-based mode
    try:
        if hasattr(env, "has_field") and env.has_field("perforin"):
            # compute coord (prefer target coord)
            coord = None
            try:
                target = env.get_cell(target_id) if hasattr(env, "get_cell") else None
                coord = getattr(target, "coord", getattr(target, "position", None))
            except Exception:
                coord = None
            if coord is None:
                coord = getattr(cell, "coord", getattr(cell, "position", None))

            amount = strength
            # call add_to_field if present
            if hasattr(env, "add_to_field"):
                try:
                    env.add_to_field("perforin", coord, amount)
                except Exception:
                    pass

            # emit intent for perforin release so tests that capture intents succeed
            intent_payload = {"field": "perforin", "coord": coord, "amount": amount, "source": getattr(cell, "id", None)}
            try:
                if hasattr(env, "emit_intent"):
                    env.emit_intent("perforin_release", intent_payload)
            except Exception:
                pass

            actions.append({"name": "add_to_field", "payload": {"field": "perforin", "coord": coord, "amount": amount}})
            return actions
    except Exception:
        # fall back to direct lysis
        pass

    # Direct lysis fallback
    lysis_payload = {"target_id": target_id, "cause": "perforin", "probability": params.get("lysis_probability", 0.5), "cell_id": getattr(cell, "id", None), "tick": None}

    # emit intent for kill if env supports it
    try:
        if hasattr(env, "emit_intent"):
            env.emit_intent("perforin_apoptosis", {"target_id": target_id, "source": getattr(cell, "id", None)})
    except Exception:
        pass

    # also emit event "lysis" to be backwards compatible
    try:
        if hasattr(env, "emit_event"):
            env.emit_event("lysis", lysis_payload)
    except Exception:
        pass

    actions.append({"name": "lysis", "payload": lysis_payload})
    return actions

