from label_center.label_center_base import LabelCenterBase

def test_step5_13_no_reclaim_same_tick():
    """
    Step5.13
    Prevent ownership oscillation within the same tick
    """

    lc = LabelCenterBase(claim_cooldown=1)

    # tick 0: emit
    lc.consume_intents([
        {
            "name": "emit_label",
            "payload": {
                "coord": (0, 0),
                "label": "antigen",
                "amount": 5.0,
            }
        }
    ])

    # tick 1: claim
    lc.advance_tick(1)
    ok = lc.claim_label((0, 0), "antigen", by="percell_A")
    assert ok is True

    # still tick 1: release
    lc.release_label((0, 0), "antigen", by="percell_A")

    # still tick 1: try reclaim
    ok = lc.claim_label((0, 0), "antigen", by="percell_B")
    assert ok is False

