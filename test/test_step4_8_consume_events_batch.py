from cell_master.cell_master_base import CellMasterBase
from scan_master.event import ScanEvent


class DummyExecutor:
    def run(self, nodes):
        # 每个 node 生成一个 intent，占位即可
        return [{"coord": n["meta"]["coord"], "score": n["score"]} for n in nodes]


class DummyCellMaster(CellMasterBase):
    def process_nodes(self, nodes):
        return self.executor.run(nodes)


def test_step4_8_3_merge_events_same_coord_into_single_intent():
    cm = DummyCellMaster(executor=DummyExecutor(), budget=None)

    e1 = ScanEvent(
        coord=(2, 3),
        value=1.5,
        type="antigen_peak",
        tick=10,
    )

    e2 = ScanEvent(
        coord=(2, 3),
        value=2.0,
        type="danger_signal",
        tick=12,
    )

    intents = cm.consume_events([e1, e2])

    # 合并后应只产生一个 intent
    assert len(intents) == 1
    assert intents[0]["coord"] == (2, 3)
    assert intents[0]["score"] == 3.5

