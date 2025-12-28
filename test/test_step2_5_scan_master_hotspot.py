from scan_master.scan_master import ScanMaster


def test_scan_master_detects_antigen_hotspot():
    sm = ScanMaster(config={"antigen_threshold": 3.0})

    summary = {
        "labels": [
            {"label": "ANTIGEN_RELEASE", "amount": 1.5, "coord": (0, 0)},
            {"label": "ANTIGEN_RELEASE", "amount": 2.0, "coord": (0, 0)},
            {"label": "ANTIGEN_RELEASE", "amount": 0.5, "coord": (1, 1)},
        ]
    }

    events = sm.step(summary)

    assert len(events) == 1
    evt = events[0]
    assert evt["event"] == "hotspot_detected"
    assert evt["coord"] == (0, 0)
    assert evt["antigen"] == 3.5

