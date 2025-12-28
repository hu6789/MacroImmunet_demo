from label_center.label_center import LabelCenter
from scan_master.scan_master_base import ScanMasterBase


class TopKScanMaster(ScanMasterBase):
    def __init__(self, space, k=2):
        super().__init__(space)
        self.k = k

    def scan(self, grid_summary):
        nodes = []

        for coord, info in grid_summary.items():
            pmhc = info["labels"].get("PMHC", 0.0)
            if pmhc <= 0:
                continue

            nodes.append({
                "behavior": "hotspot",
                "score": pmhc,
                "meta": {
                    "coord": coord,
                    "pmhc": pmhc,
                }
            })

        # 🔑 Top-K by score
        nodes.sort(key=lambda x: x["score"], reverse=True)
        return nodes[: self.k]


def test_step4_3_2_scan_topk():
    lc = LabelCenter()

    # 构造 3 个热点
    lc.enqueue_intents([
        {"name": "emit_label", "payload": {"coord": (0, 0), "label": "PMHC", "amount": 1.0}},
        {"name": "emit_label", "payload": {"coord": (1, 0), "label": "PMHC", "amount": 3.0}},
        {"name": "emit_label", "payload": {"coord": (2, 0), "label": "PMHC", "amount": 2.0}},
    ], source="test", tick=0)

    lc.apply_tick(0)

    scan = TopKScanMaster(space=None, k=2)
    summary = lc.get_grid_summary()

    nodes = scan.scan(summary)

    coords = [n["meta"]["coord"] for n in nodes]

    # ✅ 只选 Top-2
    assert len(nodes) == 2
    assert (1, 0) in coords  # PMHC = 3.0
    assert (2, 0) in coords  # PMHC = 2.0
    assert (0, 0) not in coords

