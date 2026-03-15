# tests/unit/test_behavior_move_toward_v1.py
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

def test_move_toward_chemotaxis():
    cfg = load_yaml_rel("behaviors/move_toward_v1.yaml")
    bh = instantiate_behavior_from_yaml("behaviors/move_toward_v1.yaml", cfg)

    env = FakeEnv()
    env.find_best_neighbor_by_field_gradient = lambda coord, field, max_step, sens: (coord[0] + 1, coord[1])
    env.coord_has_capacity = lambda c: True

    cell = SimpleCellMock(position=(0,0))
    payload = {"mode": "chemotaxis", "chemokine": "Field_CCL21"}
    actions = _call(bh, cell, env, cfg.get("params", {}), payload=payload)
    assert isinstance(actions, (list, tuple))
    assert any(a.get("name") == "move" for a in actions)

