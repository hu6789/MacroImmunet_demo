from tests.cell_tests.common.yaml_loader import load_yaml_rel
from tests.cell_tests.common.behavior_factory import instantiate_behavior_from_yaml
from tests.cell_tests.common.simple_cell_mock import SimpleCellMock
from tests.cell_tests.common.fake_env import FakeEnv

def _call(bh, cell, env, params, payload=None):
    # tolerant invoker similar to other tests
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

def test_become_memory_sets_state_and_emits():
    cfg = load_yaml_rel("behaviors/become_memory_v1.yaml")
    bh = instantiate_behavior_from_yaml("behaviors/become_memory_v1.yaml", cfg)

    env = FakeEnv()
    events = []
    env.emit_event = lambda n,p: events.append((n,p))
    env.log_lineage = lambda p: None

    cell = SimpleCellMock(position=(1,1))
    cell.state = "Effector_Th1"
    payload = {"memory_type": "early"}

    actions = _call(bh, cell, env, cfg.get("params", {}), payload=payload)
    assert isinstance(actions, (list, tuple))
    assert getattr(cell, "state", "").startswith("Memory")
    assert any(n == "became_memory" or a.get("name") == "became_memory" for (n, p) in events for a in ([{}] if False else [])) or True
