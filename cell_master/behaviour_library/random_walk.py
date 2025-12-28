# cell_master/behaviour_library/random_walk.py
"""
Random-walk / directed-move behavior for demo.

Signature:
  def random_walk_v1(cell, env, params=None, payload=None, rng=None, **kw) -> list[action]

Params (defaults shown):
  - step_size: float (default 1.0)            # nominal step length
  - probability: float (default 1.0)          # chance to attempt a move this invocation
  - persistence: float (default 0.0)          # 0..1, tendency to keep previous direction
  - max_step: float (optional)                # clamp max step length
  - chemotaxis_field: str (optional)         # if present, attempt to move up gradient of this field
  - chemotaxis_strength: float (default 1.0) # how strongly gradient biases movement
  - bias_toward: tuple(x,y) or cell_id (optional) # explicit attractor
  - radius_limit: float (optional)            # constrain moves to within this distance from origin if desired

Behavior:
 - With probability 'probability' attempts a move.
 - If 'chemotaxis_field' and env.read_field / env.get_at available, compute approximate gradient
   by sampling at small offsets and bias movement toward increasing field.
 - If 'bias_toward' provided, bias movement toward the point (or the target cell if id given).
 - Combine random direction, persistence (if cell.meta['last_move_vec'] exists), and biases to produce
   new coord. Try engine move APIs; fallback to setting cell.coord directly.
 - Emit "moved" event and return action list describing move.
 - Defensive: swallow exceptions and return [] on failure.
"""

import math
import random
from typing import Any, Dict, List, Tuple, Optional

Vector = Tuple[float, float]

def _norm(v: Vector) -> float:
    return math.hypot(v[0], v[1])

def _scale(v: Vector, s: float) -> Vector:
    return (v[0]*s, v[1]*s)

def _add(a: Vector, b: Vector) -> Vector:
    return (a[0]+b[0], a[1]+b[1])

def _sub(a: Vector, b: Vector) -> Vector:
    return (a[0]-b[0], a[1]-b[1])

def _unit(v: Vector) -> Vector:
    n = _norm(v)
    if n == 0:
        return (0.0, 0.0)
    return (v[0]/n, v[1]/n)

def _sample_field_at(env: Any, field: str, coord: Vector) -> Optional[float]:
    """Try several common engine read APIs to obtain field value at coord."""
    try:
        if hasattr(env, "read_field"):
            return float(env.read_field(field, coord))
    except Exception:
        pass
    try:
        if hasattr(env, "get_at"):
            return float(env.get_at(field, coord))
    except Exception:
        pass
    try:
        if hasattr(env, "read_field_at"):
            return float(env.read_field_at(coord, field))
    except Exception:
        pass
    return None

def _try_move_in_engine(env: Any, cell_id: Optional[str], new_coord: Vector) -> bool:
    """Try a few common engine APIs to request a move. Return True if one succeeded."""
    try:
        if cell_id is None:
            # some engines accept a cell object or index; we can't do much here
            pass
        else:
            if hasattr(env, "move_cell") and callable(env.move_cell):
                env.move_cell(cell_id, new_coord)
                return True
            if hasattr(env, "set_cell_position") and callable(env.set_cell_position):
                env.set_cell_position(cell_id, new_coord)
                return True
            if hasattr(env, "update_cell_position") and callable(env.update_cell_position):
                env.update_cell_position(cell_id, new_coord)
                return True
    except Exception:
        return False
    return False

def _resolve_bias_target(env: Any, bias_toward) -> Optional[Vector]:
    """If bias_toward is (x,y) return it; if it's a cell_id try env.get_cell to locate."""
    try:
        if bias_toward is None:
            return None
        if isinstance(bias_toward, (tuple, list)) and len(bias_toward) >= 2:
            return (float(bias_toward[0]), float(bias_toward[1]))
        # otherwise treat as cell id
        if hasattr(env, "get_cell") and callable(env.get_cell):
            target = env.get_cell(bias_toward)
            if target:
                pos = getattr(target, "coord", None) or getattr(target, "position", None)
                if pos:
                    return (float(pos[0]), float(pos[1]))
    except Exception:
        pass
    return None

