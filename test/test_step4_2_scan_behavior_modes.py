from label_center.label_center import LabelCenter
from scan_master.scan_master_base import ScanMasterBase
from cell_master.cell_master_base import CellMasterBase


# ---------- ScanMaster with behavior modes ----------
class ModeScanMaster(ScanMasterBase):
    def __init__(self, space):
        super().__init__(space)

    def scan(self, grid_summary):
        if (0, 0) not in grid_summary:
            return []

        pmhc = grid_summary[(0, 0)]["labels"].get("PMHC", 0.0)

        if pmhc < 1.0:
            return []

        NEXT_STEP = 0.5
        THRESHOLD = 3.0

        if pmhc + NEXT_STEP < THRESHOLD:
            behavior = "maintain"
        else:
            behavior = "expand"


        return [{
            "behavior": behavior,
            "meta": {
                "coord": (0, 0),
                "pmhc": pmhc,
            }
        }]


# ---------- CellMaster ----------
class DummyCellMaster(CellMasterBase):
    def handle_nodes(self, nodes, **kwargs):
        self.intent_queue = []

        for node in nodes:
            amount = 0.5 if node["behavior"] == "maintain" else 1.0

            self.intent_queue.append({
                "name": "emit_label",
                "payload": {
                    "coord": node["meta"]["coord"],
                    "label": "PMHC",
                    "amount": amount,
                }
            })

        return {"intents": self.intent_queue}


# ---------- World ----------
class DummyWorld:
    def __init__(self):
        self.label_center = LabelCenter()
        self.scan_master = ModeScanMaster(space=self)
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

        # bootstrap
        if not grid:
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
def test_step4_2_2_scan_behavior_modes():
    world = DummyWorld()

    # tick 0: bootstrap → PMHC = 1.0
    world.tick()
    summary = world.label_center.get_grid_summary()
    assert summary[(0, 0)]["labels"]["PMHC"] == 1.0

    # tick 1: maintain → +0.5
    world.tick()
    summary = world.label_center.get_grid_summary()
    assert summary[(0, 0)]["labels"]["PMHC"] == 1.5

    # tick 2: maintain → +0.5
    world.tick()
    summary = world.label_center.get_grid_summary()
    assert summary[(0, 0)]["labels"]["PMHC"] == 2.0

    # tick 3: still maintain → +0.5
    world.tick()
    summary = world.label_center.get_grid_summary()
    assert summary[(0, 0)]["labels"]["PMHC"] == 2.5

    # tick 4: now scan sees pmhc >= 3.0 → expand
    world.tick()
    summary = world.label_center.get_grid_summary()
    assert summary[(0, 0)]["labels"]["PMHC"] >= 3.5

    # tick 5: expand
    world.tick()
    summary = world.label_center.get_grid_summary()
    assert summary[(0, 0)]["labels"]["PMHC"] >= 3.5

