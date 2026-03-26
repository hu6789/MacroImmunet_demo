# Internalnet/node_engine.py

import os
import json


# =========================
# load graph
# =========================
def load_graph():

    base_dir = os.path.dirname(__file__)
    path = os.path.join(base_dir, "node", "graph", "graph_v0.2.json")

    with open(path, "r") as f:
        graph = json.load(f)

    return graph
# =========================
# load node definitions
# =========================
def load_nodes():

    base_dir = os.path.dirname(__file__)
    node_dir = os.path.join(base_dir, "node", "defs")

    node_defs = []

    # 🔥 遍历 defs 下面所有 json
    for root, _, files in os.walk(node_dir):
        for file in files:
            if not file.endswith(".json"):
                continue

            path = os.path.join(root, file)

            with open(path) as f:
                data = json.load(f)

                # 🔒 防御：确保是 node
                if "node_id" not in data:
                    continue

                node_defs.append(data)

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

# Internalnet/node_engine.py

import os
import json


# =========================
# load graph
# =========================
def load_graph():

    base_dir = os.path.dirname(__file__)
    path = os.path.join(base_dir, "node", "graph", "graph_v0.2.json")

    with open(path, "r") as f:
        graph = json.load(f)

    return graph
# =========================
# load node definitions
# =========================
def load_nodes():

    base_dir = os.path.dirname(__file__)
    node_dir = os.path.join(base_dir, "node", "defs")

    node_defs = []

    # 🔥 遍历 defs 下面所有 json
    for root, _, files in os.walk(node_dir):
        for file in files:
            if not file.endswith(".json"):
                continue

            path = os.path.join(root, file)

            with open(path) as f:
                data = json.load(f)

                # 🔒 防御：确保是 node
                if "node_id" not in data:
                    continue

                node_defs.append(data)

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
    node_defs_list = load_nodes()

    # 🔥 转 dict（核心修复）
    node_defs = {n["node_id"]: n for n in node_defs_list}

    current_state = dict(node_state)

    for _ in range(steps):

        new_state = dict(current_state)

        for node in graph["nodes"]:

            node_def = node_defs.get(node)
            if node_def is None:
                continue

            rule = node_def.get("update_rule", "weighted_sum")
            inputs = node_def.get("inputs", [])
            params = node_def.get("params", {})
            baseline = node_def.get("baseline", 0.0)

            # =========================
            # 🔥 rule dispatch
            # =========================

            if rule == "weighted_sum":

                weights = params.get("weights", [])
                value = 0.0

                for i, src in enumerate(inputs):
                    w = weights[i] if i < len(weights) else 1.0
                    value += current_state.get(src, 0.0) * w

                value += baseline

            elif rule == "threshold":

                threshold = params.get("threshold", 0.5)
                src = inputs[0] if inputs else None
                value = 1.0 if current_state.get(src, 0.0) > threshold else 0.0

            elif rule == "inverse_signal":

                weights = params.get("weights", [])
                value = 0.0

                for i, src in enumerate(inputs):
                    w = weights[i] if i < len(weights) else 1.0
                    value += current_state.get(src, 0.0) * w

                value = 1.0 - value

            elif rule == "baseline":

                value = baseline

            elif rule == "external":

                # 🔥 外部输入保持原值
                value = current_state.get(node, baseline)

            else:
                # fallback
                value = current_state.get(node, 0.0)

            # =========================
            # 🔥 decay（统一位置）
            # =========================

            tau = node_def.get("decay_tau", None)
            if tau:
                prev = current_state.get(node, 0.0)
                value = (prev * (tau - 1) + value) / tau

            # clamp
            value = max(0.0, min(1.0, value))

            new_state[node] = value

        current_state = new_state

    return current_state
