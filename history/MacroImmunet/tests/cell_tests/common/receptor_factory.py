# tests/cell_tests/common/receptor_factory.py
import importlib
from pathlib import Path

def receptor_class_from_relpath(rel_path: str):
    stem = Path(rel_path).stem
    module_name = f"receptors.{stem}"
    mod = importlib.import_module(module_name)
    if hasattr(mod, "Receptor"):
        return getattr(mod, "Receptor")
    for obj in mod.__dict__.values():
        if isinstance(obj, type) and obj.__name__.endswith("Receptor"):
            return obj
    raise RuntimeError(f"No Receptor class found in {module_name}")

def instantiate_receptor_from_yaml(rel_path, yaml_cfg):
    cls = receptor_class_from_relpath(rel_path)
    params = yaml_cfg.get("params", {}) if isinstance(yaml_cfg, dict) else {}
    try:
        return cls(**params)
    except TypeError:
        return cls()

