from label_center.label_center_base import LabelCenterBase
import pytest

def test_emit_label_ignored_when_claimed():
    """
    Step5.10
    When a field label is claimed, further emit_label should be ignored
    """

    lc = LabelCenterBase(decay_rate=1.0)

    # tick = 0: emit label
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

    # tick = 2: emit again (should be ignored)
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

    # still original value
    assert lc.get_label((0, 0), "antigen") == 5.0

