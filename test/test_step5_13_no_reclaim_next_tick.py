from label_center.label_center_base import LabelCenterBase

def test_step5_13_no_reclaim_next_tick():
    """
    Step5.13
    Cooldown prevents immediate reclaim across adjacent ticks
    """

    lc = LabelCenterBase(claim_cooldown=2)

    # tick 0
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

    # tick 1: claim
    lc.advance_tick(1)
    assert lc.claim_label((1, 1), "antigen", by="A") is True

    # tick 2: release
    lc.advance_tick(2)
    lc.release_label((1, 1), "antigen", by="A")

    # tick 3: still cooldown
    lc.advance_tick(3)
    assert lc.claim_label((1, 1), "antigen", by="B") is False

