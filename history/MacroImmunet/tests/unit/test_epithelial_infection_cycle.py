import pytest
from tests.cell_tests.common.yaml_loader import load_yaml_rel
from tests.cell_tests.common.behavior_factory import instantiate_behavior_from_yaml
from tests.cell_tests.common.fake_env import FakeEnv

def test_epithelial_infection_cycle_minimal():
    # load YAMLs
    inv_cfg = load_yaml_rel("behaviors/antigen_invasion_v1.yaml")
    rep_cfg = load_yaml_rel("behaviors/antigen_replication_v1.yaml")
    rel_cfg = load_yaml_rel("behaviors/antigen_release_v1.yaml")

    inv_bh = instantiate_behavior_from_yaml("behaviors/antigen_invasion_v1.yaml", inv_cfg)
    rep_bh = instantiate_behavior_from_yaml("behaviors/antigen_replication_v1.yaml", rep_cfg)
    rel_bh = instantiate_behavior_from_yaml("behaviors/antigen_release_v1.yaml", rel_cfg)

    events = []
    env = FakeEnv()
    env.emit_event = lambda n,p: events.append((n,p))
    # capture writes to field
    writes = []
    env.add_to_field = lambda field, coord, amount: writes.append((field, coord, amount))

    # setup cell (epithelial)
    cell = type("C", (), {})()
    cell.id = "epi1"
    cell.coord = (5,5)
    cell.state = "Healthy"

    # 1) simulate invasion payload (should mark infected / set meta)
    inv_payload = {"antigen_id": "Antigen_SARS_like_001", "probability": 1.0}
    inv_bh.execute(cell, env, params=inv_cfg.get("params", {}), payload=inv_payload)

    # ensure infected/meta set (impls may vary)
    assert getattr(cell, "state", None) in ("Infected", "infected", "Compromised") or getattr(cell, "meta", {}).get("viral_load") is not None

    # 2) run replication a few ticks
    rep_params = rep_cfg.get("params", {})
    for _ in range(3):
        rep_bh.execute(cell, env, params=rep_params)

    # expect a 'replicated' event (impls usually emit it)
    assert any(e[0] == "replicated" for e in events), f"no replicated event: {events}"

    # 3) simulate death -> call release behavior (we call directly)
    rel_params = rel_cfg.get("params", {})
    rel_bh.execute(cell, env, params=rel_params)

    # expect field write OR spawn
    assert any(w[0] == "Field_Antigen_Density" for w in writes) or any(e[0] == "released" for e in events)

