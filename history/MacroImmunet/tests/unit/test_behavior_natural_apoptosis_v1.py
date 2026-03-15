from tests.cell_tests.common.yaml_loader import load_yaml_rel
from tests.cell_tests.common.behavior_factory import instantiate_behavior_from_yaml
from tests.cell_tests.common.simple_cell_mock import SimpleCellMock
from tests.cell_tests.common.fake_env import FakeEnv

def _call(bh, cell, env, params, payload=None):
    try:
        if hasattr(bh, "execute"):
            return bh.execute(cell, env, params=params, payload=payload)
    except Exception:
        pass
    try:
        if callable(bh):
            return bh(cell, env, params, payload=payload)
    except Exception:
        pass
    return []

def test_natural_apoptosis_age_triggers():
    cfg = load_yaml_rel("behaviors/natural_apoptosis_v1.yaml")
    bh = instantiate_behavior_from_yaml("behaviors/natural_apoptosis_v1.yaml", cfg)

    env = FakeEnv()
    env.tick = 1000
    emitted = []
    env.emit_intent = lambda name,p: emitted.append((name,p))

    cell = SimpleCellMock(position=(0,0))
    cell.birth_tick = 0  # large age
    params = cfg.get("params", {})
    # set lifespan small to force deterministic apoptosis
    params["lifespan_ticks"] = 10
    env.tick = 20
    actions = _call(bh, cell, env, params, payload=None)
    assert isinstance(actions, (list, tuple))
    assert emitted or any(a.get("name") == "apoptosis" for a in actions)
