# tests/unit/test_behavior_present_v1.py
from tests.cell_tests.common.yaml_loader import load_yaml_rel
from tests.cell_tests.common.behavior_factory import instantiate_behavior_from_yaml
from tests.cell_tests.common.simple_cell_mock import SimpleCellMock
from tests.cell_tests.common.fake_env import FakeEnv

def test_present_extracts_kmers_and_emits():
    cfg = load_yaml_rel("behaviors/present_v1.yaml")
    bh = instantiate_behavior_from_yaml("behaviors/present_v1.yaml", cfg)

    env = FakeEnv()
    events = []
    env.emit_event = lambda n,p: events.append((n,p))

    cell = SimpleCellMock(position=(0,0))
    cell.id = "dcA"
    # antigen with sequence (will generate kmers)
    cell.captured_antigens = [{"id":"ag1", "sequence":"ABCDEFGHIJKL"}]
    cell.present_list = []

    actions = bh.execute(cell, env, params=cfg.get("params", {}))
    assert isinstance(actions, (list, tuple))
    # expect at least one pMHC_presented
    assert any(a.get("name") == "pMHC_presented" for a in actions)
    # cell.present_list populated
    assert len(cell.present_list) > 0
    # event emitted
    assert any(n == "pMHC_presented" for (n,p) in events)

def test_present_uses_epitope_list_and_deduplicates():
    cfg = load_yaml_rel("behaviors/present_v1.yaml")
    bh = instantiate_behavior_from_yaml("behaviors/present_v1.yaml", cfg)

    env = FakeEnv()
    events = []
    env.emit_event = lambda n,p: events.append((n,p))

    cell = SimpleCellMock(position=(0,0))
    cell.id = "dcB"
    # antigen with explicit epitope list and duplicated peptides across antigens
    cell.captured_antigens = [
        {"id":"ag1","epitopes":[{"id":"E1","seq":"AAAAA"},{"id":"E2","seq":"BBBBB"}]},
        {"id":"ag2","epitopes":[{"id":"E1","seq":"AAAAA"},{"id":"E3","seq":"CCCCC"}]}
    ]
    cell.present_list = []

    actions = bh.execute(cell, env, params=cfg.get("params", {}))
    assert isinstance(actions, (list, tuple))
    # dedup enabled by default: peptide "AAAAA" only once
    peptides = [e.get("peptide_id") for e in cell.present_list]
    assert peptides.count("AAAAA") == 1

