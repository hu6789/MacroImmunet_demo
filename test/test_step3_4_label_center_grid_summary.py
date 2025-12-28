from label_center.label_center import LabelCenter

def test_step3_4_grid_summary_basic():
    lc = LabelCenter()

    lc.enqueue_intents([
        {
            "name": "emit_label",
            "payload": {
                "label": "ANTIGEN",
                "amount": 4.0,
                "coord": (2, 3)
            }
        }
    ], tick=1)

    lc.apply_tick(tick=1)

    grid = lc.get_grid_summary()

    assert (2, 3) in grid
    assert grid[(2, 3)]["labels"]["ANTIGEN"] == 4.0

