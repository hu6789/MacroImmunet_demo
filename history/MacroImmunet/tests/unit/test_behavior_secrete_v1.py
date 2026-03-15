# tests/unit/test_behavior_secrete_v1.py
"""
Unit test for behaviors/secrete_v1.yaml -> behaviors_impl.secrete.secrete_v1
- verifies the behavior returns a 'secrete_field' action with molecule/rate/duration
- verifies env.emit_event is invoked (if available)
"""

from tests.cell_tests.common.yaml_loader import load_yaml_rel
from tests.cell_tests.common.behavior_factory import instantiate_behavior_from_yaml
from tests.cell_tests.common.simple_cell_mock import SimpleCellMock
from tests.cell_tests.common.fake_env import FakeEnv

def _call_behavior(bh, cell, env, params, payload=None):
    # tolerant invoker (see other tests)
    try:
        if hasattr(bh, "execute"):
            try:
                return bh.execute(cell, env, params, payload=payload)
            except TypeError:
                pass
            try:
                return bh.execute(cell=cell, env=env, params=params, payload=payload)
            except TypeError:
                pass
            try:
                return bh.execute(cell, env, params)
            except TypeError:
                pass
    except Exception:
        pass
    try:
        if callable(bh):
            try:
                return bh(cell, env, params, payload=payload)
            except TypeError:
                pass
            try:
                return bh(cell=cell, env=env, params=params, payload=payload)
            except TypeError:
                pass
    except Exception:
        pass
    return []

def test_secrete_returns_intent_and_emits_event():
    cfg = load_yaml_rel("behaviors/secrete_v1.yaml")
    bh = instantiate_behavior_from_yaml("behaviors/secrete_v1.yaml", cfg)

    env = FakeEnv()
    cell = SimpleCellMock(position=(1,1))
    events = []
    env.emit_event = lambda n,p: events.append((n,p))
    params = cfg.get("params", {})
    # provide molecule via payload to avoid None
    payload = {"molecule":"IL2", "rate_per_tick":1.0, "duration_ticks":3}

    actions = _call_behavior(bh, cell, env, params, payload=payload)
    assert isinstance(actions, (list, tuple))

    # expect at least one secrete_field action
    assert any(a.get("name") == "secrete_field" for a in actions), "expected a secrete_field action in returned actions"

    # check event emitted
    assert any(n in ("secreted",) for (n,p) in events), "expected secreted event to be emitted"
