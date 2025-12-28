# cell_master/behaviour_library/__init__.py
"""
Minimal behaviour library package initializer.

- auto-loads .py modules in this package (except __init__)
- collects callable functions with conventional names (ending with _v1 or specific function names)
- exposes a small registry object with:
    - list() -> list of behaviour names
    - get(name) -> callable or None
    - sample_and_run(name, cell, env, params=None, payload=None, rng=None, receptors=None)
      -> calls the behaviour callable and normalizes result to list(actions)
"""

import pkgutil
import importlib
import inspect
from typing import Callable, Dict, List, Any, Optional

# map behaviour_name -> callable
_BEHAVIORS: Dict[str, Callable] = {}

def _is_behavior_fn(name: str, obj: Any) -> bool:
    # Accept functions with conventional names:
    # - endswith _v1 (e.g. secrete_v1) OR
    # - a few known canonical function names
    if not inspect.isfunction(obj):
        return False
    if name.endswith("_v1"):
        return True
    if name in ("replicate_intracellular", "handle_release_on_death", "phagocytose_v1", "present_v1"):
        return True
    return False

def _load_package_behaviours():
    # import all submodules in this package and collect functions
    for finder, modname, ispkg in pkgutil.iter_modules(__path__):
        if modname.startswith("__"):
            continue
        full = f"{__name__}.{modname}"
        try:
            m = importlib.import_module(full)
        except Exception:
            # skip modules that fail to import to keep demo robust
            continue
        for nm, obj in inspect.getmembers(m, inspect.isfunction):
            if _is_behavior_fn(nm, obj):
                key = nm
                _BEHAVIORS[key] = obj

# run loader on import
_load_package_behaviours()

# Registry minimal API
class Registry:
    def list(self) -> List[str]:
        return sorted(list(_BEHAVIORS.keys()))

    def get(self, name: str) -> Optional[Callable]:
        return _BEHAVIORS.get(name)

    def sample_and_run(self, name: str, cell, env, params=None, payload=None, rng=None, receptors=None):
        fn = self.get(name)
        if fn is None:
            raise KeyError(f"behavior {name} not found")
        try:
            out = fn(cell, env, params=params or {}, payload=payload or {}, rng=rng, receptors=receptors)
            if out is None:
                return []
            if isinstance(out, list):
                return out
            if isinstance(out, dict):
                return [out]
            # fallback: try to coerce iterables
            try:
                return list(out)
            except Exception:
                return [out]
        except TypeError:
            # try fewer args
            try:
                out = fn(cell, env, params or {}, payload or {})
                if out is None:
                    return []
                if isinstance(out, list):
                    return out
                if isinstance(out, dict):
                    return [out]
                try:
                    return list(out)
                except Exception:
                    return [out]
            except Exception:
                return []
        except Exception:
            return []

# single registry instance
registry = Registry()

# convenience helpers at module level
def list_behaviors():
    return registry.list()

def get_behavior(name: str):
    return registry.get(name)

def sample_and_run(name: str, cell, env, params=None, payload=None, rng=None, receptors=None):
    return registry.sample_and_run(name, cell, env, params=params, payload=payload, rng=rng, receptors=receptors)

__all__ = ["registry", "list_behaviors", "get_behavior", "sample_and_run"]

