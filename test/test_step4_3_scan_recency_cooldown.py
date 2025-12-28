import math
from label_center.label_center import LabelCenter
from scan_master.scan_master_base import ScanMasterBase


class RecencyCooldownScanMaster(ScanMasterBase):
    def __init__(
        self,
        space,
        k=1,
        recency_weight=2.0,
        tau=2.0,
        cooldown=1,
        cooldown_penalty=5.0,
    ):
        super().__init__(space)
        self.k = k
        self.recency_weight = recency_weight
        self.tau = tau
        self.cooldown = cooldown
        self.cooldown_penalty = cooldown_penalty

        self.last_seen = {}
        self.cooldown_until = {}

    def _recency_bonus(self, coord, tick):
        if coord not in self.last_seen:
            return self.recency_weight * 2.0  # 👈 新节点抢占
        dt = tick - self.last_seen[coord]
        return self.recency_weight * math.exp(-dt / self.tau)


    def _cooldown_penalty(self, coord, tick):
        until = self.cooldown_until.get(coord, -1)
        if tick < until:
            return self.cooldown_penalty
        return 0.0

    def scan(self, grid_summary, tick=0):
        nodes = []

        for coord, info in grid_summary.items():
            pmhc = info["labels"].get("PMHC", 0.0)
            if pmhc <= 0:
                continue

            score = (
                pmhc
                + self._recency_bonus(coord, tick)
                - self._cooldown_penalty(coord, tick)
            )

            nodes.append({
                "behavior": "hotspot",
                "score": score,
                "meta": {"coord": coord, "pmhc": pmhc},
            })

        nodes.sort(key=lambda x: x["score"], reverse=True)
        selected = nodes[: self.k]

        for n in selected:
            coord = n["meta"]["coord"]
            self.last_seen[coord] = tick
            self.cooldown_until[coord] = tick + self.cooldown

        return selected


def test_step4_3_4_scan_recency_cooldown():
    lc = LabelCenter()
    scan = RecencyCooldownScanMaster(space=None, k=1, cooldown=1)

    # tick 0: 老热点
    lc.enqueue_intents([
        {"name": "emit_label", "payload": {"coord": (0, 0), "label": "PMHC", "amount": 3.0}},
    ], source="test", tick=0)
    lc.apply_tick(0)

    summary = lc.get_grid_summary()
    nodes = scan.scan(summary, tick=0)
    assert nodes[0]["meta"]["coord"] == (0, 0)

    # tick 1: 新热点
    lc.enqueue_intents([
        {"name": "emit_label", "payload": {"coord": (1, 0), "label": "PMHC", "amount": 2.0}},
    ], source="test", tick=1)
    lc.apply_tick(1)

    summary = lc.get_grid_summary()
    nodes = scan.scan(summary, tick=1)
    assert nodes[0]["meta"]["coord"] == (1, 0)

    # tick 2: B 在 cooldown，A 回归
    summary = lc.get_grid_summary()
    nodes = scan.scan(summary, tick=2)
    assert nodes[0]["meta"]["coord"] == (0, 0)

