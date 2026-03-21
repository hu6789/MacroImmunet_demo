from cdff.cell_instance import CellFactory
from cdff.world import World
from cdff.scan_master import ScanMaster
from cdff.cell_master import CellMaster

def create_population(self, n, infected=False):

    cells = []

    for i in range(n):
        cell = CellInstance(...)

        if infected:
            cell.node_state["viral_RNA"] = random.uniform(0.5, 1.0)
            cell.node_state["IRF3"] = random.uniform(0.3, 0.7)

        cells.append(cell)

    return cells

def test_cell_master():

    print("\n=== INIT ===")

    factory = CellFactory(sigma=0.2)
    cells = factory.create_population(3)

    # 🔥 注入刺激（必须在这里）
    for c in cells:
        c.node_state["NFkB"] = 0.5
        c.node_state["IRF3"] = 0.6
        c.node_state["viral_RNA"] = 0.7
    # 🔥 必须加这段
    world = World()
    for c in cells:
        world.add_cell(c)

    scanner = ScanMaster()
    scan_result = scanner.scan(world)

    print("\n=== SCAN RESULT ===")
    print(scan_result)

    print("\n=== CELL MASTER ===")

    master = CellMaster()
    intents = master.process(world, scan_result)

    print("\n=== FINAL INTENTS ===")
    print(intents)


if __name__ == "__main__":
    test_cell_master()
