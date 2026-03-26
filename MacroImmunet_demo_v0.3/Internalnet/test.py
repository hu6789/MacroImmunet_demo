import os
from Internalnet.Internalnet_engine_v0 import run_internalnet_v0

class DummyCell:
    def __init__(self):
        self.node_state = {
            "IRF3": 0.7,
            "NFkB": 0.6,
            "STAT1": 0.5,
            "ROS": 0.4,
            "stress": 0.3,
            "damage": 0.2,
            "caspase": 0.3,
            "autophagy_signal": 0.5,
            "translation_stress": 0.4,
            "ATP": 0.6,
            "viral_RNA": 0.7
        }

def load_behaviors(folder):
    import json
    behaviors = []
    for root, _, files in os.walk(folder):
        for file in files:
            if file.endswith(".json"):
                with open(os.path.join(root, file), "r") as f:
                    behaviors.append(json.load(f))
    return behaviors


def run_test():

    cell = DummyCell()

    BASE_DIR = os.path.dirname(__file__)
    behavior_dir = os.path.join(BASE_DIR, "behavior", "behavior_node")
    behaviors = load_behaviors(behavior_dir)

    for tick in range(5):
        print(f"\n=== TICK {tick} ===")

        outputs = run_internalnet_v0(
            cell,
            behaviors,
            external_input={
                "IFN_external": 0.3,
                "TNF_external": 0.2
            }
        )

        print("Outputs:", outputs)
        print("STAT1:", cell.node_state.get("STAT1"))


if __name__ == "__main__":
    run_test()
