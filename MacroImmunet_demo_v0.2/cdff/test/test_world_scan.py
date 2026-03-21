from cdff.cell_instance import CellFactory
from cdff.world import World
from cdff.scan_master import ScanMaster


def test_world_scan():

    print("\n=== CREATE CELLS ===")

    factory = CellFactory(sigma=0.2)
    cells = factory.create_population(5)

    for c in cells:
        print(c)

    print("\n=== BUILD WORLD ===")

    world = World()
    for c in cells:
        world.add_cell(c)

    print(world)
    print(world.summary())

    print("\n=== SCAN WORLD ===")

    scanner = ScanMaster()
    result = scanner.scan(world)

    print("\n=== SCAN RESULT ===")
    for region, signals in result.items():
        print(region, "->", signals)


if __name__ == "__main__":
    test_world_scan()
