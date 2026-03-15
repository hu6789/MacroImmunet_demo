# behaviors_impl/move_directed.py
"""move_directed_v1: convert dir vector or target coord -> neighbor move intent."""

from typing import Any, Dict, List, Tuple
import math

def _to_coord_tuple(c):
    if isinstance(c, dict) and "x" in c and "y" in c:
        return (int(c["x"]), int(c["y"]))
    if isinstance(c, (list, tuple)):
        return (int(c[0]), int(c[1]))
    return None

def move_directed_v1(cell, env, params=None, payload=None, rng=None, receptors=None, **kw) -> List[Dict[str,Any]]:
    params = params or {}
    payload = payload or {}
    max_step = float(params.get("max_step_distance", 1.0))
    obstacle_retry = int(params.get("obstacle_retry", 3))
    retry_strategy = params.get("retry_strategy", "prefer_forward")

    origin = getattr(cell, "position", getattr(cell, "coord", None))
    if origin is None:
        origin = getattr(cell, "coord", (0,0))
    # resolve candidate by dir_vector or target_coord
    cand = None
    if "dir_vector" in payload and payload["dir_vector"] is not None:
        dv = payload["dir_vector"]
        # call engine helper if present
        if hasattr(env, "coord_move_by_vector"):
            try:
                cand = env.coord_move_by_vector(origin, dv, max_step)
            except Exception:
                cand = None
        else:
            # fallback: simple quantize
            dx = int(math.copysign(1, dv[0])) if dv[0] != 0 else 0
            dy = int(math.copysign(1, dv[1])) if dv[1] != 0 else 0
            cand = (origin[0]+dx, origin[1]+dy)
    elif "target_coord" in payload and payload["target_coord"] is not None:
        tgt = _to_coord_tuple(payload["target_coord"])
        if tgt is not None:
            # step towards target by one grid-step (clamp by max_step)
            dx = tgt[0] - origin[0]
            dy = tgt[1] - origin[1]
            stepx = max(-1, min(1, dx))
            stepy = max(-1, min(1, dy))
            cand = (origin[0]+stepx, origin[1]+stepy)

    # helper to attempt a candidate
    def try_candidate(candidate, attempt_index=0, reason="candidate"):
        if candidate is None:
            return None
        # canonicalize
        try:
            candidate = (int(candidate[0]), int(candidate[1]))
        except Exception:
            return None
        # capacity check
        has_capacity = True
        try:
            if hasattr(env, "coord_has_capacity"):
                has_capacity = bool(env.coord_has_capacity(candidate))
        except Exception:
            has_capacity = True
        if has_capacity:
            action = {"name":"move", "payload":{"from": origin, "to": candidate, "attempt_index": attempt_index, "reason": reason}}
            # emit intent if env supports it
            try:
                if hasattr(env, "emit_intent"):
                    env.emit_intent("move", action["payload"])
            except Exception:
                pass
            return action
        return None

    # first try primary candidate
    primary_action = try_candidate(cand, attempt_index=0, reason="primary")
    if primary_action:
        return [primary_action]

    # blocked -> fallback neighbors
    neighbors = []
    try:
        # env.get_neighbors expected to return ordered neighbor coords
        if hasattr(env, "get_neighbors"):
            neighbors = env.get_neighbors(origin) or []
    except Exception:
        neighbors = []
    # ensure neighbors includes simple 4-neigh fallback
    if not neighbors:
        neighbors = [(origin[0]+1,origin[1]), (origin[0]-1,origin[1]), (origin[0],origin[1]+1), (origin[0],origin[1]-1)]

    attempt = 0
    for nb in neighbors:
        if attempt >= obstacle_retry:
            break
        a = try_candidate(nb, attempt_index=attempt+1, reason="fallback")
        if a:
            return [a]
        attempt += 1

    # no move possible
    # optionally log
    try:
        if hasattr(env, "log_event"):
            env.log_event({"name":"move_blocked","cell_id": getattr(cell,"id",None),"coord":origin})
    except Exception:
        pass
    return []

