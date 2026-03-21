from cdff.cell_instance import CellFactory
from cdff.world import World
from cdff.scan_master import ScanMaster
from cdff.cell_master import CellMaster
from cdff.label_center import LabelCenter

def test_label_center():

    print("\n=== INIT ===")

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

    # 多 tick 开始
    for tick in range(5):
 
        print(f"\n========== TICK {tick} ==========")

        # 把 field 传进去
        scan_result = scanner.scan(world, label)

        intents = master.process(world, scan_result)

        label.submit(intents)
        label.apply(world)

        print("FIELD:", label.summary())
if __name__ == "__main__":
    test_label_center()
