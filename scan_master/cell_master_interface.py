# scan_master/cell_master_interface.py
"""
CellMasterAdapter — thin adapter that normalizes various cell-master implementations
to the API expected by scan_master.node_dispatcher tests.

It exposes `CellMasterAdapter` at module top-level (tests import it directly).
The adapter:
 - prefers `execute_node(node, current_tick=...)` on the underlying object,
 - falls back to `handle_node` / `process_node` if present,
 - accepts a plain callable (callable(node, current_tick=...)),
 - returns a normalized dict:
     {
       "node_id": str,
       "node_type": str,
       "outcome": {"status": "ok" or "failed", ...},
       "emitted_labels": [ {...}, ... ],
       "intents": [ {...}, ... ]
     }
 - ensures emitted labels / intents get provenance meta appended.
"""

from typing import Any, Dict, List, Optional
import traceback
import logging
import uuid

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


def _ensure_list(x):
    if x is None:
        return []
    if isinstance(x, list):
        return x
    return [x]


class CellMasterAdapter:
    """
    Adapter that normalizes different CellMaster implementations to a single
    execute_node(node, current_tick:int) -> dict API expected by node_dispatcher.
    Accepts:
      - concrete cell master instances that implement `execute_node(node, current_tick=...)`
      - or objects that implement `handle_node` / `process_node` / callable(node,current_tick)
    """

    def __init__(self, cm_obj: Any):
        self.cm = cm_obj

    def _wrap_error(self, node_id: Optional[str], node_type: Optional[str], exc: Exception) -> Dict:
        tb = traceback.format_exc()
        logger.exception("CellMasterAdapter: exception executing node %s: %s", node_id, exc)
        return {
            "node_id": node_id or f"node_err_{uuid.uuid4().hex[:6]}",
            "node_type": node_type or "unknown",
            "outcome": {"status": "failed", "error": str(exc), "traceback": tb},
            "emitted_labels": [],
            "intents": []
        }

    def _normalize(self, node: Dict, raw: Any) -> Dict:
        """
        Normalize raw result (None, dict, tuple/list, Exception) into standard dict.
        """
        node_id = node.get("node_id") or f"{node.get('node_type','node')}_{uuid.uuid4().hex[:8]}"
        node_type = node.get("node_type", "unknown")

        if raw is None:
            return self._wrap_error(node_id, node_type, Exception("none_response"))

        if isinstance(raw, Exception):
            return self._wrap_error(node_id, node_type, raw)

        # tuple/list heuristic: (outcome_dict?, emitted?, intents?)
        if isinstance(raw, (list, tuple)):
            try:
                outcome = {"status": "ok"}
                emitted = []
                intents = []
                if len(raw) >= 1:
                    # if first element is dict-like and contains status -> treat as outcome
                    if isinstance(raw[0], dict) and "status" in raw[0]:
                        outcome = raw[0]
                        if len(raw) >= 2:
                            emitted = raw[1]
                        if len(raw) >= 3:
                            intents = raw[2]
                    else:
                        # otherwise assume (emitted, intents) or (emitted,)
                        emitted = raw[0]
                        if len(raw) >= 2:
                            intents = raw[1]
                return {
                    "node_id": node_id,
                    "node_type": node_type,
                    "outcome": outcome,
                    "emitted_labels": _ensure_list(emitted),
                    "intents": _ensure_list(intents),
                }
            except Exception as e:
                return self._wrap_error(node_id, node_type, e)

        if not isinstance(raw, dict):
            return {
                "node_id": node_id,
                "node_type": node_type,
                "outcome": {"status": "failed", "error": f"unexpected_response_type:{type(raw)}"},
                "emitted_labels": [],
                "intents": []
            }

        # raw is dict: pick canonical keys with fallbacks
        out_node_id = raw.get("node_id", node_id)
        out_node_type = raw.get("node_type", node_type)
        outcome = raw.get("outcome", {"status": "ok"})
        emitted = raw.get("emitted_labels", raw.get("emitted", raw.get("labels", [])))
        intents = raw.get("intents", raw.get("actions", raw.get("commands", [])))

        if not isinstance(emitted, list):
            emitted = _ensure_list(emitted)
        if not isinstance(intents, list):
            intents = _ensure_list(intents)
        if not isinstance(outcome, dict):
            outcome = {"status": "ok", "raw_outcome": str(outcome)}

        return {
            "node_id": out_node_id,
            "node_type": out_node_type,
            "outcome": outcome,
            "emitted_labels": emitted,
            "intents": intents
        }

    def _call_underlying(self, node: Dict, current_tick: int):
        """
        Try a sequence of call signatures on the underlying cell-master/callable.
        Raises RuntimeError if no compatible entrypoint found.
        """
        # prefer execute_node
        if hasattr(self.cm, "execute_node") and callable(getattr(self.cm, "execute_node")):
            return self.cm.execute_node(node, current_tick=current_tick)
        # fallback names
        if hasattr(self.cm, "handle_node") and callable(getattr(self.cm, "handle_node")):
            return self.cm.handle_node(node, current_tick=current_tick)
        if hasattr(self.cm, "process_node") and callable(getattr(self.cm, "process_node")):
            return self.cm.process_node(node, current_tick=current_tick)
        # if underlying is a callable itself
        if callable(self.cm):
            return self.cm(node, current_tick=current_tick)
        raise RuntimeError("no_compatible_executor_on_cell_master")

    def execute_node(self, node: Dict, current_tick: int = 0) -> Dict:
        """
        Call underlying cell master safely and normalize result.
        """
        try:
            raw = self._call_underlying(node, current_tick)
            normalized = self._normalize(node, raw)
            # attach provenance if not present in each emitted label / intent
            for l in normalized.get("emitted_labels", []):
                if isinstance(l, dict):
                    l.setdefault("meta", {})
                    l["meta"].setdefault("provenance", []).append({"node_id": normalized["node_id"], "tick": current_tick})
            for it in normalized.get("intents", []):
                if isinstance(it, dict):
                    it.setdefault("meta", {})
                    it["meta"].setdefault("provenance", []).append({"node_id": normalized["node_id"], "tick": current_tick})
            return normalized
        except Exception as e:
            return self._wrap_error(node.get("node_id"), node.get("node_type"), e)

