from label_center.label_center_base import LabelCenterBase

def test_owned_label_not_decay():
    lc = LabelCenterBase()

    # 直接注入一个 label（模拟 per-cell 认领）
    lc.field[(1, 1)] = {
        "PMHC": {
            "amount": 1.0,
            "owned_by": "percell:42"
        }
    }

    lc.tick()

    field = lc.field[(1, 1)]
    assert field["PMHC"]["amount"] == 1.0

