from cell_master.cell_master_base import CellMasterBase
from scan_master.event import ScanEvent
from cell_master.cell_master_base import CellMasterBase



def test_step4_8_2_merge_events_same_coord():
    cm = CellMasterBase(score_threshold=0.0)

    e1 = ScanEvent(coord=(1, 1), value=1.0, type="antigen", tick=1)
    e2 = ScanEvent(coord=(1, 1), value=2.0, type="danger", tick=2)

    merged = cm.merge_events([e1, e2])

    assert len(merged) == 1
    assert merged[0].coord == (1, 1)
    assert merged[0].value == 3.0

