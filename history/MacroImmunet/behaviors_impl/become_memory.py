"""
behaviors_impl.become_memory
Implementation for become_memory_v1

Exports:
 - become_memory_v1(cell, env, params=None, payload=None, rng=None, **kw)
 - BecomeMemoryBehavior class with execute(...)
 - become_memory(...) helper
"""
from typing import Any, Dict, Optional

def _resolve_payload(params: Optional[Dict[str, Any]], payload: Optional[Dict[str, Any]], cell: Any, kw: Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(payload, dict) and payload:
        return payload
    if isinstance(params, dict) and isinstance(params.get("payload"), dict):
        return params.get("payload")
    if isinstance(kw, dict) and isinstance(kw.get("payload"), dict):
        return kw.get("payload")
    p = getattr(cell, "payload", None)
    if isinstance(p, dict):
        return p
    meta = getattr(cell, "meta", None) or {}
    if isinstance(meta, dict) and isinstance(meta.get("payload"), dict):
        return meta.get("payload")
    return {}

def _emit(env, event_name: str, payload: Dict[str, Any]):
    try:
        if hasattr(env, "emit_event"):
            env.emit_event(event_name, payload)
            return
    except Exception:
        pass
    try:
        if hasattr(env, "emit_intent"):
            env.emit_intent(event_name, payload)
            return
    except Exception:
        pass
    # best-effort log if exists
    try:
        if hasattr(env, "log_event"):
            env.log_event(event_name, payload)
    except Exception:
        pass

def become_memory_v1(cell, env, params=None, payload=None, rng=None, **kw):
    """
    Finalize memory transition.
    Returns list of actions (for tests/adapter compatibility).
    """
    params = params or {}
    pld = _resolve_payload(params, payload, cell, kw) or {}

    # determine memory_type: payload override if allowed and valid
    allowed_override = params.get("allow_payload_override", True)
    memory_type = params.get("memory_type", "early")
    if allowed_override and isinstance(pld.get("memory_type"), str):
        memory_type = pld.get("memory_type")
    if not isinstance(memory_type, str):
        memory_type = str(memory_type or "early")
    memory_type = memory_type.lower()
    if memory_type not in ("early", "late"):
        # fallback safe
        memory_type = "early"

    # derive a deterministic state name using cell type/lineage if present
    # try several heuristics; keep it simple and transparent
    lineage = None
    try:
        lineage = getattr(cell, "cell_type", None) or getattr(cell, "type", None)
    except Exception:
        lineage = None
    if not lineage:
        meta = getattr(cell, "meta", None) or {}
        lineage = meta.get("lineage") or meta.get("cell_type") or None

    if isinstance(lineage, str) and lineage:
        # normalize: replace spaces/slashes with underscore
        normalized = lineage.replace(" ", "_").replace("/", "_")
        new_state = f"Memory_{normalized}_{memory_type.capitalize()}"
    else:
        # fallback: use generic naming
        new_state = f"Memory_{memory_type.capitalize()}"

    prev_state = getattr(cell, "state", None)
    # perform the update atomically as possible (best-effort)
    try:
        cell.state = new_state
    except Exception:
        # if cannot set, bail out gracefully
        return []

    # optionally adjust numeric fields safely
    try:
        if not hasattr(cell, "survival_score"):
            cell.survival_score = float(getattr(cell, "survival_score", 1.0) or 1.0)
        else:
            try:
                cell.survival_score = float(cell.survival_score)
            except Exception:
                cell.survival_score = 1.0
    except Exception:
        pass

    try:
        if not hasattr(cell, "proliferation_potential"):
            cell.proliferation_potential = float(getattr(cell, "proliferation_potential", 0.0) or 0.0)
        else:
            try:
                cell.proliferation_potential = float(cell.proliferation_potential)
            except Exception:
                cell.proliferation_potential = 0.0
    except Exception:
        pass

    # log lineage if available
    log_payload = {
        "memory_type": memory_type,
        "cell_id": getattr(cell, "id", None),
        "clone_id": getattr(cell, "clone_id", None),
        "prev_state": prev_state,
        "new_state": new_state,
    }
    try:
        if hasattr(env, "log_lineage"):
            # defensive: ensure not to raise
            try:
                env.log_lineage(log_payload)
            except Exception:
                # try alternate signature
                try:
                    env.log_lineage(getattr(cell, "id", None), log_payload)
                except Exception:
                    pass
    except Exception:
        pass

    # emit became_memory event (engine consumers may look for this)
    _emit(env, "became_memory", {"memory_type": memory_type, "cell_id": getattr(cell, "id", None), "clone_id": getattr(cell, "clone_id", None), "tick": getattr(env, "tick", None)})

    # return action list for compatibility
    return [{"name": "became_memory", "payload": {"memory_type": memory_type, "cell_id": getattr(cell, "id", None)}}]

class BecomeMemoryBehavior:
    def __init__(self, **kwargs):
        self.params = kwargs or {}

    def execute(self, cell, env, params=None, payload=None, rng=None, **kw):
        merged = {}
        merged.update(self.params or {})
        if isinstance(params, dict):
            merged.update(params)
        return become_memory_v1(cell, env, params=merged, payload=payload, rng=rng, **kw)

def become_memory(cell, env, params=None, payload=None, rng=None, **kw):
    return become_memory_v1(cell, env, params=params, payload=payload, rng=rng, **kw)
