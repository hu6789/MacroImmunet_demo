from cell_master.cell_master_base import CellMasterBase
from scan_master.scan_master_base import ScanEvent

class DummyExecutor:
    def __init__(self):
        self.called = []

    def execute(self, intent):
        self.called.append(intent)
        return {"ok": True}


def test_step4_8_cellmaster_consume_events():
    executor = DummyExecutor()

    cm = CellMasterBase(
        executor=executor,
        budget=1,
        score_threshold=0.0
    )

    e1 = ScanEvent(coord=(0, 0), value=1.0, type="antigen_peak", tick=1)
    e2 = ScanEvent(coord=(0, 0), value=2.0, type="danger_signal", tick=2)

    intents = cm.consume_events([e1, e2])

    # 只处理一个事件（budget=1）
    assert len(intents) == 1

    # executor 被调用
    assert len(executor.called) == 1

