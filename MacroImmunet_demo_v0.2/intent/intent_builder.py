def build_intents(behavior_outputs, cell_id):

    intents = []

    for b in behavior_outputs:

        behavior_id = b["behavior_id"]
 
        if behavior_id.startswith("secrete_"):
            intent_type = "secretion"
            target = behavior_id.replace("secrete_", "")

        elif behavior_id in ["glycolysis_upregulation", "autophagy"]:
            intent_type = "state_update"
            target = behavior_id

        elif behavior_id in ["apoptosis_commit", "necrosis"]:
            intent_type = "fate"
            target = behavior_id
        elif behavior_id in ["cell_cycle_arrest"]:
            intent_type = "state_update"
            target = behavior_id

        else:
            intent_type = "state_update"
            target = behavior_id

        intents.append({
            "cell_id": cell_id,
            "type": intent_type,
            "target": target,
            "strength": b["activation"],
            "metadata": {
                "source_behavior": behavior_id
            }
        })
    return intents
