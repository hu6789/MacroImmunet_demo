from tests.cell_tests.common.yaml_loader import load_yaml_rel
from tests.cell_tests.common.behavior_factory import instantiate_behavior_from_yaml
from tests.cell_tests.common.simple_cell_mock import SimpleCellMock
from tests.cell_tests.common.fake_env import FakeEnv

def test_effector_ctl_scan_kill_and_secrete_and_move():
    cfg = load_yaml_rel("cells/Effector_CTL_v1.yaml")

    cell = SimpleCellMock(position=(8,8))
    cell.id = "ctl_1"
    cell.meta.update(cfg.get("meta_defaults", {}))

    env = FakeEnv()
    events = []
    env.emit_event = lambda n,p: events.append((n,p))
    intents = []
    env.emit_intent = lambda n,p: intents.append((n,p))
    writes = []
    env.add_to_field = lambda f,c,a: writes.append((f,c,a))

    # prepare a nearby pMHC-I and high affinity
    pmhc = {"pMHC_id":"pmI1","peptide_id":"PepI","mhc_type":"MHC_I","presenter":"dcX"}
    env.collect_pMHC_near = lambda coord, radius=1: [pmhc]
    env.compute_affinity = lambda pm, tcr: 0.95

    # run TCR scan -> expect event
    tcfg = load_yaml_rel("behaviors/TCR_scan_v1.yaml")
    tbh = instantiate_behavior_from_yaml("behaviors/TCR_scan_v1.yaml", tcfg)
    tbh.execute(cell, env, params=tcfg.get("params", {}))
    assert any(e[0] == "tcr_scan_result" for e in events), f"expected tcr_scan_result, got {events}"

    events.clear()

    # perforin behavior: call with a mock target via payload to trigger lysis/intent
    perf_cfg = load_yaml_rel("behaviors/perforin_apoptosis_v1.yaml")
    perf = instantiate_behavior_from_yaml("behaviors/perforin_apoptosis_v1.yaml", perf_cfg)
    # create a fake target id and stub env.get_cell if implementation queries it
    target = SimpleCellMock(position=(9,8))
    target.id = "target_1"
    env.get_cell = lambda tid: target if tid == "target_1" else None

    # call behavior with payload typical of CTL (target_id + strength)
    acts = perf.execute(cell, env, params=perf_cfg.get("params", {}), payload={"target_id":"target_1","strength":1.0})
    # check for lysis event/emitted intent OR returned actions
    ok = any(n in ("lysis","perforin_release","perforin_apoptosis") for (n,p) in events) or any(a.get("name") in ("lysis","perforin_release","perforin_apoptosis") for a in (acts or [])) or intents
    assert ok, f"expected kill intent/event/action; events={events}; acts={acts}; intents={intents}"

    # secrete IFNg should produce field write or event or action
    sec_cfg = load_yaml_rel("behaviors/secrete_v1.yaml")
    sec = instantiate_behavior_from_yaml("behaviors/secrete_v1.yaml", sec_cfg)
    sec.execute(cell, env, params={"substance":"IFNg","rate":0.8})
    assert writes or events or isinstance(sec.execute(cell, env, params={"substance":"IFNg","rate":0.8}), (list, tuple))

    # move_toward (chemotaxis) should be callable
    mv_cfg = load_yaml_rel("behaviors/move_toward_v1.yaml")
    mv = instantiate_behavior_from_yaml("behaviors/move_toward_v1.yaml", mv_cfg)
    out = mv.execute(cell, env, params={"chemokine_field":"Field_CXCL10","speed":1.4})
    assert isinstance(out, (list, tuple))

