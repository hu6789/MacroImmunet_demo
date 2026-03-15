# tests/conftest.py
import pytest
from tests.cell_tests.common.fake_env import FakeEnv
from tests.cell_tests.common.simple_cell_mock import SimpleCellMock
from tests.cell_tests.common.yaml_loader import load_yaml_rel

@pytest.fixture
def fake_env():
    env = FakeEnv(grid_size=(20,20))
    # create common minimal fields used in demo
    env.add_field("antigen_density")
    env.add_field("cell_debris")
    env.add_field("IL2")
    env.add_field("IFNg")
    return env

@pytest.fixture
def simple_cell():
    return SimpleCellMock()

@pytest.fixture
def load_cfg():
    def _load(p):
        return load_yaml_rel(p)
    return _load

@pytest.fixture
def default_seed():
    return 2025

