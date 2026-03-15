from tests.cell_tests.common.yaml_loader import load_yaml_rel
from tests.cell_tests.common.behavior_factory import instantiate_behavior_from_yaml
from tests.cell_tests.common.simple_cell_mock import SimpleCellMock
from tests.cell_tests.common.fake_env import FakeEnv

def test_th1_tcr_scan_secrete_and_migrate():
    cfg = load_yaml_rel("cells/Effector_Th1_v1.yaml")

    # mock cell
    cell = SimpleCellMock(position=(4,4))
    cell.id = "th1_1"
    cell.meta.update(cfg.get("meta_defaults", {}))

    # environment stubs
    env = FakeEnv()
    events = []
    env.emit_event = lambda n,p: events.append((n,p))
    writes = []
    env.add_to_field = lambda f,c,a: writes.append((f,c,a))

    # TCR scan: provide a pmhc and affinity function
    pmhc = {"pMHC_id":"pm1","peptide_id":"PepTh1","mhc_type":"MHC_II","presenter":"dcA"}
    env.collect_pMHC_near = lambda coord, radius=1: [pmhc]
    env.compute_affinity = lambda pm, tcr: 0.9

    # instantiate TCR scan behavior and run
    tcfg = load_yaml_rel("behaviors/TCR_scan_v1.yaml")
    tbh = instantiate_behavior_from_yaml("behaviors/TCR_scan_v1.yaml", tcfg)
    tbh.execute(cell, env, params=tcfg.get("params", {}))
    assert any(e[0] == "tcr_scan_result" for e in events), f"expected tcr_scan_result, got {events}"

    events.clear()
    writes.clear()

    # secrete: expect either field write or event (IFNg)
    sec_cfg = load_yaml_rel("behaviors/secrete_v1.yaml")
    sec = instantiate_behavior_from_yaml("behaviors/secrete_v1.yaml", sec_cfg)
    sec.execute(cell, env, params={"substance":"IFNg","rate":1.0})
    assert writes or events or isinstance(sec.execute(cell, env, params={"substance":"IFNg","rate":1.0}), (list, tuple))

    # move_toward (migration helper) should return action or be no-op; at least must not raise
    mv_cfg = load_yaml_rel("behaviors/move_toward_v1.yaml")
    mv = instantiate_behavior_from_yaml("behaviors/move_toward_v1.yaml", mv_cfg)
    actions = mv.execute(cell, env, params={"chemokine_field":"Field_CCL19","speed":1.0})
    assert isinstance(actions, (list, tuple))

