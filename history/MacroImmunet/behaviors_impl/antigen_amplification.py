"""
Simple antigen amplification implementation used by unit tests.

Exports:
 - antigen_amplification_v1(cell, env, params=None, payload=None, rng=None, **kw)

Behavior:
 - If mode == 'field': read local field value, compute amplified = val * factor (or logistic),
   apply delta via env.add_to_field or env.apply_field_deltas.
 - If mode == 'cell': and cell has 'viral_load' or similar, amplify that (tests may not use).
 - Defensive about missing APIs.
"""
from typing import Any, Dict

def _read_field(env, field, coord):
    if hasattr(env, "read_field"):
        try:
            return env.read_field(field, coord)
        except Exception:
            pass
    if hasattr(env, "get_field"):
        try:
            return env.get_field(field, coord)
        except Exception:
            pass
    return 0.0

def antigen_amplification_v1(cell, env, params=None, payload=None, rng=None, **kw):
    params = params or {}
    pld = payload or {}
    field = (params.get("target_field") or "Field_Antigen_Density")
    mode = pld.get("mode") or params.get("mode", "field")
    factor = float(pld.get("replication_factor") or params.get("replication_rate_fold_per_tick", 1.15))
    saturation_K = float(params.get("saturation_K", 500.0))
    burst = int(params.get("burst_yield_units", 0))

    coord = getattr(cell, "position", None) or getattr(cell, "coord", None)
    actions = []

    if mode == "field":
        # read current
        cur = float(_read_field(env, field, coord) or 0.0)
        new = cur * factor
        # optional logistic saturation (simple)
        if saturation_K and saturation_K > 0:
            new = new * (1.0 - (cur / saturation_K))
        delta = new - cur
        # if burst specified, we can add burst in addition
        if burst:
            delta += burst
        try:
            if hasattr(env, "add_to_field"):
                env.add_to_field(field, coord, delta)
            elif hasattr(env, "apply_field_deltas"):
                env.apply_field_deltas(field, {coord: delta})
            else:
                # fallback no-op
                pass
        except Exception:
            pass
        actions.append({"name": "replicate", "payload": {"field": field, "delta": delta}})
    else:
        # cell-mode: try to bump cell.viral_load if present
        try:
            vl = float(getattr(cell, "viral_load", 0.0) or 0.0)
            new_vl = vl * factor + burst
            try:
                setattr(cell, "viral_load", new_vl)
            except Exception:
                pass
            actions.append({"name": "replicate_cell", "payload": {"prev": vl, "new": new_vl}})
        except Exception:
            pass

    return actions
