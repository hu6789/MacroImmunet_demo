# Internalnet/run_simulation.py

import json
import os

from Internalnet.HIR.hir_core import compute_HIR
from intent.intent_builder import build_intents

# =========================
# 工具函数
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

    # === 1️⃣ 模拟 node 状态 ===
    node_state = {
        "IRF3": 0.7,
        "NFkB": 0.6,
        "STAT1": 0.5,
        "ROS": 0.4,
        "stress": 0.3,
        "damage": 0.2,
        "caspase": 0.3,
        "autophagy_signal": 0.5,
        "translation_stress": 0.4
    }

    # === 2️⃣ cell_state ===
    cell_state = {
        "ATP": 0.6,
        "stress": node_state["stress"],
        "damage": node_state["damage"],
        "viral_RNA": 0.7
    }

    # === 3️⃣ HIR ===
    hir_output = compute_HIR(cell_state)

    print("\n=== HIR OUTPUT ===")
    print(hir_output)

    # === 4️⃣ 加载 behaviors ===
    BASE_DIR = os.path.dirname(__file__)
    behavior_dir = os.path.join(BASE_DIR, "behavior", "behavior_node")

    behaviors = load_behaviors(behavior_dir)

    print(f"\nLoaded {len(behaviors)} behaviors")
    print("\n=== BEHAVIOR EXECUTION ===")

    behavior_outputs = []

    for behavior in behaviors:

        # === gate ===
        gate_ok = True
        for g in behavior.get("gate", []):
            if node_state.get(g["node"], 0.0) < g["threshold"]:
                gate_ok = False
                break

        if not gate_ok:
            print(f"{behavior['behavior_id']} → GATED OFF")
            continue

        # === drive ===
        drive = compute_drive(behavior, node_state)

        # === HIR ===
        drive = apply_HIR(drive, behavior, hir_output)

        # === activation ===
        act = apply_activation(behavior, drive)

        print(f"{behavior['behavior_id']}: drive={round(drive,3)} → act={round(act,3)}")

        #  在 for 内，但和 print 同级
        if act > 0.3:
            behavior_outputs.append({
                "behavior_id": behavior["behavior_id"],
                "activation": act,
                "drive": drive
            })

            print(f"  → BEHAVIOR: {behavior['behavior_id']} | act={act:.3f}")

    #  for 循环结束后（还在函数内部）
    print("\n=== BEHAVIOR OUTPUT ===")
    for b in behavior_outputs:
        print(b)

    # 这里交给 IntentBuilder
    final_intents = build_intents(behavior_outputs)

    print("\n=== FINAL INTENTS ===")
    for i in final_intents:
        print(i)
if __name__ == "__main__":
    run_single_cell()
