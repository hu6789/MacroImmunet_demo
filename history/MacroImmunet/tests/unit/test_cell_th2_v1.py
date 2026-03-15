from tests.cell_tests.common.yaml_loader import load_yaml_rel
from tests.cell_tests.common.behavior_factory import instantiate_behavior_from_yaml
from tests.cell_tests.common.simple_cell_mock import SimpleCellMock
from tests.cell_tests.common.fake_env import FakeEnv

def test_th2_tcr_scan_il4_secrete_and_proliferate():
    cfg = load_yaml_rel("cells/Effector_Th2_v1.yaml")

    cell = SimpleCellMock(position=(6,6))
    cell.id = "th2_1"
    cell.meta.update(cfg.get("meta_defaults", {}))

    env = FakeEnv()
    events = []
    env.emit_event = lambda n,p: events.append((n,p))
    writes = []
    env.add_to_field = lambda f,c,a: writes.append((f,c,a))

    # TCR scan stub
    pmhc = {"pMHC_id":"pm2","peptide_id":"PepTh2","mhc_type":"MHC_II","presenter":"dcB"}
    env.collect_pMHC_near = lambda coord, radius=1: [pmhc]
    env.compute_affinity = lambda pm, tcr: 0.85

    tcfg = load_yaml_rel("behaviors/TCR_scan_v1.yaml")
    tbh = instantiate_behavior_from_yaml("behaviors/TCR_scan_v1.yaml", tcfg)
    tbh.execute(cell, env, params=tcfg.get("params", {}))
    assert any(e[0] == "tcr_scan_result" for e in events), f"expected tcr_scan_result, got {events}"

    events.clear()
    writes.clear()

    # secrete IL4 - accept field write OR emitted event OR returned action
    sec_cfg = load_yaml_rel("behaviors/secrete_v1.yaml")
    sec = instantiate_behavior_from_yaml("behaviors/secrete_v1.yaml", sec_cfg)
    sec.execute(cell, env, params={"substance":"IL4","rate":1.0})
    assert writes or events or isinstance(sec.execute(cell, env, params={"substance":"IL4","rate":1.0}), (list, tuple))

    # proliferate behavior should return an action list or be callable without error
    prol_cfg = load_yaml_rel("behaviors/proliferate_v1.yaml")
    prol = instantiate_behavior_from_yaml("behaviors/proliferate_v1.yaml", prol_cfg)
    acts = prol.execute(cell, env, params={"base_rate":0.08})
    assert isinstance(acts, (list, tuple))

