from scan_master.scan_master_base import ScanMasterBase, ScanEvent

class DummyLabelCenter:
    def get_grid_summary(self):
        return {
            (0, 0): {"antigen": 0.5},
            (1, 1): {"antigen": 2.3},
        }

def test_step4_5_scanmaster_emit_event():
    lc = DummyLabelCenter()
    sm = ScanMasterBase(label_center=lc, threshold=1.0)

    events = sm.scan()

    assert len(events) == 1
    evt = events[0]

    assert evt.type == "hotspot"
    assert evt.coord == (1, 1)
    assert evt.value == 2.3

