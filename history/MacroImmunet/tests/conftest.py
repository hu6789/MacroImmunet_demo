# tests/conftest.py -- robust fixtures for pytest
# This file ensures the project root is on sys.path so imports like
# `from tests.cell_tests.common.fake_env import FakeEnv` work consistently
# whether pytest treats tests/ as a package or not.

import sys
from pathlib import Path
import pytest

# Insert repo root into sys.path (safe, non-destructive)
# __file__ is tests/conftest.py -> repo root is parents[1]
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Now normal imports should work regardless of pytest import context
try:
    from tests.cell_tests.common.fake_env import FakeEnv
    from tests.cell_tests.common.simple_cell_mock import SimpleCellMock
    from tests.cell_tests.common.yaml_loader import load_yaml_rel
except Exception as e:
    # As a defensive fallback, try one more import style and re-raise if fails
    try:
        # fallback to direct path import if package name resolution still fails
        import importlib.util, importlib.machinery
        # attempt to import modules by path (best-effort)
        base = REPO_ROOT / "tests" / "cell_tests" / "common"
        spec = importlib.util.spec_from_file_location("fake_env_mod", str(base / "fake_env.py"))
        fake_env_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fake_env_mod)
        FakeEnv = getattr(fake_env_mod, "FakeEnv")
        spec = importlib.util.spec_from_file_location("simple_cell_mock_mod", str(base / "simple_cell_mock.py"))
        scm = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(scm)
        SimpleCellMock = getattr(scm, "SimpleCellMock")
        spec = importlib.util.spec_from_file_location("yaml_loader_mod", str(base / "yaml_loader.py"))
        ylm = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ylm)
        load_yaml_rel = getattr(ylm, "load_yaml_rel")
    except Exception:
        raise e  # let pytest show the original import error for debugging

@pytest.fixture
def fake_env():
    env = FakeEnv(grid_size=(20,20))
    # try to add common minimal fields if API supports it
    try:
        env.add_field("antigen_density")
        env.add_field("cell_debris")
        env.add_field("IL2")
        env.add_field("IFNg")
    except Exception:
        pass
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
