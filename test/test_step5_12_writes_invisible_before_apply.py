from label_center.label_center import LabelCenter

def test_step5_12_writes_invisible_before_apply():
    lc = LabelCenter()

    intent = {
        "name": "emit_label",
        "payload": {
            "coord": (1, 1),
            "label": "hotspot",
            "amount": 1.0,
        },
    }

    lc.enqueue_intents([intent], source="test", tick=0)

    # apply 前不可见
    summary = lc.get_grid_summary()
    assert summary == {}

