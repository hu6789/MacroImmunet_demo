"""
behaviors_impl.natural_apoptosis
Implementation for natural_apoptosis_v1

Exports:
 - natural_apoptosis_v1(cell, env, params=None, payload=None, rng=None, **kw)
 - NaturalApoptosisBehavior class
 - natural_apoptosis(...) helper
"""
from typing import Any, Dict, Optional

def _safe_int(val, default=0):
    try:
        return int(val)
    except Exception:
        try:
            return int(float(val))
        except Exception:
            return default

def natural_apoptosis_v1(cell, env, params=None, payload=None, rng=None, **kw):
    params = params or {}
    lifespan_ticks = int(params.get("lifespan_ticks", 20000) or 20000)
    probability_per_tick_after_age = float(params.get("probability_per_tick_after_age", 0.01) or 0.01)
    early_stochastic_fraction = float(params.get("early_stochastic_fraction", 0.8) or 0.8)

    tick = getattr(env, "tick", None)
    birth_tick = getattr(cell, "birth_tick", None)
    # treat missing birth_tick as current tick (age 0)
    try:
        if birth_tick is None and tick is not None:
            birth_tick = tick
    except Exception:
        birth_tick = birth_tick

    age = 0
    try:
        if tick is not None and birth_tick is not None:
            age = int(max(0, int(tick) - int(birth_tick)))
        else:
            age = int(getattr(cell, "age_ticks", 0) or 0)
    except Exception:
        try:
            age = int(getattr(cell, "age_ticks", 0) or 0)
        except Exception:
            age = 0

    actions = []

    # deterministic death on exceeding lifespan
    if age >= lifespan_ticks:
        payload_out = {"cell_id": getattr(cell, "id", None), "cause": "age", "age": age, "tick": tick, "probability": 1.0}
        try:
            if hasattr(env, "emit_intent"):
                env.emit_intent("apoptosis", payload_out)
            elif hasattr(env, "emit_event"):
                env.emit_event("apoptosis", payload_out)
        except Exception:
            pass
        actions.append({"name": "apoptosis", "payload": payload_out})
        return actions

    # else may stochastic after threshold
    threshold_age = int(lifespan_ticks * early_stochastic_fraction)
    if age >= threshold_age:
        # rng
        try:
            r = rng.random() if (rng is not None and hasattr(rng, "random")) else __import__("random").random()
        except Exception:
            r = __import__("random").random()
        if r < probability_per_tick_after_age:
            payload_out = {"cell_id": getattr(cell, "id", None), "cause": "stochastic_age", "age": age, "tick": tick, "probability": probability_per_tick_after_age}
            try:
                if hasattr(env, "emit_intent"):
                    env.emit_intent("apoptosis", payload_out)
                elif hasattr(env, "emit_event"):
                    env.emit_event("apoptosis", payload_out)
            except Exception:
                pass
            actions.append({"name": "apoptosis", "payload": payload_out})
            return actions

    # no death this tick -> return empty list
    return actions

class NaturalApoptosisBehavior:
    def __init__(self, **kwargs):
        self.params = kwargs or {}

    def execute(self, cell, env, params=None, payload=None, rng=None, **kw):
        merged = {}
        merged.update(self.params or {})
        if isinstance(params, dict):
            merged.update(params)
        return natural_apoptosis_v1(cell, env, params=merged, payload=payload, rng=rng, **kw)

def natural_apoptosis(cell, env, params=None, payload=None, rng=None, **kw):
    return natural_apoptosis_v1(cell, env, params=params, payload=payload, rng=rng, **kw)
