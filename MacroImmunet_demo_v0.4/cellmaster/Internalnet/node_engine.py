# Internalnet/node_engine.py

import os
import json

from .signal_mapping.mapping_utils import apply_mapping
# =========================
# load node definitions
# =========================
def load_nodes():

    base_dir = os.path.dirname(__file__)
    node_dir = os.path.join(base_dir, "node", "defs")

    node_defs = []

    for root, _, files in os.walk(node_dir):
        for file in files:
            if not file.endswith(".json"):
                continue

            path = os.path.join(root, file)

            with open(path) as f:
                data = json.load(f)

                if "node_id" not in data:
                    continue

                node_defs.append(data)

    return node_defs
def collect_emitters(node_state, node_defs):

    emitted = {}

    for node_id, node_def in node_defs.items():

        if node_def.get("io_role") != "emitter":
            continue

        key = node_def.get("external_key")
        if not key:
            continue

        value = node_state.get(node_id, 0.0)

        if value > 0:
            emitted[key] = emitted.get(key, 0.0) + value

    return emitted

def build_node_inputs_from_graph(graph):
    inputs_map = {}

    for edge in graph.get("node_edges", []):
        src = edge["source"]
        tgt = edge["target"]
        w = edge.get("weight", 1.0)

        inputs_map.setdefault(tgt, []).append({
            "node": src,
            "weight": w
        })

    return inputs_map
# =========================
# run node graph（核心）
# =========================
def resolve_update_order(graph):
    return list(graph.get("nodes", {}).keys())

def run_node_graph(node_state, graph, node_defs, external_field, receptor_params=None):
    for k, v in external_field.items():
        node_state[k] = v

    update_order = resolve_update_order(graph)

    # ✅ 1️⃣ external → receptor mapping（只做一次）
    node_state = apply_mapping(external_field, node_state)

    # ✅ 2️⃣ 构建 inputs_map
    inputs_map = build_node_inputs_from_graph(graph)

    current_state = dict(node_state)

    # ✅ 3️⃣ 真正的 graph propagation（核心！！！）
    for node in update_order:
        if node in external_field:
            continue

        node_def = node_defs.get(node)
        if not node_def:
            continue

        # 🔥 核心：receptor 不参与更新
        if node_def.get("type") == "receptor":
            continue

        inputs = inputs_map.get(node, [])

        values = []
        for inp in inputs:
            src = inp["node"]
            w = inp.get("weight", 1.0)
            values.append(current_state.get(src, 0.0) * w)

        value = sum(values)

        # clamp
        value = max(0.0, min(1.0, value))

        current_state[node] = value
    print("BEFORE mapping:", node_state)
    print("EXTERNAL:", external_field)
    return current_state, update_order

