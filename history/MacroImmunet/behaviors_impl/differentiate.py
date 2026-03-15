# behaviors_impl/differentiate.py
"""
Behavior implementation for differentiate_v1.

Compatibility notes:
- Quick-path: if payload or params contains 'target_state' (and optionally 'probability'),
  will set cell.state -> emit both 'state_changed' and 'differentiated' events and return actions.
- Rules-based: reads params['differentiation'] or payload['differentiation'] or cell.meta['differentiation'],
  chooses according to probabilities/gating, writes canonical markers (cell.meta['effector_type'], phenotype),
  may set cell.state if rule contains 'target_state'/'state' -> emits events 'state_changed' and 'differentiated'.
- Uses rng argument (or deterministic random.Random if provided) for deterministic tests.
"""
import random
from typing import Any, Dict

def _choose_rule(rules: Dict[str, Any], rng):
    if not rules:
        return None
    entries = []
    total = 0.0
    for name, rule in rules.items():
        p = 0.0
        if isinstance(rule, dict):
            p = float(rule.get("prob", 0.0) or 0.0)
        else:
            try:
                p = float(rule)
            except Exception:
                p = 0.0
        if p < 0.0:
            p = 0.0
        entries.append((name, p, rule))
        total += p
    # deterministic if prob >= 1
    for name, p, rule in entries:
        if p >= 1.0:
            return name, rule
    if total <= 0.0:
        return None
    r = rng.random()
    cumul = 0.0
    for name, p, rule in entries:
        cumul += p / total
        if r <= cumul:
            return name, rule
    return entries[-1][0], entries[-1][2]

def _normalize_behavior_name(b):
    if not b or not isinstance(b, str):
        return None
    return b.rsplit(".", 1)[0]

def _emit(env, name, payload):
    try:
        if hasattr(env, "emit_event") and callable(env.emit_event):
            env.emit_event(name, payload)
    except Exception:
        pass

def _maybe_set_state_and_emit(cell, env, new_state, cause=None):
    """
    Helper: set cell.state (try attribute then meta), and emit state_changed event with old/new.
    """
    old_state = getattr(cell, "state", None)
    try:
        setattr(cell, "state", new_state)
    except Exception:
        try:
            if not hasattr(cell, "meta") or cell.meta is None:
                cell.meta = {}
            cell.meta["state"] = new_state
        except Exception:
            pass
    # also mirror into meta if possible
    try:
        if not hasattr(cell, "meta") or cell.meta is None:
            cell.meta = {}
        cell.meta["state"] = new_state
    except Exception:
        pass

    # emit state_changed event (tests expect this)
    evt = {"cell_id": getattr(cell, "id", None), "old_state": old_state, "new_state": new_state, "cause": cause, "tick": getattr(env, "tick", None)}
    _emit(env, "state_changed", evt)
    return old_state, new_state

def differentiate_v1(cell, env, params=None, payload=None, rng=None, **kw):
    params = params or {}
    payload = payload or {}
    rng = rng or random.Random()

    # --- Quick-path: explicit target_state in payload or params ---
    tgt = payload.get("target_state") or params.get("target_state")
    if tgt:
        prob = float(payload.get("probability", params.get("probability", 1.0) or 1.0))
        if prob >= 1.0 or rng.random() < prob:
            # set state and emit state_changed
            _maybe_set_state_and_emit(cell, env, tgt, cause=payload.get("cause"))
            # mirror effector markers
            try:
                if not hasattr(cell, "meta") or cell.meta is None:
                    cell.meta = {}
                cell.meta["effector_type"] = tgt
                if isinstance(tgt, str) and tgt.lower().startswith("th"):
                    cell.meta["phenotype"] = tgt
            except Exception:
                pass
            # emit differentiated
            evt_payload = {"cell_id": getattr(cell, "id", None), "fate": tgt, "cause": payload.get("cause"), "tick": getattr(env, "tick", None)}
            _emit(env, "differentiated", evt_payload)
            return [{"name": "differentiated", "payload": evt_payload}]
        else:
            return []

    # --- Rules-based differentiation ---
    diff_rules = None
    if isinstance(params.get("differentiation"), dict):
        diff_rules = params.get("differentiation")
    elif isinstance(params.get("differentiation_rules"), dict):
        diff_rules = params.get("differentiation_rules")
    if diff_rules is None and isinstance(payload.get("differentiation"), dict):
        diff_rules = payload.get("differentiation")
    if diff_rules is None:
        cm = getattr(cell, "meta", {}) or {}
        if isinstance(cm.get("differentiation"), dict):
            diff_rules = cm.get("differentiation")

    if not diff_rules:
        return []

    # context/gating
    cm = getattr(cell, "meta", {}) or {}
    last_scan = cm.get("last_scan", {}) or {}
    best_affinity = float(last_scan.get("best_affinity", 0.0) or 0.0)
    recognized = bool(last_scan.get("recognized", False))
    co_stim = getattr(cell, "co_stim", None)
    if co_stim is None:
        co_stim = cm.get("co_stim", None)

    gated = {}
    for fate_name, rule in diff_rules.items():
        r = rule if isinstance(rule, dict) else {"prob": float(rule or 0.0)}
        min_aff = float(r.get("min_affinity", 0.0) or 0.0)
        min_cost = r.get("min_co_stim", None)
        if best_affinity < min_aff:
            continue
        if min_cost is not None:
            try:
                if float(min_cost) > (float(co_stim) if co_stim is not None else 0.0):
                    continue
            except Exception:
                pass
        gated[fate_name] = r

    candidate_rules = gated if gated else diff_rules

    chosen = _choose_rule(candidate_rules, rng)
    if not chosen:
        return []

    fate_name, fate_rule = chosen if isinstance(chosen, tuple) else (chosen, candidate_rules.get(chosen))
    if isinstance(fate_rule, (int, float)):
        fate_rule = {"prob": float(fate_rule)}

    require_recognized = bool(fate_rule.get("require_recognized", False))
    if require_recognized and not recognized:
        return []

    prob = float(fate_rule.get("prob", 1.0))
    if prob < 1.0 and rng.random() >= prob:
        return []

    canonical = fate_name if isinstance(fate_name, str) else str(fate_name)

    # write canonical markers
    try:
        if not hasattr(cell, "meta") or cell.meta is None:
            cell.meta = {}
        cell.meta["effector_type"] = canonical
        if canonical.lower().startswith("th"):
            cell.meta["phenotype"] = canonical
        try:
            setattr(cell, "effector_type", canonical)
        except Exception:
            pass
    except Exception:
        pass

    # if rule supplies a target_state, set it and emit state_changed
    target_state_rule = fate_rule.get("target_state") or fate_rule.get("state")
    if target_state_rule:
        _maybe_set_state_and_emit(cell, env, target_state_rule, cause=fate_rule.get("cause"))

    # build actions based on rule behaviors
    actions = []
    behs = fate_rule.get("behaviors") or fate_rule.get("actions") or []
    if isinstance(behs, (list, tuple)):
        for b in behs:
            nm = _normalize_behavior_name(b)
            if nm:
                actions.append({"name": nm, "payload": {"cell_id": getattr(cell, "id", None), "fate": canonical}})

    # standardized differentiated action & event
    actions.insert(0, {"name": "differentiated", "payload": {"cell_id": getattr(cell, "id", None), "fate": canonical}})
    evt_payload = {"cell_id": getattr(cell, "id", None), "fate": canonical, "best_affinity": best_affinity, "tick": getattr(env, "tick", None)}
    _emit(env, "differentiated", evt_payload)

    return actions

