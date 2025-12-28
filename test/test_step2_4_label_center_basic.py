from label_center.label_center import LabelCenter


def test_label_center_receives_emit_label():
    lc = LabelCenter()

    actions = [
        {
            "name": "emit_label",
            "payload": {
                "label": "ANTIGEN_RELEASE",
                "amount": 5.0,
                "coord": (1, 2),
                "source": "epithelial"
            }
        }
    ]

    lc.apply_actions(actions)
    labels = lc.snapshot()

    assert len(labels) == 1
    assert labels[0]["label"] == "ANTIGEN_RELEASE"
    assert labels[0]["amount"] == 5.0
    assert labels[0]["coord"] == (1, 2)

