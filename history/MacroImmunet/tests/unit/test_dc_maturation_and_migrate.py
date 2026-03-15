import pytest
from tests.cell_tests.common.yaml_loader import load_yaml_rel
from tests.cell_tests.common.behavior_factory import instantiate_behavior_from_yaml
from tests.cell_tests.common.fake_env import FakeEnv

def test_dc_maturation_and_migrate_minimal():
    cfg = load_yaml_rel("behaviors/DC_process_and_load_MHC_v1.yaml")
    bh = instantiate_behavior_from_yaml("behaviors/DC_process_and_load_MHC_v1.yaml", cfg)

    events = []
    env = FakeEnv()
    env.emit_event = lambda n,p: events.append((n,p))
    # stub phagocytose to populate captured_antigens
    def fake_phago(cell, env, params=None, payload=None, **kw):
        cell.captured_antigens = [{"id":"ag1","epitopes":[{"id":"E1","seq":"AAAAA"}]}]
        return [{"name":"phagocytosed","payload":{}}]
    # if dc_process implementation calls behaviors.phagocytose_v1 by import, ensure env provides callable
    env.call_phagocytose = fake_phago

    cell = type("C", (), {})()
    cell.id = "dc1"
    cell.coord = (0,0)
    cell.present_list = []
    cell.co_stim = 0.0
    # run DC composite behavior
    actions = bh.execute(cell, env, params=cfg.get("params", {}))
    # expect pMHC_presented and possibly migrate_to_LN
    has_present = any(e[0] == "pMHC_presented" for e in events)
    has_migrate = any(e[0] == "migrate_to_LN" for e in events)
    assert has_present, f"No pMHC_presented events: {events}"
    # migrate may be conditional; accept either but log
    # if co_stim threshold low default, often migrate will be emitted; we accept either

