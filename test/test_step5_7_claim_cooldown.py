import pytest
from label_center import LabelCenterBase


def test_released_label_has_claim_cooldown():
    """
    Step5.7
    Released field label cannot be re-claimed until cooldown expires
    """

    lc = LabelCenterBase(decay_rate=1.0, claim_cooldown=2)

    # tick = 0: emit label
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

    # tick = 1: first claim
    lc.advance_tick(1)
    ok = lc.claim_label(coord=(0, 0), label_name="antigen", by="percell_A")
    assert ok is True

    # tick = 2: release
    lc.advance_tick(2)
    lc.release_label(coord=(0, 0), label_name="antigen", by="percell_A")

    # tick = 3: still in cooldown → cannot claim
    lc.advance_tick(3)
    ok = lc.claim_label(coord=(0, 0), label_name="antigen", by="percell_B")
    assert ok is False

    # tick = 4: cooldown ends → can claim again
    lc.advance_tick(4)
    ok = lc.claim_label(coord=(0, 0), label_name="antigen", by="percell_B")
    assert ok is True

