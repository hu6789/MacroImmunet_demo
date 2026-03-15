# behaviors_impl/proinflammatory.py
import math
from typing import Any, Dict, List

def proinflammatory_program_v1(cell, env, params=None, payload=None, **kw) -> List[Dict]:
    """
    Emit intents to increase TNF/IL12 secretion and emit a regulate intent for adhesion.
    Returns list of actions for compatibility.
    """
    params = params or {}
    pld = payload or {}
    # resolve parameters
    tnf_factor = float(pld.get("tnf_factor", params.get("increase_tnf_factor", 0.5)))
    tnf_duration = int(pld.get("tnf_duration", params.get("tnf_duration", 24)))
    adhesion_fold = float(pld.get("adhesion_fold", params.get("adhesion_fold", 1.2)))
    adhesion_duration = int(pld.get("adhesion_duration", params.get("adhesion_duration", 48)))

    actions = []

    # Emit TNF secrete intent
    tnf_payload = {"molecule": "TNF", "rate_per_tick": tnf_factor, "duration_ticks": tnf_duration}
    try:
        if hasattr(env, "emit_intent"):
            env.emit_intent("secrete", tnf_payload)
        else:
            actions.append({"intent": "secrete", "payload": tnf_payload})
    except Exception:
        # defensive: swallow env errors
        actions.append({"intent": "secrete", "payload": tnf_payload})

    # Emit IL12 secrete intent (smaller)
    il12_payload = {"molecule": "IL12", "rate_per_tick": float(tnf_factor) / 2.0, "duration_ticks": tnf_duration}
    try:
        if hasattr(env, "emit_intent"):
            env.emit_intent("secrete", il12_payload)
        else:
            actions.append({"intent": "secrete", "payload": il12_payload})
    except Exception:
        actions.append({"intent": "secrete", "payload": il12_payload})

    # Emit regulate intent for adhesion
    reg_payload = {"target": "adhesion_molecules", "fold_change": adhesion_fold, "duration_ticks": adhesion_duration}
    try:
        if hasattr(env, "emit_intent"):
            env.emit_intent("regulate", reg_payload)
        else:
            actions.append({"intent": "regulate", "payload": reg_payload})
    except Exception:
        actions.append({"intent": "regulate", "payload": reg_payload})

    return actions

