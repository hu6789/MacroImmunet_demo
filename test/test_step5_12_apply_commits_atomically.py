from label_center.label_center import LabelCenter

def test_step5_12_apply_commits_atomically():
    lc = LabelCenter()

    intents = [
        {
            "name": "emit_label",
            "payload": {"coord": (1, 1), "label": "A", "amount": 1.0},
        },
        {
            "name": "emit_label",
            "payload": {"coord": (2, 2), "label": "B", "amount": 2.0},
        },
    ]

    lc.enqueue_intents(intents)
    lc.apply_tick()

    summary = lc.get_grid_summary()

    assert summary[(1, 1)]["labels"]["A"] == 1.0
    assert summary[(2, 2)]["labels"]["B"] == 2.0

