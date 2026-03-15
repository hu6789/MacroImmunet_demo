# tests/unit/test_cell_epithelial_v1.py
from tests.cell_tests.common.yaml_loader import load_yaml_rel
from tests.cell_tests.common.behavior_factory import instantiate_behavior_from_yaml
from types import SimpleNamespace
from tests.cell_tests.common.fake_env import FakeEnv

def test_epithelial_infection_to_release_cycle():
    inv_cfg = load_yaml_rel("behaviors/antigen_invasion_v1.yaml")
    rep_cfg = load_yaml_rel("behaviors/antigen_replication_v1.yaml")
    rel_cfg = load_yaml_rel("behaviors/antigen_release_v1.yaml")

    inv_bh = instantiate_behavior_from_yaml("behaviors/antigen_invasion_v1.yaml", inv_cfg)
    rep_bh = instantiate_behavior_from_yaml("behaviors/antigen_replication_v1.yaml", rep_cfg)
    rel_bh = instantiate_behavior_from_yaml("behaviors/antigen_release_v1.yaml", rel_cfg)

    env = FakeEnv()
    events = []
    env.emit_event = lambda n,p: events.append((n,p))
    writes = []
    env.add_to_field = lambda f, coord, amt: writes.append((f, coord, amt))

    cell = SimpleNamespace()
    cell.id = "epi_test_1"
    cell.coord = (5,5)
    # copy meta defaults
    cfg = load_yaml_rel("cells/Epithelial_Lung_Cell_v1.yaml")
    cell.meta = dict(cfg.get("meta", {}))

    # step 1: invasion with probability forcing infection
    inv_payload = {"antigen_id":"Antigen_SARS_like_001", "probability":1.0}
    inv_bh.execute(cell, env, params=inv_cfg.get("params", {}), payload=inv_payload)

    # after invasion expect infected flag or viral_load > 0
    assert getattr(cell, "state", None) in ("Infected","infected","Compromised") or cell.meta.get("viral_load", 0) > 0

    # step 2: replicate a few ticks
    for _ in range(3):
        rep_bh.execute(cell, env, params=rep_cfg.get("params", {}))

    assert any(e[0] == "replicated" for e in events) or cell.meta.get("viral_load", 0) > 0

    # step 3: simulate death -> release
    rel_bh.execute(cell, env, params=rel_cfg.get("params", {}))
    # expect field write or spawn event
    assert any(w[0] == "Field_Antigen_Density" for w in writes) or any(e[0] == "released" for e in events)

