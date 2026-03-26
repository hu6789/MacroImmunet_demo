import json
import os

def load_rules():
    base_dir = os.path.dirname(__file__)
    path = os.path.join(base_dir, "state_rules.json")

    with open(path, "r") as f:
        data = json.load(f)

    return {r["behavior_id"]: r for r in data}

def apply_state_update(node_state, behavior_outputs, behavior_defs):

    new_state = dict(node_state)

    for b in behavior_outputs:
        bid = b["behavior_id"]
        act = b["activation"]

        if bid not in behavior_defs:
            continue

        effects = behavior_defs[bid].get("state_effects", {})

        for k, delta in effects.items():
            new_state[k] = new_state.get(k, 0.0) + delta * act

    return new_state
