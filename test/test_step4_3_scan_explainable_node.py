from label_center.label_center import LabelCenter
from scan_master.recency_cooldown_scan_master import RecencyCooldownScanMaster


def test_step4_3_5_scan_explainable_node():
    lc = LabelCenter()
    scan = RecencyCooldownScanMaster(k=1, cooldown=1)

    # tick 0: two hotspots
    lc.enqueue_intents([
        {"name": "emit_label", "payload": {"coord": (0, 0), "label": "PMHC", "amount": 2.0}},
        {"name": "emit_label", "payload": {"coord": (1, 0), "label": "PMHC", "amount": 3.0}},
    ], source="test", tick=0)
    lc.apply_tick(0)

    summary = lc.get_grid_summary()
    nodes = scan.scan(summary, tick=0)

    assert len(nodes) == 1

    node = nodes[0]
    meta = node["meta"]

    # ---------- explainable meta ----------
    assert "coord" in meta
    assert "score" in meta
    assert "pmhc" in meta
    assert "rank" in meta

    # ---------- correctness ----------
    assert meta["coord"] == (1, 0)
    assert meta["pmhc"] == 3.0
    assert meta["rank"] == 0
    assert meta["score"] >= meta["pmhc"]

