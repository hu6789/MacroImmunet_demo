# tests/unit/test_behavior_differentiate_v1.py
from tests.cell_tests.common.yaml_loader import load_yaml_rel
from tests.cell_tests.common.behavior_factory import instantiate_behavior_from_yaml
from tests.cell_tests.common.simple_cell_mock import SimpleCellMock
from tests.cell_tests.common.fake_env import FakeEnv

def _call(bh, cell, env, params, payload=None):
    if hasattr(bh, "execute"):
        try:
            return bh.execute(cell, env, params=params, payload=payload)
        except TypeError:
            try:
                return bh.execute(cell, env, payload=payload)
            except TypeError:
                return bh.execute(cell, env, params)
    if callable(bh):
        try:
            return bh(cell, env, params=params, payload=payload)
        except TypeError:
            return bh(cell, env, payload=payload)
    return []

def test_differentiate_changes_state_and_emits():
    cfg = load_yaml_rel("behaviors/differentiate_v1.yaml")
    bh = instantiate_behavior_from_yaml("behaviors/differentiate_v1.yaml", cfg)

    env = FakeEnv()
    events = []
    env.emit_event = lambda n,p: events.append((n,p))

    cell = SimpleCellMock(position=(1,1))
    cell.state = "Naive"
    payload = {"target_state": "Effector_Th1", "probability": 1.0, "cause": "test"}
    actions = _call(bh, cell, env, cfg.get("params", {}), payload=payload)
    assert isinstance(actions, (list, tuple))
    assert getattr(cell, "state", None) == "Effector_Th1"
    assert any(n == "state_changed" for (n,p) in events)

