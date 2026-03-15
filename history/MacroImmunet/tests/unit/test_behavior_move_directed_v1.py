# tests/unit/test_behavior_move_directed_v1.py
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

def test_move_directed_simple_forward():
    cfg = load_yaml_rel("behaviors/move_directed_v1.yaml")
    bh = instantiate_behavior_from_yaml("behaviors/move_directed_v1.yaml", cfg)

    env = FakeEnv()
    # stub env.coord_move_by_vector to return neighbor
    env.coord_move_by_vector = lambda coord, vec, max_step: (coord[0] + 1, coord[1])
    env.coord_has_capacity = lambda c: True
    env.get_neighbors = lambda coord: [(coord[0]+1, coord[1]), (coord[0], coord[1]+1)]

    cell = SimpleCellMock(position=(2,2))
    payload = {"dir_vector": (1,0)}
    actions = _call(bh, cell, env, cfg.get("params", {}), payload=payload)
    assert isinstance(actions, (list, tuple))
    assert any(a.get("name") == "move" for a in actions)

