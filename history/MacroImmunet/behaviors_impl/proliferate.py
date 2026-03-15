# behaviors_impl/proliferate.py
"""
Proliferation impl aligned to proliferate_v1 YAML.

Signature:
  def proliferate_v1(cell, env, params, rng=None, receptors=None, payload=None) -> list[action]
Behavior:
 - Check division_request (cell.division_request or cell.meta['division_request'] or payload)
 - Schedule/execute division: find free neighbor(s), optionally reserve, spawn via env.spawn_cell
 - Retry per params.spawn_retry with backoff
 - Update parent cell.meta (division_pending, division_count)
 - Emit events 'divided' and 'post_expansion'
 - Return a summary action {'name':'proliferate_attempt', ...}
"""
import time

def _emit(env, name, payload):
    try:
        if hasattr(env, "emit_event"):
            env.emit_event(name, payload)
    except Exception:
        pass

def _find_free(env, pos, strategy):
    try:
        if hasattr(env, "find_free_neighbor"):
            return env.find_free_neighbor(pos, strategy)
    except Exception:
        pass
    return None

def _reserve(env, coord):
    try:
        if hasattr(env, "reserve_coord"):
            return bool(env.reserve_coord(coord))
    except Exception:
        pass
    return True

def _release(env, coord):
    try:
        if hasattr(env, "release_reservation"):
            return bool(env.release_reservation(coord))
    except Exception:
        pass
    return True

def _spawn(env, template_id, coord, clone_id):
    try:
        if hasattr(env, "spawn_cell"):
            return env.spawn_cell(template_id=template_id, coord=coord, clone_id=clone_id)
    except Exception:
        pass
    return None

def proliferate_v1(cell, env, params, rng=None, receptors=None, payload=None):
    params = params or {}
    try:
        # detect division request: explicit flag or payload
        division_request = False
        if getattr(cell, "division_request", False):
            division_request = True
        elif getattr(cell, "meta", {}).get("division_request"):
            division_request = True
        elif payload and isinstance(payload, dict) and payload.get("delay") is not None:
            division_request = True
        elif payload and isinstance(payload, dict) and payload.get("daughter_count"):
            division_request = True

        if not division_request:
            return []

        pos = getattr(cell, "position", getattr(cell, "coord", (0,0)))
        template_id = getattr(cell, "template_id", params.get("template_id", None))
        clone_id = getattr(cell, "clone_id", params.get("clone_id", None))
        daughter_count = int(payload.get("daughter_count", params.get("daughter_count", 1))) if payload else int(params.get("daughter_count", 1))
        spawn_retry = int(params.get("spawn_retry", 3))
        backoff = int(params.get("spawn_retry_backoff_ticks", 1))
        strategy = params.get("spawn_strategy", "nearest_free")
        require_reservation = bool(params.get("require_reservation", True))

        daughters = []
        success_all = True

        for i in range(daughter_count):
            attempts = 0
            spawned = None
            while attempts <= spawn_retry:
                attempts += 1
                try_coord = _find_free(env, pos, strategy)
                if try_coord is None:
                    spawned = None
                    break
                reserved = True
                if require_reservation:
                    reserved = _reserve(env, try_coord)
                if not reserved:
                    # backoff and retry
                    if backoff:
                        try:
                            time.sleep(0)
                        except Exception:
                            pass
                    continue
                spawned = _spawn(env, template_id, try_coord, clone_id)
                if spawned:
                    if isinstance(spawned, (list, tuple)):
                        if spawned:
                            daughters.extend(list(spawned))
                    else:
                        daughters.append(spawned)
                if spawned:
                    break
                # spawn failed -> release and retry
                _release(env, try_coord)
                if backoff:
                    try:
                        time.sleep(0)
                    except Exception:
                        pass
            if spawned is None:
                success_all = False

        # bookkeeping
        try:
            if not hasattr(cell, "meta"):
                cell.meta = {}
            cell.meta["division_pending"] = False
            cell.meta["division_count"] = int(cell.meta.get("division_count", 0)) + (len(daughters) if daughters else 0)
        except Exception:
            pass

        # emit events
        if daughters:
            try:
                _emit(env, "divided", {"parent_id": getattr(cell, "id", None), "daughter_ids": daughters, "coords": None, "clone_id": clone_id, "tick": getattr(env, "tick", None)})
                _emit(env, "post_expansion", {"parent_id": getattr(cell, "id", None), "total_divisions_for_clone": params.get("max_total_divisions_per_clone", 0), "tick": getattr(env, "tick", None)})
            except Exception:
                pass

        action = {"name": "proliferate_attempt", "parent": getattr(cell, "id", None), "success": success_all, "daughters": daughters}
        return [action]
    except Exception:
        return []
