from label_center.label_center_base import LabelCenterBase

def test_step5_13_emit_not_revive_claimed_state():
    """
    Step5.13
    Emit should not override recently released ownership state
    """

    lc = LabelCenterBase(claim_cooldown=1)

    # tick 0
    lc.consume_intents([
        {
            "name": "emit_label",
            "payload": {
                "coord": (2, 2),
                "label": "antigen",
                "amount": 5.0,
            }
        }
    ])

    # tick 1: claim
    lc.advance_tick(1)
    lc.claim_label((2, 2), "antigen", by="A")

    # tick 2: release
    lc.advance_tick(2)
    lc.release_label((2, 2), "antigen", by="A")

    # same tick 2: emit again
    lc.consume_intents([
        {
            "name": "emit_label",
            "payload": {
                "coord": (2, 2),
                "label": "antigen",
                "amount": 10.0,
            }
        }
    ])

    # amount should remain unchanged
    assert lc.get_label((2, 2), "antigen") == 5.0

