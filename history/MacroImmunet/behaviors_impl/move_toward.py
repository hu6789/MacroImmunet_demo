# behaviors_impl/move_toward.py
"""move_toward_v1: chemotaxis helper or delegate to move_directed."""

from typing import Any, Dict, List
import importlib

def move_toward_v1(cell, env, params=None, payload=None, rng=None, receptors=None, **kw) -> List[Dict[str,Any]]:
    params = params or {}
    payload = payload or {}

    mode = payload.get("mode")
    if mode == "chemotaxis":
        # payload may specify chemokine (molecule) OR field directly
        chemokine = payload.get("chemokine")
        field = payload.get("field") or (("Field_" + chemokine.upper()) if chemokine else None)

        # try engine helper - prefer a field-aware API
        best = None
        try:
            if hasattr(env, "find_best_neighbor_by_field_gradient"):
                best = env.find_best_neighbor_by_field_gradient(getattr(cell,"position",getattr(cell,"coord",(0,0))), field or chemokine, params.get("max_step_distance",1.0), params.get("sensitivity",1.0))
            else:
                best = None
        except Exception:
            best = None

        if best is None:
            return []

        # capacity check
        try:
            if hasattr(env, "coord_has_capacity") and not env.coord_has_capacity(best):
                return []
        except Exception:
            pass

        action = {"name":"move", "payload":{"from": getattr(cell,"position",getattr(cell,"coord",(0,0))), "to": best, "reason":"chemotaxis", "field": field or chemokine}}
        try:
            if hasattr(env, "emit_intent"):
                env.emit_intent("move", action["payload"])
        except Exception:
            pass
        return [action]

    # delegate to move_directed for target or other modes
    try:
        mod = importlib.import_module("behaviors_impl.move_directed")
        fn = getattr(mod, "move_directed_v1", None)
        if fn:
            # map payload.target_coord through
            p = {"target_coord": payload.get("target_coord"), "dir_vector": payload.get("dir_vector")}
            return fn(cell, env, params=params, payload=p, rng=rng, receptors=receptors)
    except Exception:
        pass

    return []

