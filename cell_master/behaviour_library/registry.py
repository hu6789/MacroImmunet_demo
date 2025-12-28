# cell_master/behaviour_library/registry.py
"""
Simple registry/loader for behaviour implementations found under
cell_master.behaviour_library package.

Features:
 - auto-register functions matching naming convention *_v1 or functions exported manually
 - get(name) -> callable
 - list() -> list of names
 - sample(template_name, ...) -> apply deterministic RNG / wrapper (demo)
"""
import pkgutil
import importlib
import inspect
import random
from typing import Callable, Dict, Any, List, Optional

class BehaviourRegistry:
    def __init__(self):
        self._map: Dict[str, Callable] = {}

    def register(self, name: str, fn: Callable):
        self._map[str(name)] = fn

    def get(self, name: str) -> Optional[Callable]:
        return self._map.get(name)

    def list(self) -> List[str]:
        return sorted(list(self._map.keys()))

    def sample_and_run(self, name: str, cell, env, params=None, payload=None, rng=None, receptors=None):
        fn = self.get(name)
        if fn is None:
            raise KeyError(f"behavior {name} not found")
        rng = rng or random.Random()
        # many of your implementations accept params/payload/rng
        return fn(cell, env, params=params or {}, payload=payload or {}, rng=rng, receptors=receptors)

def load_builtin_behaviours(reg: BehaviourRegistry, pkg="cell_master.behaviour_library"):
    """
    auto-import modules in the package and register functions matching *_v1 names
    """
    try:
        pkg_mod = importlib.import_module(pkg)
    except Exception:
        return reg

    # iterate modules in the package
    prefix = pkg + "."
    for finder, modname, ispkg in pkgutil.iter_modules(pkg_mod.__path__, prefix):
        try:
            m = importlib.import_module(modname)
        except Exception:
            # ignore faulty modules in demo
            continue
        # register suitable callables
        for name, obj in inspect.getmembers(m, inspect.isfunction):
            if name.endswith("_v1") or name.endswith("_v1_func"):
                # normalize name: drop suffix or keep full? keep full to avoid collision
                reg.register(name, obj)
        # also register common-named functions (e.g. replicate_intracellular)
        for name, obj in inspect.getmembers(m, inspect.isfunction):
            # allow explicit registration for common names
            if name in ("replicate_intracellular","handle_release_on_death","phagocytose_v1","present_v1","secrete_v1","TCR_scan_v1"):
                reg.register(name, obj)
    return reg

