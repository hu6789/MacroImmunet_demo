# scan_master/node_dispatcher.py
"""
Robust node dispatcher for MacroImmunet demo tests.

Main export:
  dispatch_nodes(nodes: list, cell_master_adapter: object, current_tick: int=0) -> dict

This dispatcher:
 - ensures node_id/node_type exist
 - calls cell_master_adapter.execute_node(node, current_tick=...)
 - accepts a variety of return shapes (dict, tuple/list, non-dict) and normalizes
 - collects emitted_labels and intents across nodes and returns a full result
 - logs normalized responses for easier debugging in tests
"""
from typing import List, Dict, Any
import logging
import uuid
import traceback

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

def _ensure_list(x):
    if x is None:
        return []
    if isinstance(x, list):
        return x
    return [x]

def _normalize_cm_response(node: Dict[str, Any], raw: Any) -> Dict[str, Any]:
    """
    Normalize possible cell-master responses into a dict with keys:
      - node_id, node_type, outcome (dict), emitted_labels (list), intents (list)
    """
    node_id = node.get("node_id") or f"{node.get('node_type','node')}_{uuid.uuid4().hex[:8]}"
    node_type = node.get("node_type", "unknown")

    # exceptions -> failure outcome
    if isinstance(raw, Exception):
        tb = traceback.format_exc()
        return {
            "node_id": node_id,
            "node_type": node_type,
            "outcome": {"status": "failed", "error": str(raw), "traceback": tb},
            "emitted_labels": [],
            "intents": []
        }

    # None -> failed
    if raw is None:
        return {
            "node_id": node_id,
            "node_type": node_type,
            "outcome": {"status": "failed", "error": "none_response"},
            "emitted_labels": [],
            "intents": []
        }

    # dict -> pick canonical fields
    if isinstance(raw, dict):
        out_node_id = raw.get("node_id", node_id)
        out_node_type = raw.get("node_type", node_type)
        outcome = raw.get("outcome", {"status": "ok"})
        emitted = raw.get("emitted_labels", raw.get("emitted", raw.get("labels", [])))
        intents = raw.get("intents", raw.get("actions", raw.get("commands", [])))
        # defensive coercion
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

    # tuple/list heuristic patterns: (outcome, emitted, intents) or (emitted, intents)
    if isinstance(raw, (list, tuple)):
        emitted = []
        intents = []
        outcome = {"status": "ok"}
        # heuristics
        if len(raw) == 1:
            # maybe emitted list
            if isinstance(raw[0], list):
                emitted = raw[0]
            else:
                emitted = [raw[0]]
        elif len(raw) == 2:
            # (emitted, intents) or (outcome, emitted)
            if isinstance(raw[0], dict) and "status" in raw[0]:
                outcome = raw[0]
                emitted = _ensure_list(raw[1])
            else:
                emitted = _ensure_list(raw[0])
                intents = _ensure_list(raw[1])
        else:
            # (outcome, emitted, intents, ...)
            if isinstance(raw[0], dict) and "status" in raw[0]:
                outcome = raw[0]
                emitted = _ensure_list(raw[1])
                intents = _ensure_list(raw[2])
            else:
                emitted = _ensure_list(raw[1])
                intents = _ensure_list(raw[2]) if len(raw) >= 3 else []
        return {
            "node_id": node_id,
            "node_type": node_type,
            "outcome": outcome,
            "emitted_labels": emitted,
            "intents": intents
        }

    # fallback for unknown return types
    return {
        "node_id": node_id,
        "node_type": node_type,
        "outcome": {"status": "failed", "error": f"unexpected_response_type:{type(raw)}"},
        "emitted_labels": [],
        "intents": []
    }

def dispatch_nodes(nodes: List[Dict[str, Any]], cell_master_adapter: Any, current_tick: int = 0) -> Dict[str, Any]:
    """
    Dispatch a list of nodes to the provided cell master adapter.

    nodes: list of dicts, each node should at least have node_type. node_id is optional.
    cell_master_adapter: object with execute_node(node, current_tick=...) method (or callable)
    current_tick: integer tick for provenance bookkeeping

    Returns dict:
      {
        "results": [ normalized per-node dicts... ],
        "emitted_labels": [ ... all emitted labels ... ],
        "intents": [ ... all intents ... ]
      }
    """
    results = []
    emitted_labels = []
    intents = []

    for idx, node in enumerate(nodes):
        # ensure node_id exists for provenance
        if "node_id" not in node:
            node = dict(node)
            node["node_id"] = f"{node.get('node_type','node')}_{uuid.uuid4().hex[:8]}"

        try:
            # Prefer explicit execute_node if provided
            if hasattr(cell_master_adapter, "execute_node"):
                raw = cell_master_adapter.execute_node(node, current_tick=current_tick)
            elif callable(cell_master_adapter):
                raw = cell_master_adapter(node, current_tick=current_tick)
            else:
                raise RuntimeError("cell_master_adapter not callable and has no execute_node")
        except Exception as e:
            logger.exception("cell_master.execute_node failed for node %s: %s", node.get("node_id"), e)
            raw = e

        norm = _normalize_cm_response(node, raw)

        # attach provenance to emitted labels & intents (if dicts)
        for l in norm.get("emitted_labels", []):
            if isinstance(l, dict):
                l.setdefault("meta", {})
                l["meta"].setdefault("provenance", []).append({"node_id": norm["node_id"], "tick": current_tick})
        for it in norm.get("intents", []):
            if isinstance(it, dict):
                it.setdefault("meta", {})
                it["meta"].setdefault("provenance", []).append({"node_id": norm["node_id"], "tick": current_tick})

        # extend global lists
        emitted_labels.extend(norm.get("emitted_labels", []))
        intents.extend(norm.get("intents", []))
        results.append(norm)

        # debug log each normalized result for easier traceability in tests
        logger.debug("dispatch_nodes: node %s normalized -> outcome=%s emitted=%d intents=%d",
                     norm.get("node_id"), norm.get("outcome"), len(norm.get("emitted_labels", [])), len(norm.get("intents", [])))

    return {"results": results, "emitted_labels": emitted_labels, "intents": intents}

