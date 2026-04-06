# Internalnet/library/node_library.py

import os
import json


class NodeLibrary:

    def __init__(self):
        self.nodes = {}

    def load(self, base_dir):

        node_dir = os.path.join(base_dir, "node", "defs")

        for root, _, files in os.walk(node_dir):
            for file in files:
                if not file.endswith(".json"):
                    continue

                path = os.path.join(root, file)

                with open(path, "r") as f:
                    data = json.load(f)

                    nid = data.get("node_id")
                    if nid:
                        self.nodes[nid] = data

    def get(self, node_id):
        return self.nodes.get(node_id)

    def all(self):
        return self.nodes
