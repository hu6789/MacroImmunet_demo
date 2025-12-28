from cell_master.cell_master_base import CellMasterBase
from scan_master.scan_master_base import ScanEvent


def test_step4_6_cellmaster_consume_event_basic():
    cm = CellMasterBase(
        score_threshold=0.5,
        budget=1
    )

    event = ScanEvent(
        coord=(2, 3),
        value=1.2,
        type="antigen_peak"
    )

    intents = cm.consume_event(event)

    assert intents is not None
    assert isinstance(intents, list)
    assert len(intents) == 1

    it = intents[0]
    # Step4.4.5 emit intent shape
    assert it["name"] == "emit_label"
    assert it["payload"]["coord"] == (2, 3)

