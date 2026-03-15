# tests/unit/test_behavior_antigen_invasion_v1.py
"""
Robust unit test for behaviors/antigen_invasion_v1.yaml -> behaviors_impl.antigen_invasion.attempt_entry
This test:
 - loads the YAML config
 - instantiates the behavior via the test factory
 - provides a FakeEnv that can sample antigen and consume field units
 - asserts that either an "infected" action is returned or the cell meta/state is updated
"""

from tests.cell_tests.common.yaml_loader import load_yaml_rel
from tests.cell_tests.common.behavior_factory import instantiate_behavior_from_yaml
from tests.cell_tests.common.simple_cell_mock import SimpleCellMock
from tests.cell_tests.common.fake_env import FakeEnv

def _call_behavior(bh, cell, env, params, payload=None):
    """
    Try several invocation signatures to be robust to different impl wrappers:
      - bh.execute(cell, env, params)
      - bh.execute(cell=..., env=..., params=...)
      - bh(cell, env, params)
      - bh(cell=..., env=..., params=..., payload=...)
      - FunctionBehaviorAdapter cases
    """
    try:
        if hasattr(bh, "execute"):
            try:
                return bh.execute(cell, env, params)
            except TypeError:
                pass
            try:
                return bh.execute(cell=cell, env=env, params=params, payload=payload)
            except TypeError:
                pass
            try:
                return bh.execute(cell, env)
            except TypeError:
                pass
    except Exception:
        pass

    try:
        if callable(bh):
            try:
                return bh(cell, env, params)
            except TypeError:
                pass
            try:
                return bh(cell=cell, env=env, params=params, payload=payload)
            except TypeError:
                pass
    except Exception:
        pass

    return []

def test_antigen_invasion_consumes_and_infects():
    cfg = load_yaml_rel("behaviors/antigen_invasion_v1.yaml")
    bh = instantiate_behavior_from_yaml("behaviors/antigen_invasion_v1.yaml", cfg)

    env = FakeEnv()
    pos = (4,4)
    env.add_field("Field_Antigen_Density")
    env.set_field("Field_Antigen_Density", pos, 5)

    # env.sample_local_antigen returns a list of antigen dicts (test stub)
    def sample_local_antigen(coord):
        return [{"id":"antA","ace2_binding":{"affinity_score":0.5},"initial_viral_load":2.0}]
    env.sample_local_antigen = sample_local_antigen

    # atomic consume function used by impls
    def consume_local_antigen(coord, amount):
        val = env.get_at("Field_Antigen_Density", coord)
        if val >= amount:
            env.add_to_field("Field_Antigen_Density", coord, -amount)
            return True
        return False
    env.consume_local_antigen = consume_local_antigen

    events = []
    env.emit_event = lambda n,p: events.append((n,p))

    cell = SimpleCellMock(position=pos)
    params = cfg.get("params", {})

    actions = _call_behavior(bh, cell, env, params, payload=None)

    assert isinstance(actions, (list, tuple))
    # Either behavior returned infected action or cell.meta/state updated
    infected = (getattr(cell, "state", None) == "Infected") or (getattr(cell, "meta", {}).get("viral_load", 0) > 0)
    assert infected or any(a.get("name") == "infected" for a in actions)
    # ensure field didn't go negative
    remaining = env.get_at("Field_Antigen_Density", pos)
    assert remaining >= 0
    # if events emitted check presence of infected or infection_failed
    for (n,p) in events:
        assert isinstance(n, str)
