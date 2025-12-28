# cell_master/behaviour_library/natural_apoptosis.py
"""
Natural apoptosis / programmed cell death behavior for demo.

Signature:
  def natural_apoptosis_v1(cell, env, params=None, payload=None, rng=None, **kw) -> list[action]

Behavior semantics (demo-minimum):
 - May trigger apoptosis with probability params['probability'] (default 1.0)
 - When apoptosing:
     - set cell.state / cell.meta['state'] -> 'APOPTOTIC'
     - mark cell.meta['dying'] = True and optionally 'death_cause'
     - emit event "apoptosis_started" (payload includes cell_id, tick, cause)
 - Optionally release internal antigen/viral load:
     - uses cell.meta['viral_load'] or cell.meta['antigen_load'] as internal load
     - spill fraction controlled by params.spill_fraction (default 1.0)
     - min_internal_for_spill prevents tiny spills
     - write into Field_Antigen_Density (via env.add_to_field) if available,
       otherwise try env.spawn_antigen(coord, count)
     - emit "released" event if any release attempted
 - Return a list of actions describing what happened. Actions use the demo convention:
     {"name": "...", "payload": {...}}
 - Defensive: never raise; swallow engine errors.
"""

from typing import Any, Dict, List
import random
from math import floor

def _get_internal_load(cell) -> float:
    """Try multiple meta keys for internal antigen/viral load."""
    try:
        meta = getattr(cell, "meta", {}) or {}
        # prefer viral_load, then antigen_load
        vl = meta.get("viral_load")
        if vl is None:
            vl = meta.get("antigen_load")
        if vl is None:
            # fallback attribute
            vl = getattr(cell, "viral_load", None)
        if vl is None:
            vl = getattr(cell, "antigen_load", None)
        return float(vl or 0.0)
    except Exception:
        try:
            return float(getattr(cell, "viral_load", 0.0) or 0.0)
        except Exception:
            return 0.0

def _set_internal_load(cell, new_val: float) -> None:
    """Attempt to write back to meta or attribute."""
    try:
        if not hasattr(cell, "meta") or cell.meta is None:
            cell.meta = {}
        if isinstance(cell.meta, dict):
            # prefer viral_load key if existed before, else antigen_load
            if "viral_load" in cell.meta or hasattr(cell, "viral_load"):
                cell.meta["viral_load"] = float(new_val)
            else:
                cell.meta["antigen_load"] = float(new_val)
            return
    except Exception:
        pass
    try:
        setattr(cell, "viral_load", float(new_val))
    except Exception:
        try:
            setattr(cell, "antigen_load", float(new_val))
        except Exception:
            pass

def _emit(env: Any, name: str, payload: Dict[str, Any]) -> None:
    try:
        if hasattr(env, "emit_event") and callable(env.emit_event):
            env.emit_event(name, payload)
    except Exception:
        pass

