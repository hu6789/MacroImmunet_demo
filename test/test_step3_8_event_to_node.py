from cell_master.cell_master_base import CellMasterBase
from scan_master.scan_master_base import ScanEvent


def test_step3_8_event_to_node_mapping():
    cm = CellMasterBase()
    e = ScanEvent(coord=(0, 1), value=2.0, type="test")

    node = cm.event_to_node(e)

    assert node["score"] == 2.0
    assert node["meta"]["coord"] == (0, 1)

