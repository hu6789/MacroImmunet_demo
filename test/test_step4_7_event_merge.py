from scan_master.scan_master_base import ScanEvent
from cell_master.cell_master_base import CellMasterBase

def test_step4_7_merge_events_by_coord():
    cm = CellMasterBase()

    events = [
        ScanEvent(coord=(1, 2), value=3.0, type="antigen", meta={"src": "field"}),
        ScanEvent(coord=(1, 2), value=2.0, type="cytokine", meta={"src": "field"}),
    ]

    nodes = cm.merge_events_to_nodes(events)

    assert len(nodes) == 1
    node = nodes[0]

    assert node["meta"]["coord"] == (1, 2)
    assert node["score"] == 5.0
    assert "antigen" in node["explain"]
    assert "cytokine" in node["explain"]

