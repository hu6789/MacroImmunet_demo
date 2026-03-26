# IntentBuilder/behavior_interpreter.py

def interpret_behavior(b, bdef):
    """
    behavior → intent spec（纯语义，不涉及cell / fate）
    """

    if "output" not in bdef:
        return None

    out = bdef["output"]

    # === secretion ===
    if out["type"] == "secretion":
        return {
            "intent_type": "add_field",
            "target": out["target"],
            "base": b["drive"],
            "activation": b["activation"],
            "behavior_id": b["behavior_id"]
        }

    return None