def natural_apoptosis_v1(cell, env, params=None, payload=None, rng=None, **kw) -> List[Dict[str, Any]]:
    params = params or {}
    payload = payload or {}
    rng = rng or random.Random()

    prob = float(payload.get("probability", params.get("probability", 1.0) or 1.0))
    spill_fraction = float(payload.get("spill_fraction", params.get("spill_fraction", 1.0) or 1.0))
    min_internal_for_spill = float(payload.get("min_internal_for_spill", params.get("min_internal_for_spill", 0.5)))
    burst_yield = float(payload.get("burst_yield", params.get("burst_yield", None) or 0.0))
    cause = payload.get("cause", params.get("cause", "natural"))

    actions: List[Dict[str, Any]] = []

    # decide whether apoptosis actually triggers
    try:
        if prob < 1.0 and rng.random() >= prob:
            # considered but not executed: return empty (no event)
            return []
    except Exception:
        # if RNG fails, proceed
        pass

    # mark cell dying / set state
    try:
        old_state = getattr(cell, "state", None)
        try:
            setattr(cell, "state", "APOPTOTIC")
        except Exception:
            # fallback to meta
            if not hasattr(cell, "meta") or cell.meta is None:
                cell.meta = {}
            cell.meta["state"] = "APOPTOTIC"
        # mirror into meta
        try:
            if not hasattr(cell, "meta") or cell.meta is None:
                cell.meta = {}
            cell.meta["state"] = "APOPTOTIC"
            cell.meta["dying"] = True
            cell.meta["death_cause"] = cause
        except Exception:
            pass
    except Exception:
        old_state = None

    tick = getattr(env, "tick", None)

    # emit apoptosis start event
    evt_payload = {"cell_id": getattr(cell, "id", None), "old_state": old_state, "new_state": "APOPTOTIC", "cause": cause, "tick": tick}
    _emit(env, "apoptosis_started", evt_payload)
    actions.append({"name": "apoptosis_started", "payload": evt_payload})

    # attempt to spill internal load (viral / antigen) if present
    internal = _get_internal_load(cell)
    spilled_amount = 0.0
    if internal and internal > 0.0 and internal >= min_internal_for_spill:
        # compute planned spill: if burst_yield provided use min(burst_yield, fraction*internal)
        if burst_yield and burst_yield > 0.0:
            planned = min(burst_yield, internal * spill_fraction)
        else:
            planned = internal * spill_fraction
        planned = max(0.0, planned)
        # for field we can write float; for spawn we convert to int
        spawn_count = int(floor(planned))

        # choose coordinate
        coord = getattr(cell, "coord", None) or getattr(cell, "position", None)

        written = False
        try:
            if hasattr(env, "add_to_field") and callable(env.add_to_field):
                # try float first
                try:
                    env.add_to_field("Field_Antigen_Density", coord, planned)
                    actions.append({"name": "add_to_field", "payload": {"field": "Field_Antigen_Density", "coord": coord, "amount": planned}})
                    written = True
                    spilled_amount = planned
                except TypeError:
                    # fallback to integer count
                    try:
                        env.add_to_field("Field_Antigen_Density", coord, spawn_count)
                        actions.append({"name": "add_to_field", "payload": {"field": "Field_Antigen_Density", "coord": coord, "amount": spawn_count}})
                        written = True
                        spilled_amount = float(spawn_count)
                    except Exception:
                        written = False
                except Exception:
                    written = False
        except Exception:
            written = False

        if not written:
            # try spawn_antigen(coord, count) for engines with particle API
            try:
                if hasattr(env, "spawn_antigen") and callable(env.spawn_antigen):
                    env.spawn_antigen(coord, spawn_count)
                    actions.append({"name": "spawn_antigen", "payload": {"coord": coord, "count": spawn_count}})
                    written = True
                    spilled_amount = float(spawn_count)
            except Exception:
                written = False

        # reduce internal load in cell by spilled amount
        try:
            new_internal = max(0.0, internal - spilled_amount)
            _set_internal_load(cell, new_internal)
        except Exception:
            pass

        # emit released event describing the spill
        release_evt = {"cell_id": getattr(cell, "id", None), "yield": spilled_amount, "coord": coord, "tick": tick, "cause": cause}
        _emit(env, "released", release_evt)
        actions.append({"name": "released", "payload": release_evt})

    # optionally create a DAMP label / event to signal danger
    create_damp = bool(payload.get("create_damp", params.get("create_damp", True)))
    if create_damp:
        damp_payload = {"cell_id": getattr(cell, "id", None), "tick": tick, "cause": cause}
        _emit(env, "DAMP_emitted", damp_payload)
        actions.append({"name": "DAMP_emitted", "payload": damp_payload})

    # final standardized event to mark apoptosis finished/registered (demo-level)
    finished_payload = {"cell_id": getattr(cell, "id", None), "spilled": spilled_amount, "tick": tick}
    _emit(env, "apoptosis_registered", finished_payload)
    actions.append({"name": "apoptosis_registered", "payload": finished_payload})

    return actions

