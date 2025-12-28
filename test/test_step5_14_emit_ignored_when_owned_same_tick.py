from label_center.label_center_base import LabelCenterBase

def test_step5_14_emit_ignored_when_owned_same_tick():
    """
    Step5.14
    emit_label must be ignored when label is owned (same tick)
    """

    lc = LabelCenterBase(decay_rate=1.0)

    # tick 0
    lc.consume_intents([
        {
            "name": "emit_label",
            "payload": {
                "coord": (1, 1),
                "label": "antigen",
                "amount": 5.0,
            }
        }
    ])

    # tick 1
    lc.advance_tick(1)
    assert lc.claim_label((1, 1), "antigen", by="percell_A") is True

    # same tick: emit again
    lc.consume_intents([
        {
            "name": "emit_label",
            "payload": {
                "coord": (1, 1),
                "label": "antigen",
                "amount": 10.0,
            }
        }
    ])

    assert lc.get_label((1, 1), "antigen") == 5.0

