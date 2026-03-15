# demo/demo_trace_run.py v0.2

from cdff.scanmaster.scan_master import ScanMaster
from cdff.cellmaster.cell_master import CellMaster
from cdff.label_center.label_center import LabelCenter
from cdff.debug.trace import StageTrace  # 用于阶段输出

# ===== 最小 world =====
class DemoWorld:

    def __init__(self):
        self.cells = [
            {"id": "cell_1", "type": "epithelial", "state": "healthy", "health": 100},
            {"id": "cell_2", "type": "virus", "state": "free", "replication_level": 1}
        ]

    def get_neighbors(self, cell):
        # demo 简单返回除了自己之外的所有 cell
        return [c for c in self.cells if c != cell]

# ===== Demo Trace Run =====
def run_demo():
    print("=== MacroImmunet Demo Trace Run v0.2 ===")

    # --------- Step 0: 初始化世界 ---------
    world = DemoWorld()
    print("[World] Initial cells:")
    for cell in world.cells:
        print(f"  {cell}")

    # --------- Step 1: ScanMaster ---------
    scan = ScanMaster(world)
    print("\n[ScanMaster] Scanning cells...")
    scanned_results = {}
    for cell in world.cells:
        node_input = scan.scan_cell(cell)

        # 简单 demo：病毒 cell 会产生信号给 epithelial cell
        if cell["type"] == "virus":
            for neighbor in world.get_neighbors(cell):
                node_input["events"].append({
                    "signal": "pMHC_candidate",
                    "source": cell["id"],
                    "target": neighbor["id"],
                    "strength": 1.0
                })
                node_input["signals"]["pMHC_candidate"] = 1.0

        scanned_results[cell["id"]] = node_input
        print(f"  Cell {cell['id']} scan result: {node_input}")

    # --------- Step 2: CellMaster ---------
    cell_master = CellMaster()
    label_center = LabelCenter()

    print("\n[CellMaster] Processing cells...")
    for cell in world.cells:
        node_input = scanned_results[cell["id"]]
        print(f"  -> Node input for Cell {cell['id']}: {node_input}")

        # 决策（内部调用 ASI + InternalNet + HIR）
        raw_behaviors = cell_master.process_cell(cell, node_input)
        print(f"  -> Raw behaviors for Cell {cell['id']}: {raw_behaviors}")

        # demo规则：如果接收到 pMHC_candidate 信号，则行为是 attack
        behaviors = {
            "behaviors": raw_behaviors
        }
        if node_input["signals"].get("pMHC_candidate", 0) > 0:
            behaviors["behaviors"].append("attack")

        # IntentBuilder 构建意图
        intents = cell_master.intent_builder.build_intents(cell, behaviors)
        print(f"  -> Intents for Cell {cell['id']}: {intents}")

        # 写入 LabelCenter
        label_center.apply(intents)
        print(f"  -> LabelCenter state updated for Cell {cell['id']}")

    # --------- Step 3: 总结 ---------
    print("\n[Demo] Final LabelCenter State:")
    print(label_center.state_summary())

if __name__ == "__main__":
    run_demo()
