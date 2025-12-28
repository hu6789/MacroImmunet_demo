# cell_master/behaviour_library/proliferate.py
"""
Proliferation behaviour (proliferate_v1).

Signature:
  def proliferate_v1(cell, env, params=None, payload=None, rng=None, **kw) -> list[action]

Behaviour:
 - With probability (params or payload) attempt to divide.
 - Check optional gating:
    - max_divisions: stop if cell.meta['division_count'] >= max_divisions
    - min_interval_ticks: require last_division_tick gap
    - optional resource_field/resource_cost: try to consume local resource
 - If permitted, create a daughter cell using engine API (spawn_cell/create_cell) or by emitting an intent.
 - Update mother's meta: increment division_count, set last_division_tick.
 - If `separate_mass` True and mass present, split mass between mother and daughter.
 - Emit 'divided' event and return actions describing creation and meta updates.
 - Defensive: swallow exceptions and return [] on failure.
"""

import random
from typing import Any, Dict, List, Optional, Tuple

def _try_consume_resource(env: Any, coord: Tuple[float, float], field: str, amount: float) -> bool:
    """
    Best-effort consumption from engine. Tries a few common APIs.
    Returns True if a call succeeded (not necessarily validated).
    """
    try:
        # common engines might expose consume_local_resource or consume_field or add_to_field with negative
        if hasattr(env, "consume_local_resource"):
            return bool(env.consume_local_resource(coord, field, amount))
    except Exception:
        pass
    try:
        if hasattr(env, "consume_local_antigen"):
            # legacy API for antigen-like resources - attempt
            return bool(env.consume_local_antigen(coord, int(amount)))
    except Exception:
        pass
    try:
        # fallback: write negative delta to field via add_to_field or apply_field_delta
        if hasattr(env, "add_to_field"):
            env.add_to_field(field, coord, -amount)
            return True
        if hasattr(env, "apply_field_delta"):
            # some APIs signature apply_field_delta(field, coord, delta)
            try:
                env.apply_field_delta(field, coord, -amount)
            except TypeError:
                # try alternate signature
                env.apply_field_delta(coord, field, -amount)
            return True
    except Exception:
        pass
    return False

def _try_spawn_cell(env: Any, coord: Tuple[float, float], cell_type: Optional[str], meta: Dict[str,Any]) -> Optional[str]:
    """
    Try engine APIs to create a new cell. Return new cell id if available, else None.
    Falls back to emitting intent 'spawn_cell' (so outside orchestrator can act).
    """
    try:
        if hasattr(env, "spawn_cell") and callable(env.spawn_cell):
            new_id = env.spawn_cell(coord, cell_type, meta)
            return new_id
    except Exception:
        pass
    try:
        if hasattr(env, "create_cell") and callable(env.create_cell):
            new = env.create_cell(cell_type=cell_type, coord=coord, meta=meta)
            # some engines return id, others return object
            if isinstance(new, str):
                return new
            try:
                return getattr(new, "id", None)
            except Exception:
                return None
    except Exception:
        pass
    # fallback: emit intent so harness can create
    try:
        if hasattr(env, "emit_intent"):
            env.emit_intent("spawn_cell", {"coord": coord, "cell_type": cell_type, "meta": meta})
            return None
    except Exception:
        pass
    return None

