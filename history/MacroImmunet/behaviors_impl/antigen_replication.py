# behaviors_impl/antigen_replication.py
"""
Implementation for antigen_replication_v1 -> replicate_intracellular

YAML params supported:
  - replication_rate_per_tick (multiplicative e.g. 1.10)
  - max_replication_time
  - min_viral_load_for_burst
  - max_replication_per_cell_per_tick
  - max_internal_viral_load

Signature:
  def replicate_intracellular(cell, env, params, rng=None, receptors=None) -> list[action]
"""
def _emit(env, name, payload):
    try:
        if hasattr(env, "emit_event"):
            env.emit_event(name, payload)
    except Exception:
        pass

def replicate_intracellular(cell, env, params, rng=None, receptors=None):
    params = params or {}
    try:
        # require infected state or meta
        state = getattr(cell, "state", None)
        meta = getattr(cell, "meta", {}) or {}
        if state not in ("Infected", "infected") and not meta.get("viral_load"):
            return []

        viral_load = float(meta.get("viral_load", 0.0))
        infection_timer = int(meta.get("infection_timer", 0))
        max_time = int(params.get("max_replication_time", 6))
        if infection_timer >= max_time:
            return []

        rep_rate = float(params.get("replication_rate_per_tick", 1.10))
        # compute growth amount (new virions produced this tick)
        growth = viral_load * (rep_rate - 1.0)
        # clamp to max per tick
        max_per_tick = float(params.get("max_replication_per_cell_per_tick", 20.0))
        spawn_amount = int(min(growth, max_per_tick))
        # update internal viral load
        new_vl = viral_load + spawn_amount
        max_internal = float(params.get("max_internal_viral_load", 1000.0))
        if new_vl > max_internal:
            new_vl = max_internal
        # commit updates
        try:
            if not hasattr(cell, "meta"):
                cell.meta = {}
            cell.meta["viral_load"] = float(new_vl)
            cell.meta["infection_timer"] = infection_timer + 1
        except Exception:
            pass

        # release to environment if above burst threshold
        min_for_burst = float(params.get("min_viral_load_for_burst", 5.0))
        released = 0
        if new_vl >= min_for_burst and spawn_amount > 0:
            # best-effort: add to Field_Antigen_Density
            pos = getattr(cell, "position", getattr(cell, "coord", (0,0)))
            try:
                if hasattr(env, "add_to_field"):
                    env.add_to_field("Field_Antigen_Density", pos, int(spawn_amount))
                    released = int(spawn_amount)
            except Exception:
                released = 0

        # emit event
        _emit(env, "replicated", {"cell_id": getattr(cell, "id", None), "viral_load": new_vl, "released": released, "tick": getattr(env, "tick", None)})
        return [{"name": "replicated", "cell_id": getattr(cell, "id", None), "viral_load": new_vl, "released": released}]
    except Exception:
        return []
