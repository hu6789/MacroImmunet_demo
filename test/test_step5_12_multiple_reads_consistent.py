from label_center.label_center import LabelCenter

def test_step5_12_multiple_reads_consistent():
    lc = LabelCenter()

    intent = {
        "name": "emit_label",
        "payload": {"coord": (1, 1), "label": "X", "amount": 1.0},
    }

    lc.enqueue_intents([intent])

    s1 = lc.get_grid_summary()
    s2 = lc.get_grid_summary()

    assert s1 == s2

