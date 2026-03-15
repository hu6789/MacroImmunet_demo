# tests/unit/test_behavior_survival_signal_v1.py
from tests.cell_tests.common.yaml_loader import load_yaml_rel
from tests.cell_tests.common.behavior_factory import instantiate_behavior_from_yaml
from tests.cell_tests.common.simple_cell_mock import SimpleCellMock
from tests.cell_tests.common.fake_env import FakeEnv

def test_survival_signal_updates_score_and_threshold():
    cfg = load_yaml_rel("behaviors/survival_signal_v1.yaml")
    bh = instantiate_behavior_from_yaml("behaviors/survival_signal_v1.yaml", cfg)

    # fake env with read_field and emit_event
    env = FakeEnv()
    # make tick available
    env.tick = 42
    # simple field store keyed by (coord, field)
    field_store = {((0,0), "Field_IL2"): 1.0, ((0,0), "Field_IL15"): 0.5}
    def read_field(coord, field):
        return field_store.get((coord, field), 0.0)
    env.read_field = read_field

    events = []
    env.emit_event = lambda name, payload: events.append((name, payload))

    cell = SimpleCellMock(position=(0,0))
    cell.coord = (0,0)
    cell.id = "cellA"
    cell.base_apoptosis_threshold = 0.2
    cell.survival_score = 0.0

    actions = bh.execute(cell, env, params=cfg.get("params", {}))
    assert isinstance(actions, (list, tuple))
    # check survival_score set > 0
    assert getattr(cell, "survival_score", 0.0) >= 0.0
    # apoptosis_threshold must be set and >= min_apoptosis_threshold
    assert getattr(cell, "apoptosis_threshold", None) is not None
    assert isinstance(events, list) and events and events[0][0] == "survival_boosted"

