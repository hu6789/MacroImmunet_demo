from scan_master.scan_master_base import ScanEvent


def test_step3_7_scan_event_fields():
    e = ScanEvent(
        coord=(1, 2),
        value=3.4,
        type="antigen_peak",
        meta={"source": "field"}
    )

    assert e.coord == (1, 2)
    assert isinstance(e.value, float)
    assert e.type == "antigen_peak"
    assert isinstance(e.meta, dict)

