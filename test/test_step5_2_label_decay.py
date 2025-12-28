from label_center.label_center_base import LabelCenterBase

def test_step5_2_label_decay_over_time():
    lc = LabelCenterBase(decay_rate=0.5)

    lc.consume_intents([
        {
            "name": "emit_label",
            "payload": {
                "coord": (1, 1),
                "label": "PMHC",
                "amount": 4.0
            }
        }
    ])

    # tick = 0
    assert lc.get_label((1, 1), "PMHC") == 4.0

    # tick = 1
    lc.advance_tick(1)
    assert lc.get_label((1, 1), "PMHC") == 2.0

    # tick = 2
    lc.advance_tick(2)
    assert lc.get_label((1, 1), "PMHC") == 1.0

