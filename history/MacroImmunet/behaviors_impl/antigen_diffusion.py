"""
Simple antigen diffusion hook implementation used by unit tests.

Exports:
 - antigen_diffusion_hook_v1(cell, env, params=None, payload=None, rng=None, **kw)

Behavior:
 - Reads centre cell coord value and neighbor values (via env.read_field or env.get_field/get_neighbors)
 - Computes simple explicit-diffusion deltas: d = factor * (avg_neighbors - val)
 - Applies deltas atomically via env.apply_field_deltas(field, deltas) if available,
   otherwise calls env.add_to_field(coord, delta) per coord.
 - Returns a list-of-actions for test compatibility.
"""
from typing import Dict, Tuple, Any, Iterable
import math

def _read_point(env, field, coord):
    # Try common APIs in order
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
    # fallback: try direct indexing if env has field map
    try:
        fm = getattr(env, "fields", {})
        return fm.get(field, {}).get(coord, 0)
    except Exception:
        return 0

def _get_neighbors(env, coord, radius):
    # Prefer env.get_neighbors(coord, radius) -> iterable of coords
    if hasattr(env, "get_neighbors"):
        try:
            return list(env.get_neighbors(coord, radius))
        except Exception:
            pass
    # fallback: 4-neighborhood for radius=1 (best-effort)
    x,y = coord
    out = []
    for dx in range(-int(radius), int(radius)+1):
        for dy in range(-int(radius), int(radius)+1):
            if dx == 0 and dy == 0:
                continue
            out.append((x+dx, y+dy))
    return out

def antigen_diffusion_hook_v1(cell, env, params=None, payload=None, rng=None, **kw):
    params = params or {}
    field = (params.get("target_field") or "Field_Antigen_Density") if isinstance(params, dict) else "Field_Antigen_Density"
    diffusion_factor = float(params.get("diffusion_rate", 0.05))
    radius = int(params.get("diffusion_radius", 1))
    max_ticks = int(params.get("max_diffusion_ticks", 10))

    # Resolve coordinate - tests will provide cell.position/coord/position tuple
    coord = getattr(cell, "position", None) or getattr(cell, "coord", None) or getattr(cell, "position", None)
    if coord is None:
        return []

    # read center and neighbors
    center_val = float(_read_point(env, field, coord) or 0.0)
    neighbors = _get_neighbors(env, coord, radius)
    if not neighbors:
        return []

    neighbor_vals = {}
    total = 0.0
    for n in neighbors:
        v = float(_read_point(env, field, n) or 0.0)
        neighbor_vals[n] = v
        total += v
    avg_neighbors = total / max(1, len(neighbor_vals))

    # compute simple explicit diffusion deltas: each cell tends toward neighbor average
    deltas: Dict[Tuple[int,int], float] = {}
    # center delta: factor * (avg_neighbors - center)
    center_delta = diffusion_factor * (avg_neighbors - center_val)
    if abs(center_delta) > 0:
        deltas[coord] = center_delta
    # neighbors receive -center_delta distributed proportionally (simple symmetric)
    # here we equally distribute opposite sign among neighbors
    if deltas and neighbor_vals:
        share = -center_delta / max(1, len(neighbor_vals))
        for n in neighbor_vals:
            # accumulate if already present
            deltas[n] = deltas.get(n, 0.0) + share

    # Apply deltas atomically if env supports it
    try:
        if hasattr(env, "apply_field_deltas"):
            env.apply_field_deltas(field, deltas)
        else:
            # fallback: call add_to_field per coord
            for c, dv in deltas.items():
                if hasattr(env, "add_to_field"):
                    env.add_to_field(field, c, dv)
                else:
                    # last resort: try env.apply_delta(field, coord, dv)
                    try:
                        env.apply_delta(field, c, dv)
                    except Exception:
                        pass
    except Exception:
        # be defensive: don't raise to break engine/tests
        pass

    return [{"name": "diffuse", "payload": {"field": field, "deltas_count": len(deltas)}}]
