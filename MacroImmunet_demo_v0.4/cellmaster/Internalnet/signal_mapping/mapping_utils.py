import json
import os

MAPPING_PATH = os.path.join(os.path.dirname(__file__), "receptor_mapping.json")

def load_mapping():
    with open(MAPPING_PATH) as f:
        return json.load(f)

def apply_mapping(external_field, node_state):
    mapping = load_mapping()
    for ext_key, cfg in mapping.items():
        if ext_key in external_field:
            val = external_field[ext_key]
            if cfg["type"] == "linear":
                node_state[cfg["node"]] = cfg["scale"] * val
            elif cfg["type"] == "hill":
                K = cfg["K"]
                n = cfg["n"]
                node_state[cfg["node"]] = val**n / (K + val**n)
    return node_state
