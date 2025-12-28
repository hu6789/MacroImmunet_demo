# cell_master/intents.py
from typing import Any, Dict, Optional
import time
import uuid
import json

def _safe_jsonify(value):
    """
    Try to JSON-serialize value; if fails, fall back to str(value).
    Keep None as None.
    """
    if value is None:
        return None
    try:
        # small optimization: simple types pass through
        if isinstance(value, (str, int, float, bool, list, dict)):
            json.dumps(value)  # validate
            return value
    except Exception:
        pass
    try:
        return json.loads(json.dumps(value))
    except Exception:
        try:
            return str(value)
        except Exception:
            return None

class Intent:
    def __init__(
        self,
        name: str,
        payload: Optional[Dict[str, Any]] = None,
        coord: Optional[tuple] = None,
        src_cell_id: Optional[str] = None,
        src_cell_type: Optional[str] = None,
        src_genotype: Optional[Dict[str,Any]] = None,
        priority: int = 0,
        lifetime: Optional[float] = None,
        flags: Optional[Dict[str, Any]] = None,
        intent_id: Optional[str] = None,
        created_ts: Optional[float] = None,
        **extra_kwargs,
    ):
        # canonical fields
        self.intent_id = intent_id or uuid.uuid4().hex[:8]
        self.name = str(name)
        self.payload = dict(payload or {})
        self.coord = coord
        self.src_cell_id = src_cell_id
        self.src_cell_type = src_cell_type
        self.src_genotype = dict(src_genotype) if isinstance(src_genotype, dict) else src_genotype
        self.priority = int(priority or 0)
        self.lifetime = lifetime
        self.flags = dict(flags or {})
        self.created_ts = float(created_ts or time.time())

        # stash additional kwargs both as attributes and inside flags (non-destructive)
        for k, v in (extra_kwargs or {}).items():
            try:
                setattr(self, k, v)
            except Exception:
                # if can't set attribute, put into flags
                try:
                    self.flags[k] = v
                except Exception:
                    pass
            else:
                if k not in self.flags:
                    try:
                        self.flags[k] = v
                    except Exception:
                        pass

    def to_dict(self) -> Dict[str, Any]:
        """
        Return a safe JSON-serializable dict with *all* useful intent fields.
        Include both 'intent_id' and 'id' for compatibility with tests.
        """
        # start with explicit canonical keys (keeps stable order)
        out = {
            "intent_id": self.intent_id,
            "id": self.intent_id,
            "name": self.name,
            "payload": _safe_jsonify(self.payload),
            "coord": _safe_jsonify(self.coord),
            "src_cell_id": self.src_cell_id,
            "src_cell_type": self.src_cell_type,
            "src_genotype": _safe_jsonify(self.src_genotype),
            "priority": self.priority,
            "lifetime": self.lifetime,
            "flags": _safe_jsonify(self.flags),
            "created_ts": self.created_ts,
        }

        # add any other attributes found on the instance that tests might expect
        # but avoid overriding keys we already set
        for k, v in vars(self).items():
            if k in out:
                continue
            out[k] = _safe_jsonify(v)

        return out

    def __repr__(self):
        src = f"{self.src_cell_type or ''}/{self.src_cell_id or ''}"
        coord = f"{self.coord}" if self.coord is not None else "None"
        return f"Intent({self.name}, coord={coord}, src={src}, id={self.intent_id})"

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

# ---- convenience intent factories used by masters/tests ----
def Intent_perforin_release(source: Optional[tuple] = None, target: Optional[tuple] = None, amount: float = 1.0, **kw):
    payload = {"field": "perforin", "coord": target, "amount": amount, "source": source, "target": target}
    return Intent(name="perforin_release", payload=payload, coord=source, src_cell_id=kw.get("src_cell_id"), src_cell_type=kw.get("src_cell_type"), src_genotype=kw.get("src_genotype"))

def Intent_granzyme_release(source: Optional[tuple] = None, target: Optional[tuple] = None, amount: float = 1.0, **kw):
    payload = {"field": "granzyme", "coord": target, "amount": amount, "source": source, "target": target}
    return Intent(name="granzyme_release", payload=payload, coord=source, src_cell_id=kw.get("src_cell_id"), src_cell_type=kw.get("src_cell_type"), src_genotype=kw.get("src_genotype"))

