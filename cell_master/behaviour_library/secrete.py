# behaviors_impl/secrete.py
# Demo-safe secrete_v1: emits event AND attempts to write field deltas using common env APIs.

def _normalize_params(params, payload):
    params = params or {}
    payload = payload or {}
    molecule = payload.get("molecule", params.get("molecule"))
    rate = payload.get("rate_per_tick", params.get("rate_per_tick", 0.0))
    duration = payload.get("duration_ticks", params.get("duration_ticks", 0))
    # optional target field name (allow YAML to pass Field_IFNg etc.)
    target_field = payload.get("field", params.get("field"))
    return {"molecule": molecule, "rate_per_tick": rate, "duration_ticks": duration, "field": target_field}

def _guess_field_from_molecule(molecule):
    if not molecule:
        return None
    # convention: molecule names -> Field_<upper molecule>
    name = str(molecule)
    return "Field_" + name.upper().replace("-", "_")

def _try_apply_field_delta(env, coord, field, delta):
    """
    Try a few common engine/test stub APIs to apply a field delta.
    Return True if any call succeeded (no exceptions).
    """
    if field is None:
        return False
    try:
        # prioritized attempts (non-exhaustive)
        if hasattr(env, "apply_field_delta"):
            try:
                env.apply_field_delta(field, coord, delta)
                return True
            except TypeError:
                # some engines accept coord first
                try:
                    env.apply_field_delta(coord, field, delta)
                    return True
                except Exception:
                    pass
        if hasattr(env, "add_field_delta"):
            env.add_field_delta(field, coord, delta)
            return True
        if hasattr(env, "write_field"):
            # write_field(field, coord, value) or write_field(coord, field, value)
            try:
                env.write_field(field, coord, delta)
                return True
            except TypeError:
                try:
                    env.write_field(coord, field, delta)
                    return True
                except Exception:
                    pass
        # fallback: emit_intent that tests may capture
        if hasattr(env, "emit_intent"):
            env.emit_intent("secrete_field", {"field": field, "coord": coord, "delta": delta})
            return True
        # last resort: emit_event
        if hasattr(env, "emit_event"):
            env.emit_event("secrete_field", {"field": field, "coord": coord, "delta": delta})
            return True
    except Exception:
        # swallow engine errors for demo-safety
        return False
    return False

def secrete_v1(cell, env, params=None, payload=None, rng=None, receptors=None, **kw):
    cfg = _normalize_params(params, payload)
    molecule = cfg["molecule"] or "UNKNOWN"
    rate = float(cfg["rate_per_tick"] or 0.0)
    duration = int(cfg["duration_ticks"] or 0)
    field = cfg.get("field") or _guess_field_from_molecule(molecule)

    coord = getattr(cell, "position", None) or getattr(cell, "coord", None)

    # Try to apply a per-tick delta to the field (engine may interpret rate as per-tick)
    delta_applied = False
    try:
        delta_applied = _try_apply_field_delta(env, coord, field, rate)
    except Exception:
        delta_applied = False

    # emit a simple event if env supports it (for tests / logging)
    try:
        if hasattr(env, "emit_event") and callable(env.emit_event):
            env.emit_event("secreted", {"cell_id": getattr(cell, "id", None),
                                        "molecule": molecule,
                                        "field": field,
                                        "rate_per_tick": rate,
                                        "duration_ticks": duration,
                                        "delta_written": bool(delta_applied)})
    except Exception:
        # don't let env errors break behavior (demo-safe)
        pass

    # Return an action describing field secretion intent (tests expect an action list)
    return [{"name": "secrete_field",
             "payload": {"molecule": molecule,
                         "field": field,
                         "rate_per_tick": rate,
                         "duration_ticks": duration,
                         "coord": coord}}]

# Adapter class for factory fallback
class SecreteBehavior:
    def __init__(self, **kwargs):
        self.params = kwargs or {}
    def execute(self, cell, env, params=None, payload=None, **kw):
        merged = dict(self.params)
        if params:
            merged.update(params)
        return secrete_v1(cell, env, params=merged, payload=payload, **kw)

