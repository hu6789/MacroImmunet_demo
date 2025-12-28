from label_center.label_center import LabelCenter

def test_step3_3_label_center_apply_emit_label():
    lc = LabelCenter()

    intents = [
        {
            "name": "emit_label",
            "payload": {
                "label": "ANTIGEN",
                "amount": 3.0,
                "coord": (1, 2),
                "source": "epithelial"
            }
        }
    ]

    lc.enqueue_intents(intents, source="region_A", tick=1)
    lc.apply_tick(tick=1)

    # 1️⃣ queue cleared
    assert lc.intent_queue == []

    # 2️⃣ field updated
    assert (1, 2) in lc.field
    assert lc.field[(1, 2)]["ANTIGEN"] == 3.0

