# scan_master/behavior_to_intent.py
"""
Translate behaviour-like objects (Intent objects, dicts, class instances)
into a normalized 'intent' dict format used by the demo & label writeback.

Normalized intent format:
{
  "type": "move_to" | "phagocytose" | "pMHC_presented" | "release_antigen" | ...,
  "payload": {...},
  "priority": float (0..1, default 0.5),
  "mode": "per-cell"|"batch",
  "src": "<master class name or id>",
}
"""
from typing import Any, Dict

DEFAULT_PRIORITY = 0.5

def normalize_action(a: Any, src: str = "unknown") -> Dict:
    """
    Accepts:
      - dicts: {"name":..., "payload":...}
      - Intent-like objects with .name/.payload attributes
      - class/instance with __class__.__name__
    Returns normalized dict.
    """
    out = {"type": None, "payload": {}, "priority": DEFAULT_PRIORITY, "mode": "per-cell", "src": src}
    try:
        if isinstance(a, dict):
            out["type"] = a.get("name") or a.get("action") or a.get("type") or str(a)
            out["payload"] = a.get("payload") or a.get("params") or {}
            out["priority"] = float(a.get("priority", DEFAULT_PRIORITY) or DEFAULT_PRIORITY)
            out["mode"] = a.get("mode", "per-cell")
            return out
    except Exception:
        pass

    # Intent-like object
    try:
        nm = getattr(a, "name", None) or getattr(a, "__class__", None).__name__
        pl = getattr(a, "payload", None) or getattr(a, "params", None) or {}
        pr = getattr(a, "priority", None)
        md = getattr(a, "mode", None)
        out["type"] = str(nm)
        out["payload"] = dict(pl) if isinstance(pl, dict) else {}
        if pr is not None:
            try:
                out["priority"] = float(pr)
            except Exception:
                pass
        if md:
            out["mode"] = md
        out["src"] = src
        return out
    except Exception:
        pass

    # fallback: stringified
    try:
        out["type"] = str(a)
        return out
    except Exception:
        out["type"] = "<unknown>"
        return out

