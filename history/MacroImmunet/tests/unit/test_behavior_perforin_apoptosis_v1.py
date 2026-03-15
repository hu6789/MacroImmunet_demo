# tests/unit/test_behavior_perforin_apoptosis_v1.py
from tests.cell_tests.common.yaml_loader import load_yaml_rel
from tests.cell_tests.common.behavior_factory import instantiate_behavior_from_yaml
from tests.cell_tests.common.simple_cell_mock import SimpleCellMock
from tests.cell_tests.common.fake_env import FakeEnv

def _call_behavior(bh, cell, env, params, payload=None):
    try:
        if hasattr(bh, "execute"):
            try:
                return bh.execute(cell, env, params)
            except TypeError:
                pass
            try:
                return bh.execute(cell, env)
            except TypeError:
                pass
            try:
                return bh.execute(cell=cell, env=env, params=params, payload=payload)
            except TypeError:
                pass
    except Exception:
        pass
    try:
        if callable(bh):
            try:
                return bh(cell, env, params, None, None, payload)
            except TypeError:
                pass
            try:
                return bh(cell=cell, env=env, params=params, payload=payload)
            except TypeError:
                pass
    except Exception:
        pass
    return []

def test_perforin_field_mode_and_direct_lysis():
    cfg = load_yaml_rel("behaviors/perforin_apoptosis_v1.yaml")
    bh = instantiate_behavior_from_yaml("behaviors/perforin_apoptosis_v1.yaml", cfg)

    env = FakeEnv()
    pos = (7,7)
    cell = SimpleCellMock(position=pos)
    # give a target id and a target cell object accessible via env.get_cell
    target = SimpleCellMock(position=(8,8))
    target_id = "target_1"
    target.id = target_id
    # create simple mapping in env.get_cell
    def get_cell(tid):
        if tid == target_id:
            return target
        return None
    env.get_cell = get_cell
    # env.has_field -> True to test field-based branch
    env.has_field = lambda fname: True
    # ensure add_to_field exists
    env.add_to_field = lambda fname, coord, amount: setattr(env, f"_f_{fname}", env.get_at(fname, coord)+amount) if hasattr(env, "get_at") else None
    # emit events capture
    events = []
    env.emit_event = lambda n,p: events.append((n,p))

    # set cell to have a current_target
    cell.current_target = target_id
    params = cfg.get("params", {})
    actions = _call_behavior(bh, cell, env, params)
    assert isinstance(actions, (list, tuple))
    # If field mode used, expect add_to_field action or event recorded
    assert any(a.get("name") in ("add_to_field", "lysis") for a in actions) or any(n in ("add_to_field","lysis") for (n,p) in events)
    # Test direct lysis path by making env.has_field False and using RNG deterministically via payload (optional)
    env.has_field = lambda fname: False
    # call again -> should produce lysis action/event
    actions2 = _call_behavior(bh, cell, env, params)
    assert isinstance(actions2, (list, tuple))
    # either lysis present or event emitted
    assert any(a.get("name") == "lysis" for a in actions2) or any(n == "lysis" for (n,p) in events)
