# test/test_step5_6_released_label_can_decay.py

from label_center.label_center_base import LabelCenterBase


def test_released_field_label_can_decay():
    lc = LabelCenterBase(decay_rate=0.5)

    # tick = 0，emit 一个 field label
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

    # 推进时间
    lc.advance_tick(1)

    # per-cell claim（冻结）
    lc.claim_label(coord=(0, 0), label_name="antigen", by="percell_A")

    # 再推进时间（不应 decay）
    lc.advance_tick(2)
    v_frozen = lc.get_label((0, 0), "antigen")
    assert v_frozen == 10.0

    # release ownership
    lc.release_label(coord=(0, 0), label_name="antigen", by="percell_A")

    # 再推进时间（应 decay）
    lc.advance_tick(3)
    v_decayed = lc.get_label((0, 0), "antigen")

    assert v_decayed < 10.0

