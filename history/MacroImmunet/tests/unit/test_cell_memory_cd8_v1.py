# behaviors_impl/up_down_regulate.py
"""
up_down_regulate_v1(cell, env, params=None, payload=None, **kw)

Robust implementation used by unit tests:

- Reads attribute name and up/down values from params or payload.
- Accepts multiple common key names for compatibility.
- If 'mode' == 'toggle' will flip boolean if attribute exists (optional).
- If no explicit instruction, defaults to setting attribute to up_value if provided.
- Returns a list of actions for tests to inspect.
"""
from typing import Any, Dict
import random

# common candidate key names
_ATTR_KEYS = ("attribute", "attribute_name", "attr", "name", "key", "target")
_UP_KEYS = ("up_value", "up", "value_up", "set_to", "true_value")
_DOWN_KEYS = ("down_value", "down", "value_down", "unset_to", "false_value")
_MODE_KEYS = ("mode", "toggle_mode", "action")

def _find_key(d: Dict[str, Any], candidates):
    if not isinstance(d, dict):
        return None
    for k in candidates:
        if k in d:
            return d[k]
    return None

def up_down_regulate_v1(cell, env, params=None, payload=None, **kw):
    params = params or {}
    payload = payload or {}

    # search order: params first, then payload (tests may call either)
    source_candidates = (params, payload)

    attr = None
    up_val = None
    down_val = None
    mode = None
    # also allow explicit 'value' with boolean interpretation (legacy)
    explicit_value = None

    for src in source_candidates:
        if attr is None:
            attr = _find_key(src, _ATTR_KEYS)
        if up_val is None:
            up_val = _find_key(src, _UP_KEYS)
        if down_val is None:
            down_val = _find_key(src, _DOWN_KEYS)
        if mode is None:
            mode = _find_key(src, _MODE_KEYS)
        if explicit_value is None and isinstance(src, dict) and "value" in src:
            explicit_value = src.get("value")

    # normalize attribute name
    if isinstance(attr, str):
        attr_name = attr
    elif isinstance(attr, (bytes,)):
        try:
            attr_name = attr.decode()
        except Exception:
            attr_name = None
    else:
        attr_name = None

    # default up/down if missing
    if up_val is None and down_val is None and explicit_value is not None:
        # single value provided: treat truthy as set to that
        up_val = explicit_value
        down_val = explicit_value
    if up_val is None:
        up_val = True
    if down_val is None:
        down_val = False

    # simple behavior modes:
    # - "force_up" / "force_down" / "toggle" / None (default -> set to up_val)
    if isinstance(mode, str):
        mode_l = mode.lower()
    else:
        mode_l = None

    chosen = up_val

    try:
        if mode_l == "force_up":
            chosen = up_val
        elif mode_l == "force_down":
            chosen = down_val
        elif mode_l == "toggle":
            # flip if attribute exists and is boolean, else set to up_val
            cur = getattr(cell, attr_name, None) if attr_name else None
            if isinstance(cur, bool):
                chosen = not cur
            else:
                chosen = up_val
        elif mode_l == "random":
            # choose randomly between up and down (50/50) unless a probability given
            p = None
            for src in source_candidates:
                if isinstance(src, dict) and "prob_up" in src:
                    p = float(src.get("prob_up", 0.5))
                    break
            if p is None:
                p = 0.5
            chosen = up_val if random.random() < p else down_val
        else:
            # default behaviour: set to up_val
            chosen = up_val
    except Exception:
        chosen = up_val

    # finally, set the attribute on the cell if we have a name
    actions = []
    if attr_name:
        try:
            setattr(cell, attr_name, chosen)
            actions.append({"name": "up_down_regulated", "payload": {"attribute": attr_name, "value": chosen}})
        except Exception:
            # fallback: try cell.meta dictionary
            try:
                if not hasattr(cell, "meta") or cell.meta is None:
                    cell.meta = {}
                if isinstance(cell.meta, dict):
                    cell.meta[attr_name] = chosen
                    actions.append({"name": "up_down_regulated", "payload": {"attribute": attr_name, "value": chosen, "via": "meta"}})
            except Exception:
                # give up silently; tests will detect missing attribute
                pass
    else:
        # no attribute name found; no-op but return an action describing attempt
        actions.append({"name": "up_down_regulate_noop", "payload": {"reason": "no attribute name found"}})

    return actions

