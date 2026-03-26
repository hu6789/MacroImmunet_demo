# Internalnet/run_simulation.py

import json
import os
from Internalnet.node_engine import run_node_graph
from Internalnet.HIR.hir_core import compute_HIR
from Internalnet.state.state_update import apply_state_update
# =========================
# 工具函数
# =========================

def load_behaviors(folder):
    behaviors = []

    for root, _, files in os.walk(folder):
        for file in files:
            if file.endswith(".json"):
                path = os.path.join(root, file)

                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                        behaviors.append(data)
                except Exception as e:
                    print(f"❌ JSON ERROR in: {path}")
                    raise e

    return behaviors
    
def compute_drive(behavior, node_state):
    """
    计算 drive（只支持 weighted_sum v0.2）
    """
    inputs = behavior["drive"]["inputs"]

    value = 0.0
    for item in inputs:
        node = item["node"]
        weight = item["weight"]
        value += node_state.get(node, 0.0) * weight

    return value
    
def apply_external_input(node_state, external_input):
    for k, v in external_input.items():
        node_state[k] = 0.9 * node_state.get(k, 0.0) + v

def apply_activation(behavior, drive):
    act = behavior["activation"]

    if act["mode"] == "deterministic":
        return 1.0 if drive >= act["threshold"] else 0.0

    elif act["mode"] == "probabilistic":
        # 简化 sigmoid
        import math
        x = drive - act["threshold"]
        slope = act.get("slope", 4.0)
        prob = 1 / (1 + math.exp(-slope * x))
        return prob

    return 0.0


def apply_HIR(drive, behavior, hir_output):

    if not behavior["hir_interaction"]["use_modifier"]:
        return drive

    group = behavior["group"]

    # 🚫 block
    if behavior["hir_interaction"]["blockable"]:
        if group in hir_output["blocks"]:
            if hir_output["blocks"][group]:
                return 0.0

    # ⚙️ scale
    if behavior["hir_interaction"]["use_global_scale"]:
        scale = hir_output["group_modifiers"].get(group, 1.0)
        drive *= scale

    return drive


# =========================
# 🧪 主流程
# =========================

def run_single_cell():

    # === 初始 node 状态（只初始化一次！）===
    node_state = {
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

    external_input = {
        "IFN_external": 0.3,
        "TNF_external": 0.2
    }
    
    BASE_DIR = os.path.dirname(__file__)
    behavior_dir = os.path.join(BASE_DIR, "behavior", "behavior_node")
    behaviors = load_behaviors(behavior_dir)

    print(f"\nLoaded {len(behaviors)} behaviors")

    # === 🔁 多 tick ===
    for tick in range(5):

        print(f"\n====================")
        print(f" TICK {tick}")
        print(f"====================")
        
        prev_state = dict(node_state)
        # === 构建 cell_state ===
        cell_state = {
            "ATP": node_state.get("ATP", 0.5),
            "stress": node_state.get("stress", 0.0),
            "damage": node_state.get("damage", 0.0),
            "viral_RNA": node_state.get("viral_RNA", 0.0)
        }
        # === external input 注入（必须在 graph 前）===
        apply_external_input(node_state, external_input)
        print("IFN_external:", node_state.get("IFN_external", 0))
        # === node_graph ===
        node_state = run_node_graph(node_state)
        print("ISG after graph:", node_state.get("ISG_program"))
        print("IFN_receptor:", node_state.get("IFN_receptor"))
        print("STAT1 after graph:", node_state.get("STAT1"))
        # === HIR ===
        hir_output = compute_HIR(cell_state)

        print("\nHIR:", hir_output)

        # === behavior ===
        behavior_outputs = []
        behavior_defs = {b["behavior_id"]: b for b in behaviors}
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

                print(f"{behavior['behavior_id']} → act={round(act,3)}")

        # === 状态更新 ===
        #node_state = apply_state_update(node_state, behavior_outputs, behavior_defs)

        # 👉 用统一 delta 打印
        print_delta(prev_state, node_state, ["ATP", "stress", "damage"])
        # clamp（防爆）
        for k in node_state:
            node_state[k] = max(0.0, min(1.0, node_state[k]))

        # === debug ===
        print("\nNODE STATE:")
        for k in ["ATP", "stress", "damage", "STAT1"]:
            print(f"{k}: {round(node_state[k],3)}")
def print_delta(prev, curr, keys):
    print("\nDELTA:")
    for k in keys:
        delta = curr[k] - prev[k]
        print(f"{k}: {round(delta,3)}")

if __name__ == "__main__":
    run_single_cell()
