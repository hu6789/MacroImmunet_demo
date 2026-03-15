# tests/cell_tests/common/yaml_loader.py
from pathlib import Path
import yaml

# Resolve project root from this file: tests/cell_tests/common/... -> repo root = parents[3]
REPO_ROOT = Path(__file__).resolve().parents[3]

def load_yaml_rel(rel_path: str):
    """
    Load YAML by repo-relative path, e.g. "behaviors/proliferate_v1.yaml".
    Returns parsed dict.
    """
    p = REPO_ROOT.joinpath(rel_path)
    if not p.exists():
        raise FileNotFoundError(f"YAML not found: {p}")
    text = p.read_text(encoding="utf-8")
    return yaml.safe_load(text)
