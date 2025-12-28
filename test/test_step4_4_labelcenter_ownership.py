from label_center.label_center_base import LabelCenterBase

def test_step4_4_9_labelcenter_ownership():
    lc = LabelCenterBase()

    lc.enqueue({
        "name": "emit_label",
        "payload": {
            "coord": (0, 0),
            "label": "PMHC",
            "amount": 1.0,
        },
        "meta": {
            "source": "CellMaster",
            "reason": {"score": 3.2}
        }
    })

    lc.apply_tick(tick=7)

    field = lc.get_field((0, 0))
    pmhc = field["PMHC"]

    assert pmhc["amount"] == 1.0
    assert pmhc["source"] == "CellMaster"
    assert pmhc["tick"] == 7
    assert pmhc["reason"]["score"] == 3.2

