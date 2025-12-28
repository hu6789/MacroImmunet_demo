from label_center.label_center_base import LabelCenterBase

def test_field_label_pruned_when_too_small():
    lc = LabelCenterBase(decay_rate=0.5, prune_threshold=0.2)

    # tick = 0
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

    # 推进时间
    lc.advance_tick(1)
    lc.advance_tick(2)
    lc.advance_tick(3)

    # 强制触发 prune（可以在 tick / advance_tick 中）
    lc.prune()

    assert lc.get_label((0, 0), "antigen") == 0.0

