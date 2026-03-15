from cdff.scanmaster.scan_master import ScanMaster


class DummyWorld:

    def __init__(self):

        self.cells = [
            {"id": 1, "type": "CD8_T"},
            {"id": 2, "type": "infected_cell"}
        ]

    def get_neighbors(self, cell):

        return [c for c in self.cells if c["id"] != cell["id"]]


def test_scanmaster_detects_contact():

    world = DummyWorld()

    scanmaster = ScanMaster(world)

    node_input = scanmaster.scan_cell(world.cells[0])

    assert "signals" in node_input