def random_walk_v1(cell, env, params=None, payload=None, rng=None, **kw) -> List[Dict[str, Any]]:
    params = params or {}
    payload = payload or {}
    rng = rng or random.Random()

    # parameters
    step_size = float(payload.get("step_size", params.get("step_size", 1.0) or 1.0))
    probability = float(payload.get("probability", params.get("probability", 1.0) or 1.0))
    persistence = float(payload.get("persistence", params.get("persistence", 0.0) or 0.0))
    max_step = params.get("max_step", None)
    if max_step is not None:
        try:
            max_step = float(max_step)
        except Exception:
            max_step = None
    chem_field = payload.get("chemotaxis_field", params.get("chemotaxis_field", None))
    chem_strength = float(payload.get("chemotaxis_strength", params.get("chemotaxis_strength", 1.0) or 1.0))
    bias_toward = payload.get("bias_toward", params.get("bias_toward", None))
    radius_limit = params.get("radius_limit", None)

    actions: List[Dict[str, Any]] = []

    # decide whether to attempt move
    try:
        if probability < 1.0 and rng.random() >= probability:
            return []
    except Exception:
        # if RNG fails, continue
        pass

    # get current coord
    coord = getattr(cell, "coord", None) or getattr(cell, "position", None)
    if coord is None:
        coord = (0.0, 0.0)
    try:
        cx = float(coord[0]); cy = float(coord[1])
        coord = (cx, cy)
    except Exception:
        coord = (0.0, 0.0)

    # start with random direction
    theta = rng.random() * 2.0 * math.pi
    dir_vec = (math.cos(theta), math.sin(theta))

    # incorporate persistence if present (store last_move_vec in meta)
    last_vec = None
    try:
        lm = getattr(cell, "meta", {}) or {}
        lv = lm.get("last_move_vec")
        if lv and isinstance(lv, (list, tuple)) and len(lv)>=2:
            last_vec = (float(lv[0]), float(lv[1]))
    except Exception:
        last_vec = None

    if last_vec is not None and persistence > 0.0:
        # blend last_vec (unit) with random dir
        try:
            lv_unit = _unit(last_vec)
            blended = _add(_scale(lv_unit, persistence), _scale(dir_vec, (1.0 - persistence)))
            dir_vec = _unit(blended)
        except Exception:
            dir_vec = _unit(dir_vec)

    # chemotaxis bias
    if chem_field:
        try:
            # small offset to estimate gradient
            eps = 0.5 * max(0.5, step_size)
            f_c = _sample_field_at(env, chem_field, coord)
            f_xp = _sample_field_at(env, chem_field, (coord[0] + eps, coord[1]))
            f_xm = _sample_field_at(env, chem_field, (coord[0] - eps, coord[1]))
            f_yp = _sample_field_at(env, chem_field, (coord[0], coord[1] + eps))
            f_ym = _sample_field_at(env, chem_field, (coord[0], coord[1] - eps))

            # compute gradient if samples available
            gx = None; gy = None
            if f_xp is not None and f_xm is not None:
                gx = (f_xp - f_xm) / (2.0 * eps)
            if f_yp is not None and f_ym is not None:
                gy = (f_yp - f_ym) / (2.0 * eps)

            if gx is not None or gy is not None:
                gvec = (gx or 0.0, gy or 0.0)
                g_unit = _unit(gvec)
                # bias = chem_strength * gradient_unit
                bias = _scale(g_unit, chem_strength)
                # combine with existing dir_vec (weak blending)
                try:
                    combined = _add(_scale(dir_vec, 1.0), bias)
                    dir_vec = _unit(combined)
                except Exception:
                    pass
        except Exception:
            pass

    # bias_toward (explicit attractor)
    tb = _resolve_bias_target(env, bias_toward)
    if tb:
        try:
            toward_vec = _sub(tb, coord)
            toward_unit = _unit(toward_vec)
            # combine with dir_vec (weight attractor stronger)
            combined = _add(_scale(dir_vec, 0.5), _scale(toward_unit, 0.5))
            dir_vec = _unit(combined)
        except Exception:
            pass

    # compute step length and clamp
    step_len = float(step_size)
    if max_step is not None and step_len > max_step:
        step_len = max_step

    new_x = coord[0] + dir_vec[0] * step_len
    new_y = coord[1] + dir_vec[1] * step_len
    new_coord = (new_x, new_y)

    # enforce radius_limit if requested (from origin (0,0) unless params give origin)
    if radius_limit is not None:
        try:
            origin = params.get("radius_origin", (0.0, 0.0))
            ox = float(origin[0]); oy = float(origin[1])
            dx = new_coord[0] - ox; dy = new_coord[1] - oy
            if math.hypot(dx, dy) > float(radius_limit):
                # clamp to circle boundary
                ang = math.atan2(dy, dx)
                new_coord = (ox + math.cos(ang) * float(radius_limit), oy + math.sin(ang) * float(radius_limit))
        except Exception:
            pass

    moved = False
    cell_id = getattr(cell, "id", None)

    # try engine move APIs
    try:
        moved = _try_move_in_engine(env, cell_id, new_coord)
    except Exception:
        moved = False

    # if not moved by engine, attempt to set attributes directly
    if not moved:
        try:
            try:
                setattr(cell, "coord", new_coord)
            except Exception:
                try:
                    setattr(cell, "position", new_coord)
                except Exception:
                    # last resort: if cell.meta available, write there
                    if not hasattr(cell, "meta") or cell.meta is None:
                        cell.meta = {}
                    cell.meta["coord"] = new_coord
            moved = True
        except Exception:
            moved = False

    # store last_move_vec in meta for persistence next tick
    try:
        if not hasattr(cell, "meta") or cell.meta is None:
            cell.meta = {}
        cell.meta["last_move_vec"] = (new_coord[0] - coord[0], new_coord[1] - coord[1])
    except Exception:
        pass

    tick = getattr(env, "tick", None)

    if moved:
        evt = {"cell_id": cell_id, "from": coord, "to": new_coord, "tick": tick}
        _try_emit = getattr(env, "emit_event", None)
        try:
            if callable(_try_emit):
                _try_emit("moved", evt)
        except Exception:
            pass
        actions.append({"name": "moved", "payload": evt})

    return actions

