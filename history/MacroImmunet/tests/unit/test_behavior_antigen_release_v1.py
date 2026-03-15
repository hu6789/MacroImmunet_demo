import pytest
from tests.cell_tests.common.yaml_loader import load_yaml_rel
from tests.cell_tests.common.behavior_factory import instantiate_behavior_from_yaml
from tests.cell_tests.common.fake_env import FakeEnv

def test_antigen_release_on_death_honors_min_and_spawns():
    cfg = load_yaml_rel("behaviors/antigen_release_v1.yaml")
    bh = instantiate_behavior_from_yaml("behaviors/antigen_release_v1.yaml", cfg)

    env = FakeEnv()
    # record spawn calls
    spawns = []
    env.spawn_antigen = lambda coord, count: spawns.append((coord, int(count)))
    # also provide add_to_field in case implementation falls back
    env.add_to_field = lambda fname, coord, count: spawns.append((coord, int(count)))

    # no global cap helper -> full planned spawn allowed
    cell = type("C", (), {})()
    cell.id = "cell_dead_1"
    cell.coord = (5,5)
    # ensure sufficient internal viral load
    cell.meta = {"viral_load": 10.0}

    # set params to deterministic: release_probability 1.0 so it always releases
    params = dict(cfg.get("params", {}))
    params["release_probability"] = 1.0
    params["release_burst_yield"] = 20
    params["release_min_internal_load"] = 1.0
    # call behavior (simulate state transition handler calling it)
    actions = bh.execute(cell, env, params=params, payload={})

    # expect spawn to be called (spawned > 0)
    assert len(spawns) >= 1, f"expected spawn calls, got {spawns}"
    # expect an action returned describing release
    assert any(a.get("name") == "antigen_released" for a in (actions or [])), f"actions: {actions}"

def test_antigen_release_respects_minimum_load_and_probability():
    cfg = load_yaml_rel("behaviors/antigen_release_v1.yaml")
    bh = instantiate_behavior_from_yaml("behaviors/antigen_release_v1.yaml", cfg)

    env = FakeEnv()
    spawns = []
    env.spawn_antigen = lambda coord, count: spawns.append((coord, int(count)))
    # case1: low internal load -> no spawn
    cell = type("C", (), {})()
    cell.id = "cell_low"
    cell.coord = (2,2)
    cell.meta = {"viral_load": 1.0}
    params = dict(cfg.get("params", {}))
    params["release_min_internal_load"] = 5.0
    params["release_probability"] = 1.0
    actions = bh.execute(cell, env, params=params, payload={})
    assert len(spawns) == 0, "expected no spawn when viral_load < min_internal"

    # case2: high load but probability 0 -> no spawn
    cell2 = type("C", (), {})()
    cell2.id = "cell_prob_zero"
    cell2.coord = (3,3)
    cell2.meta = {"viral_load": 100.0}
    params2 = dict(cfg.get("params", {}))
    params2["release_min_internal_load"] = 1.0
    params2["release_probability"] = 0.0
    actions2 = bh.execute(cell2, env, params=params2, payload={})
    assert len(spawns) == 0, "expected no spawn when probability is zero"

