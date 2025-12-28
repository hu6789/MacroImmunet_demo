import pytest

from cell_master.cell_master_base import CellMasterBase


# ---------- Dummy Components ----------

class DummyLabelCenter:
    def __init__(self):
        self.enqueued = []

    def enqueue_intents(self, intents, source=None, tick=None):
        self.enqueued.append({
            "intents": intents,
            "source": source,
            "tick": tick,
        })


class DummyExecutor:
    def apply_intents(self, *args, **kwargs):
        raise AssertionError(
            "executor.apply_intents should NOT be called when label_center exists"
        )


class DummyRegistry:
    """Empty behaviour registry placeholder"""
    def get(self, name):
        return None


class DummySpace:
    def __init__(self):
        self.label_center = DummyLabelCenter()


# ---------- CellMaster Stub ----------

class DummyCellMaster(CellMasterBase):
    def __init__(self, space):
        super().__init__(
            space=space,
            behaviour_registry=DummyRegistry(),
        )
        # 强行替换 executor，防止误调用
        self.executor = DummyExecutor()

    def _process_node_request(self, region_id, node, tick):
        # 直接返回一个 fake intent，绕过真实 behavior 逻辑
        return [{
            "type": "TEST_INTENT",
            "value": 1.0,
        }]


# ---------- Test ----------

def test_step3_2_cell_master_enqueues_intents():
    space = DummySpace()
    cm = DummyCellMaster(space)

    node_requests = [
        {"node": {"dummy": True}}
    ]

    res = cm.handle_node_requests(
        region_id="region_A",
        node_requests=node_requests,
        tick=42,
    )

    # 1️⃣ executor 不应被调用（否则 test 已直接失败）

    # 2️⃣ intent 应进入 label_center
    assert len(space.label_center.enqueued) == 1

    entry = space.label_center.enqueued[0]
    assert entry["source"] == "region_A"
    assert entry["tick"] == 42

    intents = entry["intents"]
    assert isinstance(intents, list)
    assert len(intents) == 1
    assert intents[0]["type"] == "TEST_INTENT"

    # 3️⃣ handle_node_requests 正常返回
    assert "intents" in res

