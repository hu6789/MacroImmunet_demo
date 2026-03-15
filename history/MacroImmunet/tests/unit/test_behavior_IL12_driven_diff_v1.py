# tests/unit/test_behavior_IL12_driven_diff_v1.py
from tests.cell_tests.common.yaml_loader import load_yaml_rel
from tests.cell_tests.common.behavior_factory import instantiate_behavior_from_yaml
from tests.cell_tests.common.simple_cell_mock import SimpleCellMock
from tests.cell_tests.common.fake_env import FakeEnv
import math

def test_IL12_driven_diff_emits_change_state_with_probability():
    cfg = load_yaml_rel("behaviors/IL12_driven_diff_v1.yaml")
    bh = instantiate_behavior_from_yaml("behaviors/IL12_driven_diff_v1.yaml", cfg)

    env = FakeEnv()
    intents = []
    env.emit_intent = lambda name, p: intents.append((name, p))

    cell = SimpleCellMock(position=(0,0))
    cell.id = "TcellA"
    # set internal fields
    cell.IL12_local = 2.0
    cell.affinity = 0.9

    actions = bh.execute(cell, env, params=cfg.get("params", {}), payload={})
    assert isinstance(actions, (list, tuple))
    assert any(name == "change_state" for name, _ in intents)
    name, pl = [it for it in intents if it[0] == "change_state"][0]
    # compute expected probability using same formula
    K = cfg.get("params", {}).get("K", 0.4)
    n = cfg.get("params", {}).get("n", 2.0)
    base = cfg.get("params", {}).get("base_multiplier", 0.8)
    hill = (cell.IL12_local ** n) / ((K ** n) + (cell.IL12_local ** n))
    expected_p = max(0.0, min(1.0, base * hill * cell.affinity))
    assert math.isclose(pl.get("probability"), expected_p, rel_tol=1e-6)

def test_IL12_driven_diff_handles_missing_fields_and_zeroes():
    cfg = load_yaml_rel("behaviors/IL12_driven_diff_v1.yaml")
    bh = instantiate_behavior_from_yaml("behaviors/IL12_driven_diff_v1.yaml", cfg)

    env = FakeEnv()
    intents = []
    env.emit_intent = lambda name, p: intents.append((name, p))

    cell = SimpleCellMock(position=(0,0))
    cell.id = "TcellB"
    # no IL12_local or affinity provided -> probability should be zero
    actions = bh.execute(cell, env, params=cfg.get("params", {}), payload={})
    assert any(name == "change_state" for name, _ in intents)
    _, pl = [it for it in intents if it[0] == "change_state"][0]
    assert pl.get("probability") == 0.0

