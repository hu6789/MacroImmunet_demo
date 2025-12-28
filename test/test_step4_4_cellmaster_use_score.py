from cell_master.cell_master_base import CellMasterBase


class ScoreDrivenCellMaster(CellMasterBase):
    """
    Step4.4.1
    CellMaster reads node.meta.score to decide intent strength
    """
    def handle_nodes(self, nodes, **kwargs):
        intents = []

        for node in nodes:
            score = node["meta"].get("score", 0.0)

            amount = 0.5
            if score >= 3.0:
                amount = 1.0

            intents.append({
                "name": "emit_label",
                "payload": {
                    "coord": node["meta"]["coord"],
                    "label": "PMHC",
                    "amount": amount,
                }
            })

        return {"intents": intents}


def test_step4_4_1_cellmaster_use_score():
    cm = ScoreDrivenCellMaster(space=None)

    nodes = [{
        "behavior": "hotspot",
        "meta": {
            "coord": (0, 0),
            "score": 3.5,
            "rank": 0,
        }
    }]

    result = cm.handle_nodes(nodes)

    intents = result["intents"]
    assert len(intents) == 1
    assert intents[0]["payload"]["amount"] == 1.0

