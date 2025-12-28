from cell_master.cell_master_base import CellMasterBase

def test_step4_4_5_cellmaster_emit_intent():
    cm = CellMasterBase(budget=1, score_threshold=2.0)

    node = {
        "meta": {"coord": (0, 0)},
        "score": 3.5,
        "explain": {"reason": "high PMHC"}
    }

    intents = cm.process_nodes([node])

    assert len(intents) == 1
    intent = intents[0]

    assert intent["name"] == "emit_label"
    assert intent["payload"]["coord"] == (0, 0)
    assert intent["meta"]["score"] == 3.5

