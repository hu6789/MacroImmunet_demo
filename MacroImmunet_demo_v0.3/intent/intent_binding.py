# IntentBuilder/intent_binding.py
GROUP_SCALE = {
    "cytokine_secretion": 10.0,
    "metabolism": 1.0,
    "stress_response": 0.5,
    "cell_fate": 1.0
}
def bind_intent(spec, cell, behavior_defs):
    """
    spec → 最终 intent（绑定 cell / 参数）
    """

    bdef = behavior_defs[spec["behavior_id"]]

    # === add_field ===
    if spec["intent_type"] == "add_field":

        capacity = cell.feature_params.get(
            bdef["cell_influence"]["capacity_param"], 1.0
        )

        sensitivity = cell.feature_params.get(
            bdef["cell_influence"]["sensitivity_param"], 1.0
        )

        scale = bdef.get("output", {}).get("scale", 1.0)

        value = (
            spec["base"]
            * spec["activation"]
            * capacity
            * sensitivity
            * scale
        )

        # ✅ NEW：group scaling
        group = bdef.get("group", None)
        group_scale = GROUP_SCALE.get(group, 1.0)

        value *= group_scale
        if value < 1e-4:
            return None
        
        MAX_OUTPUT = 1.0

        value = min(value, MAX_OUTPUT)

        return {
            "type": "add_field",
            "cell_id": cell.cell_id,
            "target": spec["target"],
            "value": value
        }

    return None
