from cell_master.cell_master_base import CellMasterBase


class DummyExecutor:
    def __init__(self):
        self.called = []

    def execute(self, intent):
        self.called.append(intent)
        return {"status": "ok", "name": intent.get("name")}


def test_step4_4_6_executor_called():
    executor = DummyExecutor()

    cm = CellMasterBase(
        executor=executor,
        budget=1,
        score_threshold=1.0
    )

    node = {
        "meta": {"coord": (1, 2)},
        "score": 5.0,
    }

    intents = cm.process_nodes([node])

    # executor 必须被调用
    assert len(executor.called) == 1
    assert executor.called[0]["name"] == "emit_label"

