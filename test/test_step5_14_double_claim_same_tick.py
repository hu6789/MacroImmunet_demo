from label_center.label_center_base import LabelCenterBase

def test_step5_14_double_claim_same_tick():
    """
    Step5.14
    Two claims in the same tick: first wins, second fails
    """

    lc = LabelCenterBase()

    # tick 0: emit
    lc.consume_intents([
        {
            "name": "emit_label",
            "payload": {
                "coord": (0, 0),
                "label": "antigen",
                "amount": 1.0,
            }
        }
    ])

    # tick 1
    lc.advance_tick(1)

    ok1 = lc.claim_label((0, 0), "antigen", by="percell_A")
    ok2 = lc.claim_label((0, 0), "antigen", by="percell_B")

    assert ok1 is True
    assert ok2 is False

    # ownership stable
    entry = lc.label_field[(0, 0)]["antigen"]
    assert entry["owned_by"] == "percell_A"

