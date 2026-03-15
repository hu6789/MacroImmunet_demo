# tests/unit/test_cell_dendritic_v1.py
from tests.cell_tests.common.yaml_loader import load_yaml_rel
from tests.cell_tests.common.behavior_factory import instantiate_behavior_from_yaml
from tests.cell_tests.common.simple_cell_mock import SimpleCellMock
from tests.cell_tests.common.fake_env import FakeEnv

def test_dendritic_cell_basic_flow():
    cfg = load_yaml_rel("cells/DendriticCell_v1.yaml")
    # construct a simple cell mock with meta defaults
    cell = SimpleCellMock(position=(5,5))
    cell.id = "dc_test_1"
    cell.meta.update(cfg.get("meta", {}))
    # ensure starting state
    assert getattr(cell, "maturation_state", None) in (None, "Immature", "immature")

    env = FakeEnv()
    events = []
    env.emit_event = lambda n,p: events.append((n,p))

    # phagocytose behavior should be instantiable and callable
    phago_cfg = load_yaml_rel("behaviors/phagocytose_v1.yaml")
    phago = instantiate_behavior_from_yaml("behaviors/phagocytose_v1.yaml", phago_cfg)
    # stub a field read: FakeEnv can be extended here if needed; for simple run, call directly
    actions_phago = phago.execute(cell, env, params=phago_cfg.get("params", {}))
    assert isinstance(actions_phago, (list, tuple))

    # process behavior
    proc_cfg = load_yaml_rel("behaviors/DC_process_and_load_MHC_v1.yaml")
    proc = instantiate_behavior_from_yaml("behaviors/DC_process_and_load_MHC_v1.yaml", proc_cfg)
    # ensure captured_antigens exists for processing
    cell.captured_antigens = [{"id":"ag1","sequence":"A"*12}]
    actions_proc = proc.execute(cell, env, params=proc_cfg.get("params", {}))
    # expects event pMHC_presented OR action describing presentation
    assert any(e[0] == "pMHC_presented" for e in events) or any(a.get("name") == "pMHC_presented" for a in (actions_proc or []))

    # DC upregulate costim
    up_cfg = load_yaml_rel("behaviors/DC_upregulate_costim.yaml")
    up = instantiate_behavior_from_yaml("behaviors/DC_upregulate_costim.yaml", up_cfg)
    actions_up = up.execute(cell, env, params=up_cfg.get("params", {}))
    # co_stim should have increased or maturation_state changed
    assert hasattr(cell, "co_stim")
    # may become mature according to threshold -- assert co_stim is numeric
    assert isinstance(getattr(cell, "co_stim", 0.0), (int, float))

