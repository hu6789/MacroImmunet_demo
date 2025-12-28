from label_center.label_center_base import LabelCenterBase

def test_step5_1_emit_label_updates_field():
    lc = LabelCenterBase()

    intents = [
        {
            "name": "emit_label",
            "payload": {
                "coord": (2, 3),
                "label": "PMHC",
                "amount": 1.0,
            },
            "meta": {
                "score": 3.5
            }
        }
    ]

    lc.consume_intents(intents)

    assert lc.get_label((2, 3), "PMHC") == 1.0

