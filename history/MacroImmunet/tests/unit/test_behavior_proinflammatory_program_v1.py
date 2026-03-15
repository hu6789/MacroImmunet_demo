# tests/unit/test_behavior_proinflammatory_program_v1.py
from tests.cell_tests.common.yaml_loader import load_yaml_rel
from tests.cell_tests.common.behavior_factory import instantiate_behavior_from_yaml
from tests.cell_tests.common.simple_cell_mock import SimpleCellMock
from tests.cell_tests.common.fake_env import FakeEnv

def test_proinflammatory_emits_expected_intents():
    cfg = load_yaml_rel("behaviors/proinflammatory_program_v1.yaml")
    bh = instantiate_behavior_from_yaml("behaviors/proinflammatory_program_v1.yaml", cfg)

    env = FakeEnv()
    emitted = []
    env.emit_intent = lambda name, payload: emitted.append((name, payload))

    cell = SimpleCellMock(position=(0,0))
    # call behavior
    actions = bh.execute(cell, env, params=cfg.get("params", {}), payload={})

    # must be list/tuple
    assert isinstance(actions, (list, tuple))
    # env should have recorded three intents (secrete TNF, secrete IL12, regulate)
    names = [e[0] for e in emitted]
    assert "secrete" in names
    assert "regulate" in names

    # check payload shapes
    secrete_payloads = [p for n,p in emitted if n == "secrete"]
    assert any(p.get("molecule") == "TNF" for p in secrete_payloads)
    assert any(p.get("molecule") == "IL12" for p in secrete_payloads)

    regs = [p for n,p in emitted if n == "regulate"]
    assert len(regs) == 1
    assert regs[0].get("target") == "adhesion_molecules"

