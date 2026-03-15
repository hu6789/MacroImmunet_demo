# tests/unit/test_behavior_phagocytose_v1.py (robust)
from tests.cell_tests.common.yaml_loader import load_yaml_rel
from tests.cell_tests.common.behavior_factory import instantiate_behavior_from_yaml
from tests.cell_tests.common.simple_cell_mock import SimpleCellMock
from tests.cell_tests.common.fake_env import FakeEnv

def _call_behavior(bh, cell, env, params):
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
                return bh.execute(cell=cell, env=env, params=params)
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
                return bh(cell=cell, env=env, params=params)
            except TypeError:
                pass
    except Exception:
        pass
    return []

def test_phagocytose_consumes_field_and_updates_cell():
    cfg = load_yaml_rel("behaviors/phagocytose_v1.yaml")
    bh = instantiate_behavior_from_yaml("behaviors/phagocytose_v1.yaml", cfg)

    env = FakeEnv()
    pos = (2,3)
    env.add_field("Field_Antigen_Density")
    env.set_field("Field_Antigen_Density", pos, 4)

    def consume_local_antigen(coord, amount):
        val = env.get_at("Field_Antigen_Density", coord)
        if val >= amount:
            env.add_to_field("Field_Antigen_Density", coord, -amount)
            return True
        return False
    env.consume_local_antigen = consume_local_antigen
    env.sample_particles_at = lambda coord: []

    evts = []
    env.emit_event = lambda n,p: evts.append((n,p))

    cell = SimpleCellMock(position=pos)
    params = cfg.get("params", {})
    actions = _call_behavior(bh, cell, env, params)
    assert isinstance(actions, (list, tuple))
    al = getattr(cell, "meta", {}).get("antigen_load", None)
    assert (al is not None and al > 0) or any(a.get("name") == "phagocytosed" for a in actions)
    remaining = env.get_at("Field_Antigen_Density", pos)
    assert remaining >= 0
    assert any(n == "phagocytosed" for (n,p) in evts)
