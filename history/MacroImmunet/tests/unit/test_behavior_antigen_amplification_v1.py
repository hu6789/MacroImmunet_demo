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

def test_antigen_amplification_field_mode_applies_delta():
    cfg = load_yaml_rel("behaviors/antigen_amplification_v1.yaml")
    bh = instantiate_behavior_from_yaml("behaviors/antigen_amplification_v1.yaml", cfg)

    class E:
        def __init__(self):
            self._map = {(0,0): 10.0}
            self.added = []
        def read_field(self, field, coord):
            return self._map.get(coord, 0.0)
        def add_to_field(self, field, coord, delta):
            self.added.append((coord, delta))

    env = E()
    cell = SimpleCellMock(position=(0,0))
    params = cfg.get("params", {})
    # make replication large so delta detectable
    params["replication_rate_fold_per_tick"] = 2.0
    actions = _call(bh, cell, env, params, payload=None)
    assert isinstance(actions, (list, tuple))
    # ensure add_to_field called with a non-zero delta
    assert env.added, "expected add_to_field to be called"
    coord, delta = env.added[0]
    assert coord == (0,0)
    assert delta != 0
