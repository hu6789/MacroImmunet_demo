# scan_master/utils.py
"""
Utility helpers used across scan_master.
Provides: mk_label, normalize_label_input, deprecation_warn
"""

import warnings
import time
from typing import Dict, Any, Optional

def deprecation_warn(msg: str):
    # use warnings so pytest can capture it if configured
    warnings.warn(msg, DeprecationWarning)

def mk_label(name: str, coord: Optional[tuple] = None, mass: float = 1.0, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Create a label dict with common fields used by tests/masters.
    """
    meta = dict(meta or {})
    return {
        "id": None,
        "name": name,
        "type": name,
        "coord": coord,
        "mass": float(mass),
        "meta": meta,
        "created_tick": int(time.time())
    }

def normalize_label_input(label: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Ensure a label-like dict has minimal keys: name, type, coord, mass, meta.
    Accepts string (treated as name) or dict.
    """
    if label is None:
        return {}
    if isinstance(label, str):
        return mk_label(label)
    if not isinstance(label, dict):
        # fallback: stringify
        return mk_label(str(label))
    # copy and ensure fields
    l = dict(label)
    if "name" not in l and "type" in l:
        l["name"] = l.get("type")
    if "type" not in l and "name" in l:
        l["type"] = l.get("name")
    l.setdefault("coord", l.get("meta", {}).get("coord"))
    l.setdefault("mass", float(l.get("mass", 1.0)))
    l.setdefault("meta", l.get("meta", {}))
    l.setdefault("created_tick", l.get("created_tick", 0))
    return l

