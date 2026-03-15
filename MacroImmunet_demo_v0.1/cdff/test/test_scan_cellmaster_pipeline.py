from cdff.scanmaster.scan_master import ScanMaster
from cdff.cellmaster.cell_master import CellMaster


class DummyWorld:

    def __init__(self):

        self.cells = [
            {"id": 1, "type": "CD8_T"},
            {"id": 2, "type": "infected_cell"}
        ]

    def get_neighbors(self, cell):

        return [c for c in self.cells if c["id"] != cell["id"]]


def test_scan_to_cellmaster_pipeline():

    world = DummyWorld()

    scanmaster = ScanMaster(world)
    cellmaster = CellMaster()

    cell = world.cells[0]

    node_input = scanmaster.scan_cell(cell)

    intents = cellmaster.process_cell(cell, node_input)

    assert isinstance(intents, list)
