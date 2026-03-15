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

def test_inflammatory_death_integrator_and_emission():
    cfg = load_yaml_rel("behaviors/inflammatory_death_v1.yaml")
    bh = instantiate_behavior_from_yaml("behaviors/inflammatory_death_v1.yaml", cfg)

    env = FakeEnv()
    # make read_field return big values to force death
    env.read_field = lambda field, coord: 10.0
    emitted = []
    env.emit_intent = lambda name,p: emitted.append((name,p))

    cell = SimpleCellMock(position=(0,0))
    params = cfg.get("params", {})
    actions = _call(bh, cell, env, params, payload=None)
    assert isinstance(actions, (list, tuple))
    # either emitted an intent or returned action with name 'lysis'/'apoptosis'
    assert emitted or any(a.get("name") in ("lysis","apoptosis") for a in actions)
