# Internalnet/node_engine.py

import os
import json


# =========================
# load graph
# =========================

def load_graph():
    base_dir = os.path.dirname(__file__)
    path = os.path.join(base_dir, "node", "graph_v0.2.json")

    with open(path, "r") as f:
        return json.load(f)


# =========================
# load node definitions
# =========================

def load_nodes():
    base_dir = os.path.dirname(__file__)
    node_dir = os.path.join(base_dir, "node")

    node_defs = {}

    for root, _, files in os.walk(node_dir):
        for file in files:
            if file.endswith(".json") and file != "graph_v0.2.json":

                path = os.path.join(root, file)

                with open(path, "r") as f:
                    data = json.load(f)
                    node_defs[data["node_id"]] = data

    return node_defs


# =========================
# build adjacency
# =========================

def build_graph_structure(graph):

    parents = {}

    for node in graph["nodes"]:
        parents[node] = []

    for src, dst in graph["edges"]:
        parents[dst].append(src)

    return parents


# =========================
# run node graph（核心）
# =========================

def run_node_graph(node_state, steps=3):

    graph = load_graph()
    node_defs = load_nodes()

    # 当前状态（会不断更新）
    current_state = dict(node_state)

    for _ in range(steps):   # 🔥 多轮传播（关键）

        new_state = dict(current_state)

        for node in graph["nodes"]:

            if node not in node_defs:
                continue

            node_def = node_defs[node]

            rule = node_def.get("update_rule", "weighted_sum")

            if rule != "weighted_sum":
                continue

            inputs = node_def.get("inputs", [])
            weights = node_def.get("params", {}).get("weights", [])

            value = 0.0

            for i, src in enumerate(inputs):
                w = weights[i] if i < len(weights) else 1.0

                # 🔥 用 current_state（不是原始 node_state！）
                value += current_state.get(src, 0.0) * w

            # baseline
            value += node_def.get("baseline", 0.0)

            # clamp
            value = max(0.0, min(1.0, value))

            new_state[node] = value

        # 🔥 更新状态（进入下一轮）
        current_state = new_state

    return current_state
