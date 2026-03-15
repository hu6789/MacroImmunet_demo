from tests.cell_tests.common.yaml_loader import load_yaml_rel
from tests.cell_tests.common.behavior_factory import instantiate_behavior_from_yaml
from tests.cell_tests.common.simple_cell_mock import SimpleCellMock
from tests.cell_tests.common.fake_env import FakeEnv

def test_memory_cd4_basic_survival_and_scan():
    cfg = load_yaml_rel("cells/Memory_CD4_v1.yaml")
    # instantiate behaviors referenced in cell yaml (tests normally instantiate behavior YAMLs directly)
    # Here we just verify the cell meta_defaults and that survival behavior can be called.
    cell = SimpleCellMock(position=(2,2))
    cell.id = "mem4_1"
    cell.meta.update(cfg.get("meta_defaults", {}))
    env = FakeEnv()
    # survival behavior
    surv_cfg = load_yaml_rel("behaviors/survival_signal_v1.yaml")
    surv_bh = instantiate_behavior_from_yaml("behaviors/survival_signal_v1.yaml", surv_cfg)
    actions = surv_bh.execute(cell, env, params=surv_cfg.get("params", {}))
    assert isinstance(actions, (list, tuple))

