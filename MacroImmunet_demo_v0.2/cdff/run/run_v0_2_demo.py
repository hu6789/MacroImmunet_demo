# cdff/run/run_v0_2_demo.py

from cdff.cell_instance import CellFactory
from cdff.world import World
from cdff.scan_master import ScanMaster
from cdff.cell_master import CellMaster
from cdff.label_center import LabelCenter


def run_demo():

    print("\n=== MacroImmunet v0.2 Demo ===")

    # ========= 初始化 =========
    factory = CellFactory(sigma=0.2)
    cells = factory.create_population(3)

    for c in cells:
        c.node_state["NFkB"] = 2.0
        c.node_state["IRF3"] = 2.0
        c.node_state["viral_RNA"] = 0.8

    world = World()
    for c in cells:
        world.add_cell(c)

    scanner = ScanMaster()
    master = CellMaster()
    label = LabelCenter()

    # ========= 主循环 =========
    for tick in range(5):

        print(f"\n========== TICK {tick} ==========")

        # --- Scan ---
        scan_result = scanner.scan(world, label)

        # --- Decision ---
        intents = master.process(world, scan_result)

        # --- Apply ---
        label.submit(intents)
        label.apply(world)

        # ========= 可视化输出 =========

        print("\n[Field]")
        print(label.summary())

        print("\n[Cell States]")
        for cell in world.cells:
            print(cell.cell_id, {
                "stress": round(cell.node_state.get("stress", 0), 3),
                "damage": round(cell.node_state.get("damage", 0), 3),
                "ATP": round(cell.node_state.get("ATP", 0), 3)
            })


if __name__ == "__main__":
    run_demo()
