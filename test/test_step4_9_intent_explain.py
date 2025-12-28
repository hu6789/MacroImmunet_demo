from cell_master.cell_master_base import CellMasterBase

class DummyExecutor:
    def execute(self, intent):
        return [intent]

def test_step4_9_intent_contains_explain_fields():
    cm = CellMasterBase(executor=DummyExecutor(), budget=None)

    node = {
        "meta": {
            "coord": (2, 3),
            "sources": ["antigen_peak", "danger_signal"]
        },
        "score": 3.5,
        "explain": {
            "antigen_peak": {"value": 1.5},
            "danger_signal": {"value": 2.0}
        }
    }

    intents = cm.process_nodes([node])
    assert len(intents) == 1

    intent = intents[0]
    meta = intent["meta"]

    # 核心解释字段
    assert meta["score"] == 3.5
    assert meta["coord"] == (2, 3)
    assert set(meta["sources"]) == {"antigen_peak", "danger_signal"}

    # explain 是否完整透传
    assert "antigen_peak" in meta["event_explain"]
    assert "danger_signal" in meta["event_explain"]

    # 决策路径声明
    assert meta["decision_path"] == "rank→merge→node→budget"

