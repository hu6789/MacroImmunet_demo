from cell_master.cell_master_base import CellMasterBase


class BudgetedCellMaster(CellMasterBase):
    """
    Step4.4.2
    CellMaster enforces per-tick intent budget
    """
    def __init__(self, space=None, max_intents=1):
        super().__init__(space)
        self.max_intents = max_intents

    def handle_nodes(self, nodes, **kwargs):
        # 🔑 sort by score desc
        nodes = sorted(
            nodes,
            key=lambda n: n["meta"].get("score", 0.0),
            reverse=True
        )

        intents = []

        for node in nodes[:self.max_intents]:
            intents.append({
                "name": "emit_label",
                "payload": {
                    "coord": node["meta"]["coord"],
                    "label": "PMHC",
                    "amount": 1.0,
                }
            })

        return {"intents": intents}


def test_step4_4_2_cellmaster_budget():
    cm = BudgetedCellMaster(space=None, max_intents=1)

    nodes = [
        {"meta": {"coord": (0, 0), "score": 5.0}},
        {"meta": {"coord": (1, 0), "score": 3.0}},
        {"meta": {"coord": (2, 0), "score": 1.0}},
    ]

    result = cm.handle_nodes(nodes)
    intents = result["intents"]

    assert len(intents) == 1
    assert intents[0]["payload"]["coord"] == (0, 0)

