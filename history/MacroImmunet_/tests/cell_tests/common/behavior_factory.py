# tests/cell_tests/common/behavior_factory.py
import importlib
from pathlib import Path

def behavior_class_from_relpath(rel_path: str):
    """
    Map 'behaviors/proliferate_v1.yaml' -> import module 'behaviors.proliferate_v1'
    and return a class exported as 'Behavior' or first class ending with 'Behavior'.
    """
    stem = Path(rel_path).stem
    module_name = f"behaviors.{stem}"
    mod = importlib.import_module(module_name)
    if hasattr(mod, "Behavior"):
        return getattr(mod, "Behavior")
    for obj in mod.__dict__.values():
        if isinstance(obj, type) and obj.__name__.endswith("Behavior"):
            return obj
    raise RuntimeError(f"No Behavior class found in {module_name}")

def instantiate_behavior_from_yaml(rel_path, yaml_cfg):
    cls = behavior_class_from_relpath(rel_path)
    params = yaml_cfg.get("params", {}) if isinstance(yaml_cfg, dict) else {}
    # try to pass params dict if supported, else attempt no-arg init
    try:
        return cls(**params)
    except TypeError:
        return cls()

