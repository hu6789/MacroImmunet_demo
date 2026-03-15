# tests/unit/test_behavior_dc_upregulate_costim.py
from tests.cell_tests.common.yaml_loader import load_yaml_rel
from tests.cell_tests.common.behavior_factory import instantiate_behavior_from_yaml
from tests.cell_tests.common.simple_cell_mock import SimpleCellMock
from tests.cell_tests.common.fake_env import FakeEnv

def test_dc_upregulate_increases_costim_and_emits_secrete():
    cfg = load_yaml_rel("behaviors/DC_upregulate_costim.yaml")
    bh = instantiate_behavior_from_yaml("behaviors/DC_upregulate_costim.yaml", cfg)

    env = FakeEnv()
    intents = []
    env.emit_intent = lambda name, p: intents.append((name, p))

    cell = SimpleCellMock(position=(0,0))
    cell.id = "dc_test"
    cell.co_stim = 0.1

    # call behavior with explicit payload overriding nothing (uses params)
    actions = bh.execute(cell, env, params=cfg.get("params", {}), payload={})
    assert isinstance(actions, (list, tuple))
    assert getattr(cell, "co_stim", None) == 0.1 + cfg.get("params", {}).get("costim_increase", 0.5)
    # secrete intent should have been emitted
    assert any(name == "secrete" for name, _ in intents)
    # check payload fields
    secrete_payload = [p for n, p in intents if n == "secrete"][0]
    assert secrete_payload.get("molecule") == "IL12"
    assert "rate_per_tick" in secrete_payload

def test_dc_upregulate_no_secrete_when_disabled():
    cfg = load_yaml_rel("behaviors/DC_upregulate_costim.yaml")
    bh = instantiate_behavior_from_yaml("behaviors/DC_upregulate_costim.yaml", cfg)

    env = FakeEnv()
    intents = []
    env.emit_intent = lambda name, p: intents.append((name, p))

    cell = SimpleCellMock(position=(0,0))
    cell.co_stim = 0.0

    # call with payload overriding to disable secretion
    payload = {"secrete_il12": False, "costim_increase": 0.2}
    actions = bh.execute(cell, env, params=cfg.get("params", {}), payload=payload)
    assert getattr(cell, "co_stim", None) == 0.2
    assert not any(name == "secrete" for name, _ in intents)

