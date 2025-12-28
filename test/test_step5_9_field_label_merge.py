from label_center.label_center_base import LabelCenterBase

def test_field_label_merge_on_emit():
    """
    Step5.9
    Field labels at same coord + name should accumulate on emit
    """

    lc = LabelCenterBase(decay_rate=0.0)

    # tick = 0: first emit
    lc.consume_intents([
        {
            "name": "emit_label",
            "payload": {
                "coord": (1, 1),
                "label": "antigen",
                "amount": 2.0,
            }
        }
    ])

    # tick = 1: second emit at same place
    lc.advance_tick(1)
    lc.consume_intents([
        {
            "name": "emit_label",
            "payload": {
                "coord": (1, 1),
                "label": "antigen",
                "amount": 3.0,
            }
        }
    ])

    assert lc.get_label((1, 1), "antigen") == 5.0

