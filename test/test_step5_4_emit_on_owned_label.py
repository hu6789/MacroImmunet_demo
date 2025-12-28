from label_center.label_center_base import LabelCenterBase

def test_emit_label_does_not_override_owned_label():
    lc = LabelCenterBase()

    # 模拟 per-cell 认领
    lc.label_field[(1, 1)] = {
        "PMHC": {
            "value": 2.0,
            "last_tick": 0,
            "owned_by": "percell:42"
        }
    }

    intents = [
        {
            "name": "emit_label",
            "payload": {
                "coord": (1, 1),
                "label": "PMHC",
                "amount": 1.0,
            }
        }
    ]

    lc.consume_intents(intents)

    # 不应该被覆盖或叠加
    assert lc.get_label((1, 1), "PMHC") == 2.0

