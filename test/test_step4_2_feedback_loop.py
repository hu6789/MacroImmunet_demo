from label_center.label_center import LabelCenter
from scan_master.scan_master_base import ScanMasterBase
from cell_master.cell_master_base import CellMasterBase


# ---------- ScanMaster with threshold ----------
class ThresholdScanMaster(ScanMasterBase):
    def __init__(self, space, threshold=2.0):
        super().__init__(space)
        self.threshold = threshold

    def scan(self, grid_summary):
        # 没有任何 label → 静默
        if (0, 0) not in grid_summary:
            return []

        pmhc = grid_summary[(0, 0)]["labels"].get("PMHC", 0.0)

        # 🔑 阈值判断
        if pmhc < self.threshold:
            return []

        return [{
            "behavior": "antigen_hotspot",
            "meta": {
                "coord": (0, 0),
                "antigen": pmhc,
            }
        }]


# ---------- CellMaster ----------
class DummyCellMaster(CellMasterBase):
    def handle_nodes(self, nodes, **kwargs):
        self.intent_queue = []

        for node in nodes:
            self.intent_queue.append({
                "name": "emit_label",
                "payload": {
                    "coord": node["meta"]["coord"],
                    "label": "PMHC",
                    "amount": 1.0,
                }
            })

        return {"intents": self.intent_queue}


# ---------- World ----------
class DummyWorld:
    def __init__(self):
        self.label_center = LabelCenter()
        self.cell_master = DummyCellMaster(space=self)
        self.scan_master = ThresholdScanMaster(space=self, threshold=2.0)
        self.tick_count = 0

    def tick(self):
        grid = self.label_center.get_grid_summary()

        nodes = self.scan_master.scan(grid)

        result = self.cell_master.handle_nodes(
            nodes,
            region_id="default",
            tick=self.tick_count
        )

        intents = result.get("intents", [])

        # bootstrap：只在世界完全空的时候
        if not grid and not intents:
            intents = [{
                "name": "emit_label",
                "payload": {
                    "coord": (0, 0),
                    "label": "PMHC",
                    "amount": 1.0,
                }
            }]

        self.label_center.enqueue_intents(
            intents,
            source="world",
            tick=self.tick_count
        )

        self.label_center.apply_tick(self.tick_count)
        self.tick_count += 1


# ---------- TEST ----------
def test_step4_2_1_threshold_loop():
    world = DummyWorld()

    # tick 0: bootstrap → PMHC = 1
    world.tick()
    summary = world.label_center.get_grid_summary()
    assert summary[(0, 0)]["labels"]["PMHC"] == 1.0

    # tick 1: 低于阈值 → scan 不触发 → PMHC 不变
    world.tick()
    summary = world.label_center.get_grid_summary()
    assert summary[(0, 0)]["labels"]["PMHC"] == 1.0

    # 手动再推一次（模拟外部刺激 / 噪声）
    world.label_center.enqueue_intents([{
        "name": "emit_label",
        "payload": {
            "coord": (0, 0),
            "label": "PMHC",
            "amount": 1.0,
        }
    }], source="external", tick=world.tick_count)
    world.label_center.apply_tick(world.tick_count)
    world.tick_count += 1

    # tick 2: PMHC >= 2 → scan 激活 → CellMaster 放大
    world.tick()
    summary = world.label_center.get_grid_summary()
    assert summary[(0, 0)]["labels"]["PMHC"] >= 3.0

