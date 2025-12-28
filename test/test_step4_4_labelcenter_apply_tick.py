from label_center.label_center_base import LabelCenterBase

def test_step4_4_8_labelcenter_apply_tick():
    lc = LabelCenterBase()

    lc.enqueue({
        "name": "emit_label",
        "payload": {
            "coord": (1, 2),
            "label": "PMHC",
            "amount": 2.0,
        }
    })

    assert len(lc.request_queue) == 1

    lc.apply_tick()

    assert len(lc.request_queue) == 0
    field = lc.get_field((1, 2))
    assert field["PMHC"] == 2.0

