from cell_master.cell_master_base import CellMasterBase


class ExplainableCellMaster(CellMasterBase):
    def __init__(self, space=None, max_intents=1):
        super().__init__(space)
        self.max_intents = max_intents

    def handle_nodes(self, nodes, **kwargs):
        nodes = sorted(
            nodes,
            key=lambda n: n["meta"].get("score", 0.0),
            reverse=True
        )

        intents = []
        explain = []

        for idx, node in enumerate(nodes):
            coord = node["meta"]["coord"]
            score = node["meta"].get("score", 0.0)

            if idx < self.max_intents:
                intents.append({
                    "name": "emit_label",
                    "payload": {
                        "coord": coord,
                        "label": "PMHC",
                        "amount": 1.0,
                    }
                })
                explain.append({
                    "coord": coord,
                    "score": score,
                    "selected": True,
                    "reason": "top-%d by score under budget" % self.max_intents
                })
            else:
                explain.append({
                    "coord": coord,
                    "score": score,
                    "selected": False,
                    "reason": "budget exceeded"
                })

        return {
            "intents": intents,
            "explain": explain
        }


def test_step4_4_3_cellmaster_explain_log():
    cm = ExplainableCellMaster(space=None, max_intents=1)

    nodes = [
        {"meta": {"coord": (0, 0), "score": 5.0}},
        {"meta": {"coord": (1, 0), "score": 3.0}},
    ]

    result = cm.handle_nodes(nodes)

    assert "explain" in result
    explain = result["explain"]

    assert explain[0]["selected"] is True
    assert explain[0]["coord"] == (0, 0)

    assert explain[1]["selected"] is False
    assert explain[1]["reason"] == "budget exceeded"

