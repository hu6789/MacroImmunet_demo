from scan_master.scan_master_base import ScanEvent, rank_events

def test_step4_7_4_event_priority():
    e1 = ScanEvent(
        coord=(1, 1),
        value=2.0,
        type="antigen_peak",
        tick=1
    )

    e2 = ScanEvent(
        coord=(1, 1),
        value=1.0,
        type="danger_signal",
        tick=2
    )

    ranked = rank_events([e1, e2])

    assert ranked[0].type == "danger_signal"

