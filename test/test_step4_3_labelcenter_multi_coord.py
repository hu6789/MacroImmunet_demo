from label_center.label_center import LabelCenter


def test_step4_3_1_labelcenter_multi_coord_sanity():
    lc = LabelCenter()

    # 同一个 tick，两个不同 coord
    intents = [
        {
            "name": "emit_label",
            "payload": {
                "coord": (0, 0),
                "label": "PMHC",
                "amount": 1.0,
            }
        },
        {
            "name": "emit_label",
            "payload": {
                "coord": (1, 0),
                "label": "PMHC",
                "amount": 2.0,
            }
        },
    ]

    lc.enqueue_intents(
        intents,
        source="test",
        tick=0,
    )

    lc.apply_tick(0)

    summary = lc.get_grid_summary()

    # ✅ 不变量 1：两个 coord 都存在
    assert (0, 0) in summary
    assert (1, 0) in summary

    # ✅ 不变量 2：数值不串
    assert summary[(0, 0)]["labels"]["PMHC"] == 1.0
    assert summary[(1, 0)]["labels"]["PMHC"] == 2.0

