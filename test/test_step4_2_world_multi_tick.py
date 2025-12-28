from label_center.label_center import LabelCenter
from scan_master.scan_master_base import ScanMasterBase
from cell_master.cell_master_base import CellMasterBase


# -------------------------
# Dummy Components
# -------------------------

class DummyScanMaster(ScanMasterBase):
    def scan(self, grid_summary):
        # Step4.2: 固定 hotspot
        return [{
            "behavior": "antigen_hotspot",
            "meta": {
                "coord": (0, 0),
                "antigen": 10.0,
            }
        }]


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


class DummyWorld:
    def __init__(self):
        self.label_center = LabelCenter()
        self.scan_master = DummyScanMaster(space=self)
        self.cell_master = DummyCellMaster(space=self)
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

        self.label_center.enqueue_intents(
            intents,
            source="cell_master",
            tick=self.tick_count
        )

        self.label_center.apply_tick(self.tick_count)

        self.tick_count += 1


# -------------------------
# Tests
# -------------------------

def test_step4_2_world_multi_tick_accumulation():
    world = DummyWorld()

    world.tick()
    world.tick()
    world.tick()

    summary = world.label_center.get_grid_summary()

    assert (0, 0) in summary
    assert summary[(0, 0)]["labels"]["PMHC"] >= 3.0
