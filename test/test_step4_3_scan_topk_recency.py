from label_center.label_center import LabelCenter
from scan_master.scan_master_base import ScanMasterBase


class RecencyTopKScanMaster(ScanMasterBase):
    def __init__(self, space, k=1, recency_bonus=2.0):
        super().__init__(space)
        self.k = k
        self.recency_bonus = recency_bonus
        self.last_seen = {}  # coord -> tick

    def scan(self, grid_summary, tick=0):
        nodes = []

        for coord, info in grid_summary.items():
            pmhc = info["labels"].get("PMHC", 0.0)
            if pmhc <= 0:
                continue

            # 🔑 recency logic
            last = self.last_seen.get(coord, None)
            bonus = self.recency_bonus if last is None else 0.0

            score = pmhc + bonus

            nodes.append({
                "behavior": "hotspot",
                "score": score,
                "meta": {
                    "coord": coord,
                    "pmhc": pmhc,
                    "bonus": bonus,
                }
            })

        nodes.sort(key=lambda x: x["score"], reverse=True)
        selected = nodes[: self.k]

        # 🔑 update last_seen
        for n in selected:
            self.last_seen[n["meta"]["coord"]] = tick

        return selected


def test_step4_3_3_scan_topk_recency():
    lc = LabelCenter()

    # tick 0: 老热点
    lc.enqueue_intents([
        {"name": "emit_label", "payload": {"coord": (0, 0), "label": "PMHC", "amount": 3.0}},
    ], source="test", tick=0)
    lc.apply_tick(0)

    scan = RecencyTopKScanMaster(space=None, k=1, recency_bonus=2.0)

    summary = lc.get_grid_summary()
    nodes = scan.scan(summary, tick=0)

    assert nodes[0]["meta"]["coord"] == (0, 0)

    # tick 1: 新热点出现，但 PMHC 较低
    lc.enqueue_intents([
        {"name": "emit_label", "payload": {"coord": (1, 0), "label": "PMHC", "amount": 1.5}},
    ], source="test", tick=1)
    lc.apply_tick(1)

    summary = lc.get_grid_summary()
    nodes = scan.scan(summary, tick=1)

    # 🔥 新热点因 recency bonus 被选中
    assert nodes[0]["meta"]["coord"] == (1, 0)

