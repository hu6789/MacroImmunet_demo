# behaviors_impl/phagocytose.py
"""
Phagocytose implementation matching phagocytose_v1 YAML.

Signature:
  def phagocytose_v1(cell, env, params, rng=None, receptors=None, payload=None) -> list[action]

Behavior:
 - Prefer particle uptake if prefer_particles True and particles exist (env.sample_particles_at)
 - Fallback to field consumption (Field_Antigen_Density) using env.consume_local_antigen if available
 - Compute consumed = min(uptake_per_tick, max_capacity - current_load, available)
 - Update cell.meta['antigen_load'] only after successful consumption
 - Emit 'phagocytosed' event with payload keys: cell_id, amount, tick, source
 - Defensive: do not raise if env lacks methods
"""
def _read_field(env, name, coord):
    try:
        if hasattr(env, "read_field"):
            return float(env.read_field(name, coord))
    except Exception:
        pass
    try:
        if hasattr(env, "get_at"):
            return float(env.get_at(name, coord))
    except Exception:
        pass
    return 0.0

def _consume(env, coord, amount):
    try:
        if hasattr(env, "consume_local_antigen"):
            return bool(env.consume_local_antigen(coord, amount))
    except Exception:
        pass
    try:
        if hasattr(env, "add_to_field"):
            # negative delta to consume
            env.add_to_field("Field_Antigen_Density", coord, -int(amount))
            return True
    except Exception:
        pass
    return False

def _emit(env, name, payload):
    try:
        if hasattr(env, "emit_event"):
            env.emit_event(name, payload)
    except Exception:
        pass

def phagocytose_v1(cell, env, params, rng=None, receptors=None, payload=None):
    params = params or {}
    try:
        pos = getattr(cell, "position", getattr(cell, "coord", (0,0)))
        current_load = int(getattr(cell, "meta", {}).get("antigen_load", 0))
        max_capacity = int(params.get("max_capacity", 5))
        uptake = int(params.get("uptake_per_tick", 2))
        prefer_particles = bool(params.get("prefer_particles", True))

        if max_capacity <= 0 or uptake <= 0 or (max_capacity - current_load) <= 0:
            return []

        remaining_cap = max_capacity - current_load
        consumed = 0
        source = None

        # Try particles first
        if prefer_particles:
            try:
                if hasattr(env, "sample_particles_at"):
                    parts = env.sample_particles_at(pos) or []
                    avail = len(parts)
                    take = min(int(avail), uptake, remaining_cap)
                    if take > 0:
                        ok = _consume(env, pos, take)
                        if ok:
                            consumed = int(take)
                            source = "particles"
            except Exception:
                pass

        # Fallback to field
        if consumed == 0:
            field_val = _read_field(env, "Field_Antigen_Density", pos)
            try:
                field_int = int(field_val)
            except Exception:
                field_int = int(field_val) if field_val else 0
            take = min(uptake, remaining_cap, field_int)
            if take > 0:
                ok = _consume(env, pos, take)
                if ok:
                    consumed = int(take)
                    source = "field"

        if consumed > 0:
            try:
                if not hasattr(cell, "meta"):
                    cell.meta = {}
                cell.meta["antigen_load"] = int(current_load + consumed)
            except Exception:
                try:
                    if hasattr(env, "log_event"):
                        env.log_event("phagocytose_update_failed", {"cell_id": getattr(cell, "id", None)})
                except Exception:
                    pass

            payload_ev = {"cell_id": getattr(cell, "id", None), "amount": consumed, "tick": getattr(env, "tick", None), "source": source}
            _emit(env, "phagocytosed", payload_ev)
            return [{"name":"phagocytosed", "cell_id": getattr(cell,"id",None), "amount": consumed, "source": source}]
        return []
    except Exception:
        return []
