from cell_master.cell_master_base import CellMasterBase
from scan_master.scan_event import ScanEvent


def test_step4_7_1_event_to_node():
    cm = CellMasterBase()

    event = ScanEvent(
        coord=(2, 3),
        value=4.5,
        type="antigen_peak",
        meta={"source": "field"}
    )

    node = cm._event_to_node(event)

    assert node["coord"] == (2, 3)
    assert node["type"] == "antigen"
    assert node["signal"] == 4.5
    assert node["meta"]["source"] == "field"

