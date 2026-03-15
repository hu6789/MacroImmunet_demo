from tests.cell_tests.common.yaml_loader import load_yaml_rel
from tests.cell_tests.common.behavior_factory import instantiate_behavior_from_yaml
from tests.cell_tests.common.simple_cell_mock import SimpleCellMock

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

def test_antigen_diffusion_computes_and_applies_deltas():
    cfg = load_yaml_rel("behaviors/antigen_diffusion_hook_v1.yaml")
    bh = instantiate_behavior_from_yaml("behaviors/antigen_diffusion_hook_v1.yaml", cfg)

    # Fake env: provide read_field, get_neighbors and apply_field_deltas
    class E:
        def __init__(self):
            # simple 3x1 line centered at (0,0)
            self._map = {
                (0,0): 10.0,
                (1,0): 0.0,
                (-1,0): 0.0
            }
            self.applied = {}
        def read_field(self, field, coord):
            return self._map.get(coord, 0.0)
        def get_neighbors(self, coord, radius):
            x,y = coord
            return [(x+1,y),(x-1,y)]
        def apply_field_deltas(self, field, deltas):
            # store applied deltas for assertion
            self.applied = dict(deltas)

    env = E()
    cell = SimpleCellMock(position=(0,0))
    params = cfg.get("params", {})
    actions = _call(bh, cell, env, params, payload=None)
    assert isinstance(actions, (list, tuple))
    # expect apply_field_deltas called and produced deltas for center and neighbors
    assert env.applied, "expected deltas to be applied"
    assert (0,0) in env.applied
    assert (1,0) in env.applied and (-1,0) in env.applied
