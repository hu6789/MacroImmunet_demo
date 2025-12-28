# test/test_step3_1_cell_master_simple.py

from cell_master.cell_master_simple import CellMasterSimple


def test_cell_master_simple_emit_intent():
    cm = CellMasterSimple(cell_type="macrophage", antigen_threshold=2.0)

    node_input = {
        "coord": (2, 3),
        "antigen_density": 3.5,
        "cell_summary": {"macrophage": 10},
        "event_flag": "hotspot"
    }

    intents = cm.process_node(node_input)

    assert isinstance(intents, list)
    assert len(intents) == 1

    intent = intents[0]
    assert intent["target_cell"] == "macrophage"
    assert intent["coord"] == (2, 3)
    assert intent["action"] == "activate"

