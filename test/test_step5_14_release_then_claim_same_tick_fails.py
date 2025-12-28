from label_center.label_center_base import LabelCenterBase

def test_step5_14_release_then_claim_same_tick_fails():
    """
    Step5.14
    release does not allow reclaim within the same tick
    """

    lc = LabelCenterBase(claim_cooldown=1)

    # tick 0
    lc.consume_intents([
        {
            "name": "emit_label",
            "payload": {
                "coord": (2, 2),
                "label": "antigen",
                "amount": 2.0,
            }
        }
    ])

    # tick 1
    lc.advance_tick(1)
    assert lc.claim_label((2, 2), "antigen", by="A") is True

    # same tick: release
    lc.release_label((2, 2), "antigen", by="A")

    # same tick: another tries to claim
    assert lc.claim_label((2, 2), "antigen", by="B") is False

    entry = lc.label_field[(2, 2)]["antigen"]
    assert entry["owned_by"] is None

