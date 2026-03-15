"""
behavior_factory - helper used by unit tests to instantiate behavior functions/classes
from YAML "implementation" hints or legacy module mapping.

Provides:
 - instantiate_behavior_from_yaml(rel_path, yaml_cfg)
 - FunctionBehaviorAdapter(func, params=None)  # wraps plain functions into behavior-like object

This file is intentionally small and self-contained for tests.
"""
from __future__ import annotations
import importlib
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Dict, Optional

class FunctionBehaviorAdapter:
    """
    Adapter that wraps a plain function (fn) into a behavior-like object that exposes
    .execute(cell, env, params=None, payload=None, rng=None, receptors=None, **kw).
    The adapter will try several calling conventions to maximize compatibility.
    """
    def __init__(self, fn: Callable, params: Optional[Dict[str, Any]] = None):
        self.func = fn
        self.params = params or {}

    def execute(self, cell=None, env=None, params=None, payload=None, rng=None, receptors=None, **kw):
        # merge params: adapter params <- call-time params
        p = {}
        p.update(self.params or {})
        if isinstance(params, dict):
            p.update(params)

        # Build call_kw once and avoid duplicate keys.
        # Start from copy of kw, then set payload/rng/receptors only if not present.
        call_kw = dict(kw or {})
        if payload is not None and 'payload' not in call_kw:
            call_kw['payload'] = payload
        if rng is not None and 'rng' not in call_kw:
            call_kw['rng'] = rng
        if receptors is not None and 'receptors' not in call_kw:
            call_kw['receptors'] = receptors

        fn = self.func

        # Try plausible calling conventions in order (explicit -> positional -> fallback)
        tries = [
            # 1) explicit cell, env, params and kw (for functions expecting params as positional first arg)
            ("cell_env_params_with_kw", (cell, env, p), dict(call_kw)),
            # 2) named-args style: pass everything as keywords (but don't duplicate keys)
            ("named_keywords", (), self._build_named_keywords(cell, env, p, call_kw)),
            # 3) positional: cell, env, params, payload
            ("pos_params_payload", (cell, env, p, call_kw.get('payload')), dict()),
            # 4) positional: cell, env, params
            ("pos_params", (cell, env, p), dict()),
            # 5) minimal positional + call_kw
            ("pos_min_with_kw", (cell, env), dict(call_kw)),
            # 6) only keyword passthrough (cell/env plus whatever in call_kw)
            ("kw_only", (), dict({"cell": cell, "env": env, **call_kw})),
        ]

        last_exc = None
        for name, pos_args, kw_args in tries:
            try:
                # ensure pos_args is a tuple (some entries may be None)
                if not isinstance(pos_args, tuple):
                    pos_args = tuple(pos_args) if pos_args is not None else tuple()
                return fn(*pos_args, **(kw_args or {}))
            except TypeError as te:
                # signature mismatch: remember and try next
                last_exc = te
                continue
            except Exception as e:
                # Real runtime error - re-raise (we don't swallow non-TypeError exceptions silently).
                raise

        # If we exhausted tries, raise the last TypeError with context
        if last_exc is not None:
            raise RuntimeError(f"Failed to call behavior function {fn!r}. Last error: {last_exc}") from last_exc
        return []

    def _build_named_keywords(self, cell, env, params_dict, call_kw):
        """
        Build named keywords dict for calling fn with explicit keyword names.
        Avoid duplicating keys between call_kw and explicit fields.
        """
        base = {}
        # Add canonical named args; do not overwrite keys existing in call_kw
        if 'cell' not in call_kw:
            base['cell'] = cell
        if 'env' not in call_kw:
            base['env'] = env
        if 'params' not in call_kw:
            base['params'] = params_dict
        # merge call_kw (call_kw takes precedence for payload/rng/receptors etc)
        merged = {}
        merged.update(base)
        merged.update(call_kw or {})
        return merged

def _import_module(mod_name: str) -> ModuleType:
    """
    Import a module by name. Raises ImportError with original message.
    """
    try:
        return importlib.import_module(mod_name)
    except Exception:
        # Re-raise so caller gets ImportError/ModuleNotFoundError as before.
        raise

def instantiate_behavior_from_yaml(rel_path: str, yaml_cfg: Any):
    """
    Instantiate a behavior object given a repo-relative yaml path and its parsed cfg.
    Expects yaml_cfg to be a dict possibly containing 'implementation' block like:
      implementation:
        module: "behaviors_impl.phagocytose"
        function: "phagocytose_v1"
        class: "PhagocytoseBehavior"   # optional alternative
    Returns an object with execute/act/run methods (or raises on import errors).
    """
    impl = None
    if isinstance(yaml_cfg, dict):
        impl = yaml_cfg.get("implementation") or yaml_cfg.get("impl")

    def _instantiate_from_module_class(module_name, class_name=None, func_name=None, params=None):
        mod = _import_module(module_name)
        # prefer class if requested
        if class_name:
            cls = getattr(mod, class_name, None)
            if cls is None:
                raise RuntimeError(f"Class {class_name} not found in {module_name}")
            try:
                return cls(**(params or {}))
            except TypeError:
                return cls()
        # prefer function if requested
        if func_name:
            func = getattr(mod, func_name, None)
            if func is None:
                raise RuntimeError(f"Function {func_name} not found in {module_name}")
            return FunctionBehaviorAdapter(func, params=params)
        # otherwise try known names
        if hasattr(mod, "Behavior"):
            cls = getattr(mod, "Behavior")
            try:
                return cls(**(params or {}))
            except TypeError:
                return cls()
        # fallback: search first class that endswith Behavior
        for obj in mod.__dict__.values():
            if isinstance(obj, type) and obj.__name__.endswith("Behavior"):
                try:
                    return obj(**(params or {}))
                except TypeError:
                    return obj()
        # fallback: if module itself is a callable (function), wrap it
        if callable(mod):
            return FunctionBehaviorAdapter(mod, params=params)
        raise RuntimeError(f"No suitable behavior found in module {module_name}")

    # 1) If implementation block provides module+function/class -> use it
    if impl and isinstance(impl, dict):
        module_name = impl.get("module")
        func_name = impl.get("function")
        class_name = impl.get("class")
        params = (yaml_cfg.get("params") if isinstance(yaml_cfg, dict) else None) or {}
        if module_name:
            return _instantiate_from_module_class(module_name, class_name=class_name, func_name=func_name, params=params)

    # 2) Fallback: try legacy mapping: behaviors.<stem>
    stem = Path(rel_path).stem
    legacy_module = f"behaviors.{stem}"
    try:
        return _instantiate_from_module_class(legacy_module, params=(yaml_cfg.get("params") if isinstance(yaml_cfg, dict) else {}))
    except Exception as e:
        raise RuntimeError(f"Failed to instantiate behavior for {rel_path}. Looked for implementation block and legacy module {legacy_module}. Original error: {e}")