def Intent_fasl_trigger(source: Optional[tuple] = None, target: Optional[tuple] = None, **kw):
    payload = {"action": "fasl_trigger", "source": source, "target": target}
    return Intent(name="fasl_trigger", payload=payload, coord=source, src_cell_id=kw.get("src_cell_id"), src_cell_type=kw.get("src_cell_type"), src_genotype=kw.get("src_genotype"))

def Intent_trigger_apoptosis(source: Optional[tuple] = None, target: Optional[tuple] = None, reason: Optional[str] = None, **kw):
    payload = {"action": "trigger_apoptosis", "source": source, "target": target, "reason": reason}
    return Intent(name="trigger_apoptosis", payload=payload, coord=target, src_cell_id=kw.get("src_cell_id"), src_cell_type=kw.get("src_cell_type"), src_genotype=kw.get("src_genotype"))

def Intent_move_to(coord: Optional[tuple] = None, target: Optional[tuple] = None, reason: Optional[str] = None, **kw):
    payload = {"action": "move_to", "target": target, "reason": reason}
    return Intent(name="move_to", payload=payload, coord=coord, src_cell_id=kw.get("src_cell_id"), src_cell_type=kw.get("src_cell_type"), src_genotype=kw.get("src_genotype"))

def Intent_random_move(coord: Optional[tuple] = None, step_size: float = 1.0, **kw):
    payload = {"action": "random_move", "step_size": step_size}
    return Intent(name="random_move", payload=payload, coord=coord, src_cell_id=kw.get("src_cell_id"), src_cell_type=kw.get("src_cell_type"), src_genotype=kw.get("src_genotype"))

__all__ = [
    "Intent",
    "Intent_perforin_release",
    "Intent_granzyme_release",
    "Intent_fasl_trigger",
    "Intent_trigger_apoptosis",
    "Intent_move_to",
    "Intent_random_move",
]
# --- Convenience typed Intent subclasses for tests / callers ---
# Append this to the end of cell_master/intents.py (after the Intent class definition).

class Intent_move_to(Intent):
    def __init__(self, coord=None, target=None, src_cell_id=None, payload=None, **kwargs):
        # payload keeps the target coordinate/label; preserve user payload if given
        p = dict(payload or {})
        p.setdefault("target", target)
        super().__init__(name="move_to", payload=p, coord=coord, src_cell_id=src_cell_id, **kwargs)


class Intent_random_move(Intent):
    def __init__(self, coord=None, src_cell_id=None, payload=None, **kwargs):
        p = dict(payload or {})
        super().__init__(name="random_move", payload=p, coord=coord, src_cell_id=src_cell_id, **kwargs)


class Intent_perforin_release(Intent):
    def __init__(self, source=None, target=None, amount: float = 1.0, payload=None, **kwargs):
        p = dict(payload or {})
        p.setdefault("source", source)
        p.setdefault("target", target)
        p.setdefault("amount", amount)
        # coord field use source for spatial context if provided
        super().__init__(name="perforin_release", payload=p, coord=source, **kwargs)


class Intent_granzyme_release(Intent):
    def __init__(self, source=None, target=None, amount: float = 1.0, payload=None, **kwargs):
        p = dict(payload or {})
        p.setdefault("source", source)
        p.setdefault("target", target)
        p.setdefault("amount", amount)
        super().__init__(name="granzyme_release", payload=p, coord=source, **kwargs)


class Intent_fasl_trigger(Intent):
    def __init__(self, source=None, target=None, payload=None, **kwargs):
        p = dict(payload or {})
        p.setdefault("source", source)
        p.setdefault("target", target)
        super().__init__(name="fasl_trigger", payload=p, coord=source, **kwargs)


class Intent_trigger_apoptosis(Intent):
    def __init__(self, source=None, target=None, reason: str = None, payload=None, **kwargs):
        p = dict(payload or {})
        p.setdefault("source", source)
        p.setdefault("target", target)
        if reason is not None:
            p.setdefault("reason", reason)
        super().__init__(name="trigger_apoptosis", payload=p, coord=target or source, **kwargs)

