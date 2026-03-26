# run_loop_v0.3.py

import json
import os

from Internalnet.Internalnet_engine import InternalNet
from Internalnet.cell.cell_factory import CellFactory
from intent.intent_builder import IntentBuilder
from world.label.label_center import LabelCenter
from world.scan.scan_master import ScanMaster
from world.space.space import Space
# =========================
# 🔹 加载 behaviors
# =========================

def load_behaviors():

    base_dir = os.path.dirname(__file__)
    behavior_dir = os.path.join(base_dir, "Internalnet", "behavior")

    behaviors = []

    for root, _, files in os.walk(behavior_dir):
        for file in files:
            if file.endswith(".json"):

                path = os.path.join(root, file)

                with open(path, "r") as f:
                    data = json.load(f)

                    # ✅ 只收 behavior
                    if "behavior_id" not in data:
                        continue

                    behaviors.append(data)
    print("Loaded behaviors:")
    for b in behaviors:
        print(" -", b["behavior_id"])
    return behaviors


# =========================
# 🔹 主循环
# =========================
def run_simulation(ticks=8):

    # === 初始化 ===
    factory = CellFactory()
    cell = factory.create("test_cell")
    behaviors = load_behaviors()

    # ❗ InternalNet 只创建一次
    internalnet = InternalNet(behaviors)
    intent_builder = IntentBuilder(behaviors)

    space = Space()
    space.place_cell(cell.cell_id, (2, 2))
    
    label_center = LabelCenter(
        {
            "IFN": 0.0,
            "IL6": 0.0,
            "TNF": 0.0,
            "damage": 0.0,
            "virus": 0.6
        },
        space=space 
    )
    
    scan_master = ScanMaster(label_center, space)
    # === loop ===
    for tick in range(ticks):

        print(f"\n========== TICK {tick} ==========")

        # 1️⃣ scan
        node_input = scan_master.scan(cell)

        print("Scan Input:", node_input)

        # 2️⃣ InternalNet（唯一一次 step）
        result = internalnet.step(cell, node_input)

        print("Features:", result.get("features", {}))
        print("Fate:", result["fate"])
        print("HIR:", result["hir"])

        print("Behaviors:")
        for b in result["behaviors"]:
            print(f"  - {b['behavior_id']} | act={b['activation']:.3f} | drive={b['drive']:.3f}")

        # 3️⃣ intent
        intents = intent_builder.build(cell, result)

        print("Intents:", intents)

        # 4️⃣ apply
        label_center.enqueue(intents)
        label_center.apply()

        field = label_center.get_all() 
        print("Field:", field)

        # 5️⃣ debug
        print("Node STATE snapshot:")
        print(f"  STAT1: {cell.node_state.get('STAT1', 0):.3f}")
        print(f"  IRF3 : {cell.node_state.get('IRF3', 0):.3f}")
        print(f"  NFkB : {cell.node_state.get('NFkB', 0):.3f}")
# =========================
# 🔹 入口
# =========================

if __name__ == "__main__":
    run_simulation()
