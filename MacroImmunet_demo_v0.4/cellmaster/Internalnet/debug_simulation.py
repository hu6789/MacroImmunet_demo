import os
import json

from cellmaster.Internalnet.Internalnet_engine import InternalNet
from cellmaster.cell.cell_factory import CellFactory
from cellmaster.Internalnet.node_engine import load_nodes


def load_behaviors(folder):
    behaviors = []
    for root, _, files in os.walk(folder):
        for file in files:
            if file.endswith(".json"):
                path = os.path.join(root, file)
                with open(path, "r") as f:
                    behaviors.append(json.load(f))
    return behaviors


def run_simulation():

    BASE_DIR = os.path.dirname(__file__)

    # 👉 load behaviors
    behavior_dir = os.path.join(BASE_DIR, "behavior", "behavior_node")
    behaviors = load_behaviors(behavior_dir)

    print(f"\nLoaded {len(behaviors)} behaviors")

    net = InternalNet(behaviors)

    # 👉 cells
    factory = CellFactory()
    cells = [
        factory.create((0, 0), "infected_cell"),
        factory.create((1, 0), "cd8_t_cell")
    ]

    # 🔥 强制 antigen 输入（代替 ScanMaster）
    external_field = {
        "pMHC_signal": 1.0,   # ⭐关键！
        "IFN_external": 0.2,
        "TNF_external": 0.0
    }

    # =========================
    # 🔁 simulation loop
    # =========================
    for tick in range(5):

        print(f"\n====================")
        print(f" TICK {tick}")
        print(f"====================")

        # 👉 衰减环境
        external_field = {k: v * 0.85 for k, v in external_field.items()}

        # 👉 持续 antigen 刺激（模拟持续感染）
        external_field["pMHC_signal"] += 0.2

        # =========================
        # 🧠 STEP 1: node update
        # =========================
        for cell in cells:
            result = net.step(cell, external_field)

        # =========================
        # ⚙️ STEP 2: behavior + fate
        # =========================
        for i, cell in enumerate(cells):

            print(f"\n--- CELL {i} ({cell.cell_type}) ---")
            print(f"DEBUG node_state id: {id(cell.node_state)}")  # 🔹 打印 id

            prev_state = dict(cell.node_state)
            result = net.run_behavior_and_fate(cell)
            node_state = cell.node_state

            # key signal
            for k in ["pMHC_signal","TCR_receptor","costim_signal","activation_signal","cytotoxic_program"]:
                print(f"{k}: {round(node_state.get(k,0),3)}")

            # delta
            for k in ["ATP","stress","damage"]:
                d = node_state.get(k,0)-prev_state.get(k,0)
                print(f"{k}: {round(d,3)}")

            # 🔥 核心信号链
            print("KEY SIGNAL CHAIN:")
            for k in [
                "pMHC_signal",
                "TCR_receptor",
                "costim_signal",
                "activation_signal",
                "cytotoxic_program"
            ]:
                print(f"{k}: {round(node_state.get(k, 0),3)}")

            # 👉 行为输出
            print("\nBEHAVIORS:")
            for b in result["behaviors"]:
                print(f"{b['behavior_id']} → {round(b['activation'],3)}")

            # 👉 delta
            print("\nDELTA:")
            for k in ["ATP", "stress", "damage"]:
                d = node_state.get(k, 0) - prev_state.get(k, 0)
                print(f"{k}: {round(d,3)}")

            print("FATE:", result["fate"])

        # 👉 输出环境
        print("\n🌍 EXTERNAL FIELD:")
        for k, v in external_field.items():
            print(f"{k}: {round(v,3)}")


if __name__ == "__main__":
    run_simulation()
