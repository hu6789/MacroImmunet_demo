from label_center.label_center_base import LabelCenterBase

def test_emit_label_works_after_release():
    """
    Step5.11
    After a label is released, emit_label should work again
    """

    lc = LabelCenterBase(decay_rate=1.0)

    # tick = 0: emit
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

    # tick = 1: claim
    lc.advance_tick(1)
    ok = lc.claim_label(coord=(0, 0), label_name="antigen", by="percell_A")
    assert ok is True

    # tick = 2: emit while claimed (ignored)
    lc.advance_tick(2)
    lc.consume_intents([
        {
            "name": "emit_label",
            "payload": {
                "coord": (0, 0),
                "label": "antigen",
                "amount": 10.0,
            }
        }
    ])
    assert lc.get_label((0, 0), "antigen") == 5.0

    # tick = 3: release
    lc.advance_tick(3)
    lc.release_label(coord=(0, 0), label_name="antigen", by="percell_A")

    # tick = 4: emit again (should merge now)
    lc.advance_tick(4)
    lc.consume_intents([
        {
            "name": "emit_label",
            "payload": {
                "coord": (0, 0),
                "label": "antigen",
                "amount": 2.0,
            }
        }
    ])

    assert lc.get_label((0, 0), "antigen") == 7.0