def proliferate_v1(cell, env, params=None, payload=None, rng=None, **kw) -> List[Dict[str, Any]]:
    params = params or {}
    payload = payload or {}
    rng = rng or random.Random()

    # resolve runtime parameters (payload overrides params)
    prob = float(payload.get("probability", params.get("probability", 1.0) or 1.0))
    max_divisions = params.get("max_divisions", None)
    if payload.get("max_divisions") is not None:
        max_divisions = payload.get("max_divisions")
    try:
        if max_divisions is not None:
            max_divisions = int(max_divisions)
    except Exception:
        max_divisions = None

    min_interval = params.get("min_interval_ticks", None)
    if payload.get("min_interval_ticks") is not None:
        min_interval = payload.get("min_interval_ticks")
    try:
        if min_interval is not None:
            min_interval = int(min_interval)
    except Exception:
        min_interval = None

    resource_field = payload.get("resource_field", params.get("resource_field", None))
    resource_cost = float(payload.get("resource_cost", params.get("resource_cost", 1.0) or 1.0))

    daughter_type = payload.get("daughter_type", params.get("daughter_type", None))
    if not daughter_type:
        # default to same as mother if provided via meta or 'cell_type' attribute
        daughter_type = getattr(cell, "cell_type", None) or getattr(cell, "type", None) or None

    inherit_keys = payload.get("inherit_meta_keys", params.get("inherit_meta_keys", [])) or []
    separate_mass = bool(payload.get("separate_mass", params.get("separate_mass", False)))
    tick = getattr(env, "tick", None)

    actions: List[Dict[str, Any]] = []

    # Random gating
    try:
        if prob < 1.0 and rng.random() >= prob:
            return []
    except Exception:
        # if RNG fails, continue
        pass

    # gating: max_divisions
    try:
        meta = getattr(cell, "meta", {}) or {}
        div_count = int(meta.get("division_count", 0) or 0)
        if max_divisions is not None and div_count >= max_divisions:
            return []
    except Exception:
        div_count = 0

    # gating: min interval
    try:
        last_div = meta.get("last_division_tick", None)
        if min_interval is not None and last_div is not None and tick is not None:
            if (tick - int(last_div)) < int(min_interval):
                return []
    except Exception:
        pass

    # resource consumption check (best-effort)
    if resource_field:
        coord = getattr(cell, "coord", None) or getattr(cell, "position", None) or (0.0, 0.0)
        ok = False
        try:
            ok = _try_consume_resource(env, coord, resource_field, resource_cost)
        except Exception:
            ok = False
        if not ok:
            # resource not available, abort proliferation attempt
            return []

    # prepare daughter meta
    daughter_meta = {}
    try:
        # inherit requested keys from mother.meta
        cm = getattr(cell, "meta", {}) or {}
        for k in inherit_keys:
            if k in cm:
                daughter_meta[k] = cm[k]
        # default minimal meta (track origin)
        daughter_meta.setdefault("parent_id", getattr(cell, "id", None))
    except Exception:
        daughter_meta = {"parent_id": getattr(cell, "id", None)}

    # handle mass splitting if requested
    mother_mass = getattr(cell, "mass", None)
    new_daughter_mass = None
    if separate_mass and mother_mass is not None:
        try:
            mother_mass = float(mother_mass)
            half = mother_mass / 2.0
            new_daughter_mass = half
            # update mother mass if writable
            try:
                setattr(cell, "mass", half)
            except Exception:
                try:
                    cell.mass = half
                except Exception:
                    pass
            daughter_meta["mass"] = half
        except Exception:
            new_daughter_mass = None

    # coordinate for daughter (try place near mother; small jitter)
    coord = getattr(cell, "coord", None) or getattr(cell, "position", None) or (0.0, 0.0)
    try:
        cx = float(coord[0]); cy = float(coord[1])
    except Exception:
        cx, cy = 0.0, 0.0
    # small jitter to avoid exact overlap
    try:
        jitter = float(params.get("spawn_jitter", 0.5))
    except Exception:
        jitter = 0.5
    try:
        # simple deterministic-ish offset using RNG
        ang = rng.random() * 2.0 * 3.141592653589793
        dx = math.cos(ang) * jitter
        dy = math.sin(ang) * jitter
        daughter_coord = (cx + dx, cy + dy)
    except Exception:
        daughter_coord = (cx, cy)

    # attempt to spawn/create cell via engine
    new_id = None
    try:
        new_id = _try_spawn_cell(env, daughter_coord, daughter_type, daughter_meta)
    except Exception:
        new_id = None

    # Update mother's meta: division_count, last_division_tick
    try:
        if not hasattr(cell, "meta") or cell.meta is None:
            cell.meta = {}
        cell.meta["division_count"] = int(meta.get("division_count", 0) or 0) + 1
        cell.meta["last_division_tick"] = tick
    except Exception:
        pass

    # emit event and build actions
    evt_payload = {"parent_id": getattr(cell, "id", None), "daughter_id": new_id, "coord": daughter_coord, "tick": tick}
    try:
        if hasattr(env, "emit_event") and callable(env.emit_event):
            env.emit_event("divided", evt_payload)
    except Exception:
        pass

    # actions: spawn/daughter info and metadata update
    if new_id is not None:
        actions.append({"name": "spawned", "payload": {"new_id": new_id, "coord": daughter_coord, "cell_type": daughter_type}})
    else:
        # record that we asked for a spawn (intent) - caller/harness may create it
        actions.append({"name": "spawn_intent", "payload": {"coord": daughter_coord, "cell_type": daughter_type, "meta": daughter_meta}})

    actions.append({"name": "divided", "payload": evt_payload})
    return actions


# adapter class for factories if desired
class ProliferateBehavior:
    def __init__(self, **kwargs):
        self.params = kwargs or {}
    def execute(self, cell, env, params=None, payload=None, rng=None, **kw):
        merged = dict(self.params)
        if params:
            merged.update(params)
        return proliferate_v1(cell, env, params=merged, payload=payload, rng=rng, **kw)

