# tests/unit/test_behavior_dc_process_v1.py
from tests.cell_tests.common.yaml_loader import load_yaml_rel
from tests.cell_tests.common.behavior_factory import instantiate_behavior_from_yaml
from tests.cell_tests.common.simple_cell_mock import SimpleCellMock
from tests.cell_tests.common.fake_env import FakeEnv

def test_dc_process_calls_present_and_migrate():
    cfg = load_yaml_rel("behaviors/DC_process_and_load_MHC_v1.yaml")
    bh = instantiate_behavior_from_yaml("behaviors/DC_process_and_load_MHC_v1.yaml", cfg)

    env = FakeEnv()
    events = []
    env.emit_event = lambda n,p: events.append((n,p))

    cell = SimpleCellMock(position=(5,5))
    cell.id = "dcX"
    # make sure there is at least one antigen
    cell.captured_antigens = [{"id":"ag1", "sequence":"ABCDEFGHIJKL"}]
    cell.present_list = []
    cell.co_stim = 0.0
    cell.maturation_state = "Immature"

    actions = bh.execute(cell, env, params=cfg.get("params", {}))
    assert isinstance(actions, (list, tuple))
    # should have pMHC_presented action and probably migrate_to_LN since co_stim increased
    assert any(a.get("name") == "pMHC_presented" for a in actions)
    assert any(a.get("name") == "migrate_to_LN" for a in actions)
    # maturation_state set to Mature
    assert getattr(cell, "maturation_state", None) == "Mature"
    # co_stim increased
    assert cell.co_stim > 0.0

