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

def _apply_distribution(self, cell):

    for k, spec in cell.feature_params.items():
        cell.feature_params[k] = self._sample_param(spec)
# =========================
# 🔹 主循环
# =========================

def run_simulation(ticks=8, n_cells=3):

    factory = CellFactory()
    behaviors = load_behaviors()

    internalnet = InternalNet(behaviors)
    intent_builder = IntentBuilder(behaviors)

    # === 空间 ===
    space = Space()

    # === 创建多个 cell ===
    cells = []
    for i in range(n_cells):
        cell = factory.create("test_cell")
        cell.cell_id = f"cell_{i}"
        cells.append(cell)

        # 随便放位置（之后可以随机）
        space.place_cell(cell.cell_id, (i, i))

    # === world ===
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

    # =========================
    # 🔁 LOOP
    # =========================
    for tick in range(ticks):

        print(f"\n========== TICK {tick} ==========")

        all_intents = []

        # =====================
        # 1️⃣ scan + decision
        # =====================
        for cell in cells:

            node_input = scan_master.scan(cell)

            result = internalnet.step(cell, node_input)

            print(f"\n[cell {cell.cell_id}]")
            print("Scan:", node_input)
            print("Fate:", result["fate"])

            # =====================
            # 2️⃣ intent
            # =====================
            intents = intent_builder.build(cell, result)

            all_intents.extend(intents)

        # =====================
        # 3️⃣ apply（统一提交！）
        # =====================
        label_center.enqueue(all_intents)
        label_center.apply()
        space.diffuse()
        print("\nField:", label_center.get_all())
# =========================
# 🔹 入口
# =========================

if __name__ == "__main__":
    run_simulation()
