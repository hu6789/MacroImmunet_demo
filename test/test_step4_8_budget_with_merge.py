from cell_master.cell_master_base import CellMasterBase
from scan_master.event import ScanEvent


class DummyExecutor:
    def run(self, nodes):
        return [{"coord": n["meta"]["coord"], "score": n["score"]} for n in nodes]


class DummyCellMaster(CellMasterBase):
    def process_nodes(self, nodes):
        return self.executor.run(nodes)


def test_step4_8_4_budget_applies_after_merge_and_rank():
    """
    多 coord、多事件，但 budget=1
    → 只处理 merge 后 score 最高的 coord
    """
    cm = DummyCellMaster(executor=DummyExecutor(), budget=1)

    events = [
        # coord A，总分 2.0
        ScanEvent(coord=(0, 0), value=1.0, type="antigen_peak", tick=1),
        ScanEvent(coord=(0, 0), value=1.0, type="danger_signal", tick=2),

        # coord B，总分 5.0（应被选中）
        ScanEvent(coord=(1, 1), value=3.0, type="antigen_peak", tick=1),
        ScanEvent(coord=(1, 1), value=2.0, type="danger_signal", tick=2),
    ]

    intents = cm.consume_events(events)

    assert len(intents) == 1
    assert intents[0]["coord"] == (1, 1)
    assert intents[0]["score"] == 5.0

