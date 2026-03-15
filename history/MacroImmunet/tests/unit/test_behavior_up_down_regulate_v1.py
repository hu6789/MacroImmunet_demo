# tests/unit/test_behavior_up_down_regulate_v1.py
from tests.cell_tests.common.yaml_loader import load_yaml_rel
from tests.cell_tests.common.behavior_factory import instantiate_behavior_from_yaml
from tests.cell_tests.common.simple_cell_mock import SimpleCellMock
from tests.cell_tests.common.fake_env import FakeEnv

def test_up_down_regulate_applies_and_schedules():
    cfg = load_yaml_rel("behaviors/up_down_regulate_v1.yaml")
    bh = instantiate_behavior_from_yaml("behaviors/up_down_regulate_v1.yaml", cfg)

    env = FakeEnv()
    scheduled = []
    def schedule_task(req):
        scheduled.append(req)
    env.schedule_task = schedule_task

    events = []
    env.emit_event = lambda n,p: events.append((n,p))

    cell = SimpleCellMock(position=(0,0))
    cell.id = "cellX"
    # ensure internal exists
    cell.internal = {"adhesion_molecules": 1.0}

    payload = {"target": "adhesion_molecules", "fold_change": 1.5, "duration_ticks": 10}
    actions = bh.execute(cell, env, params=cfg.get("params", {}), payload=payload)

    # verify internal changed
    assert abs(cell.internal["adhesion_molecules"] - 1.0 * 1.5) < 1e-6
    # scheduled should have one item
    assert len(scheduled) == 1
    # emitted event recorded
    assert any(e[0] == "internal_regulated" for e in events)

