from tests.cell_tests.common.yaml_loader import load_yaml_rel
from tests.cell_tests.common.behavior_factory import instantiate_behavior_from_yaml
from tests.cell_tests.common.fake_env import FakeEnv

def test_chemotaxis_triggers_move_toward():
    cfg = load_yaml_rel("behaviors/move_toward_v1.yaml")
    bh = instantiate_behavior_from_yaml("behaviors/move_toward_v1.yaml", cfg)

    moves = []
    env = FakeEnv()
    env.emit_intent = lambda n,p: moves.append((n,p))
    # stub best neighbor finder
    env.find_best_neighbor_by_field_gradient = lambda coord, field, max_step, sens: (coord[0]+1, coord[1])
    env.coord_has_capacity = lambda c: True

    cell = type("C", (), {})()
    cell.id = "m1"
    cell.coord = (1,1)

    actions = bh.execute(cell, env, params=cfg.get("params", {}), payload={"mode":"chemotaxis","chemokine":"Field_CCL21"})
    # expect move action and emit_intent call
    assert isinstance(actions, (list, tuple))
    assert any(a.get("name") == "move" for a in actions), f"no move action: {actions}"
    assert any(m[0] == "move" for m in moves), f"no move emit: {moves}"

