# behaviors_impl/antigen_invasion.py
"""
Simple antigen invasion implementation used by tests.
Provides:
 - antigen_invasion_v1: simpler wrapper (kept for compatibility)
 - attempt_entry: full entry function expected by some YAMLs/tests
"""

import random

def _ensure_meta(cell):
    if not hasattr(cell, "meta") or cell.meta is None:
        cell.meta = {}

def antigen_invasion_v1(cell, env, params=None, payload=None, **kw):
    # keep a simple deterministic wrapper for tests that call antigen_invasion_v1
    return attempt_entry(cell, env, params=params, payload=payload, **kw)

def attempt_entry(cell, env, params=None, payload=None, **kw):
    """
    Attempt antigen entry / infection.
    - Consumes 'consumption_on_infection_units' from params (if present) into cell.meta['viral_load'].
    - Honors probability in payload/params.
    - Returns actions list and emits events if env.emit_event present.
    """
    params = params or {}
    payload = payload or {}

    base_scaler = float(params.get("base_entry_scaler", 1.0))
    consumption_units = float(params.get("consumption_on_infection_units", 1.0))
    default_infectivity = float(params.get("default_infectivity_scale", 1.0))
    prob = float(payload.get("probability", params.get("probability", 1.0)))

    do_infect = (prob >= 1.0) or random.random() < prob

    actions = []
    if not do_infect:
        return actions

    # ensure cell.meta exists
    _ensure_meta(cell)

    # increase viral load by consumption_units * base_scaler
    added = consumption_units * base_scaler * default_infectivity
    prev = float(cell.meta.get("viral_load", 0.0))
    cell.meta["viral_load"] = prev + added

    # mark infected state
    cell.state = params.get("infected_state", "Infected")

    # emit an event for infection if env supports it
    evt_payload = {"cell_id": getattr(cell, "id", None), "antigen_id": payload.get("antigen_id"), "added": added, "tick": None}
    try:
        if hasattr(env, "emit_event"):
            env.emit_event("infected", evt_payload)
    except Exception:
        pass

    actions.append({"name": "infected", "payload": {"cell_id": getattr(cell, "id", None), "added": added}})
    return actions

