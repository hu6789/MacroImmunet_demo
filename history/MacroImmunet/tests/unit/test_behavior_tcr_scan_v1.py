# tests/unit/test_behavior_tcr_scan_v1.py
from tests.cell_tests.common.yaml_loader import load_yaml_rel
from tests.cell_tests.common.behavior_factory import instantiate_behavior_from_yaml
from tests.cell_tests.common.simple_cell_mock import SimpleCellMock
from tests.cell_tests.common.fake_env import FakeEnv

def test_tcr_scan_reports_best_affinity():
    cfg = load_yaml_rel("behaviors/TCR_scan_v1.yaml")
    bh = instantiate_behavior_from_yaml("behaviors/TCR_scan_v1.yaml", cfg)

    env = FakeEnv()
    events = []
    env.emit_event = lambda n,p: events.append((n,p))

    # stub env.collect_pMHC_near and env.compute_affinity
    def collect(coord, radius):
        return [
            {"pMHC_id":"pm1","peptide_id":"AAA","mhc_type":"MHC_II"},
            {"pMHC_id":"pm2","peptide_id":"BBB","mhc_type":"MHC_II"},
        ]
    env.collect_pMHC_near = collect
    def compute_aff(pm, tcr):
        # simple affinity: 1.0 if match target_peptide
        return 1.0 if pm.get("peptide_id") == tcr.get("target_peptide") else 0.0
    env.compute_affinity = compute_aff

    cell = SimpleCellMock(position=(0,0))
    cell.id = "Tcell1"
    # TCR repertoire with one matching TCR for "BBB"
    cell.tcr_repertoire = [{"id":"t1","target_peptide":"BBB"}]

    actions = bh.execute(cell, env, params=cfg.get("params", {}))
    assert isinstance(actions, (list, tuple))
    # expect tcr_scan_result action returned
    assert any(a.get("name") == "tcr_scan_result" for a in actions)
    # event emitted with best_affinity 1.0
    assert any(n == "tcr_scan_result" and p.get("best_affinity") == 1.0 for (n,p) in events)

