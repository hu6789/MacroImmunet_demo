# Internalnet/library/behavior_library.py

import os
import json


class BehaviorLibrary:

    def __init__(self):
        self.behaviors = {}

    def load(self, base_dir):

        behavior_dir = os.path.join(base_dir, "behavior", "behavior_node")

        for root, _, files in os.walk(behavior_dir):
            for file in files:
                if not file.endswith(".json"):
                    continue

                path = os.path.join(root, file)

                with open(path, "r") as f:
                    data = json.load(f)

                    bid = data.get("behavior_id")
                    if bid:
                        self.behaviors[bid] = data

    def get(self, behavior_id):
        return self.behaviors.get(behavior_id)

    def all(self):
        return self.behaviors
