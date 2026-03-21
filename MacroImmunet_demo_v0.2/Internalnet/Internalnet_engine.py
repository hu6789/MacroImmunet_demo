# Internalnet/Internalnet_engine.py

import os
import json
import math

from Internalnet.HIR.hir_core import compute_HIR
from Internalnet.node_engine import run_node_graph

# =========================
# 工具函数（从 run_simulation 复制）
# =========================

def load_behaviors(folder):
    behaviors = []

    for root, _, files in os.walk(folder):
        for file in files:
            if file.endswith(".json"):
                path = os.path.join(root, file)

                with open(path, "r") as f:
                    data = json.load(f)
                    behaviors.append(data)

    return behaviors


def compute_drive(behavior, node_state):
    value = 0.0
    for item in behavior["drive"]["inputs"]:
        node = item["node"]
        weight = item["weight"]
        value += node_state.get(node, 0.0) * weight
    return value


def apply_activation(behavior, drive):
    act = behavior["activation"]

    if act["mode"] == "deterministic":
        return 1.0 if drive >= act["threshold"] else 0.0

    elif act["mode"] == "probabilistic":
        x = drive - act["threshold"]
        slope = act.get("slope", 4.0)
        return 1 / (1 + math.exp(-slope * x))

    return 0.0


def apply_HIR(drive, behavior, hir_output):

    if not behavior["hir_interaction"]["use_modifier"]:
        return drive

    group = behavior["group"]

    if behavior["hir_interaction"]["blockable"]:
        if group in hir_output["blocks"]:
            if hir_output["blocks"][group]:
                return 0.0

    if behavior["hir_interaction"]["use_global_scale"]:
        scale = hir_output["group_modifiers"].get(group, 1.0)
        drive *= scale

    return drive


# =========================
# 🧠 核心接口
# =========================

def run_internalnet(cell, external_input=None):

    # 拷贝内部状态
    node_state = dict(cell.node_state)

    # 注入外部信号
    if external_input:
        for k, v in external_input.items():
            node_state[k] = node_state.get(k, 0.0) + v

    updated = run_node_graph(node_state)

    external_keys = set(external_input.keys()) if external_input else set()

    # 覆盖所有计算节点（但保留 external_input）
    for k, v in updated.items():
        if k not in external_keys:
            node_state[k] = v

    # HIR 输入
    cell_state = {
        "ATP": node_state.get("ATP", 0.5),
        "stress": node_state.get("stress", 0.0),
        "damage": node_state.get("damage", 0.0),
        "viral_RNA": node_state.get("viral_RNA", 0.0)
    }

    hir_output = compute_HIR(cell_state)

    # behavior 计算（保持你原来的）

    # === behaviors ===
    BASE_DIR = os.path.dirname(__file__)
    behavior_dir = os.path.join(BASE_DIR, "behavior", "behavior_node")

    behaviors = load_behaviors(behavior_dir)

    behavior_outputs = []

    for behavior in behaviors:

        # gate
        gate_ok = True
        for g in behavior.get("gate", []):
            if node_state.get(g["node"], 0.0) < g["threshold"]:
                gate_ok = False
                break

        if not gate_ok:
            continue

        # drive
        drive = compute_drive(behavior, node_state)

        # HIR
        drive = apply_HIR(drive, behavior, hir_output)

        # activation
        act = apply_activation(behavior, drive)

        if act > 0.3:
            behavior_outputs.append({
                "behavior_id": behavior["behavior_id"],
                "activation": act,
                "drive": drive
            })

    print("before:", cell.node_state)
    print("after:", node_state)
    for k in node_state:
        if external_input and k in external_input:
            continue  # 
        cell.node_state[k] = node_state[k]
    behavior_outputs.append({
        "behavior_id": "secrete_IFN",
        "activation": 1.0,
        "drive": 1.0
    })

    return behavior_outputs
