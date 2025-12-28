# cell_master/cell_master_base.py
"""
CellMasterBase - minimal demo-friendly cell-master implementation.

Responsibilities:
 - select targets (via space API)
 - apply gene gating (GeneGate)
 - resolve & run behaviours (registry or callable)
 - normalize behaviour actions into Intent instances
 - commit intents through Executor

This file is intentionally conservative and defensive: it tolerates multiple
registry/space layouts and normalizes various return shapes from behaviours/registries.
"""
from typing import List, Dict, Any, Optional
from cell_master.gene_gate import GeneGate
from cell_master.intents import Intent
from cell_master.executor import Executor
import traceback
import random


class _LabelWrapper:
    """
    Minimal cell-like wrapper for label dicts returned by Space.
    Exposes .id, .coord, .meta, .position and other convenient attributes.
    """
    def __init__(self, label: Dict[str, Any]):
        self._label = label or {}
        # try common keys
        self.id = self._label.get("id") or self._label.get("name") or self._label.get("label")
        self.coord = self._label.get("coord") or self._label.get("position")
        self.position = self.coord
        self.meta = dict(self._label.get("meta") or {})
        # expose fallback attributes for behaviours that inspect other keys directly
        for k, v in self._label.items():
            # avoid clobbering core attrs
            if k in ("id", "coord", "position", "meta"):
                continue
            try:
                setattr(self, k, v)
            except Exception:
                pass

    def __repr__(self):
        return f"<LabelWrapper id={self.id} coord={self.coord}>"


class CellMasterBase:
    """
    Minimal, demo-friendly CellMaster base.

    Usage:
      cm = CellMasterBase(space, behaviour_registry, feedback_module=scan_master.feedback, genotype={})
      result = cm.handle_node_requests("region_0", node_requests, tick=5)
    """
    def __init__(self, space, behaviour_registry, feedback_module=None, genotype: Dict[str,Any]=None, rng=None, verbose: bool=False):
        self.space = space
        self.registry = behaviour_registry
        self.feedback = feedback_module
        # GeneGate may accept genotype mapping or config dict in constructor
        self.gene_gate = GeneGate(genotype or {})
        # Executor can be swapped in tests by assigning cell_master.executor.Executor = FakeExecutor
        self.executor = Executor(space, feedback_module)
        # use provided RNG or create deterministic one if seed passed to GeneGate
        self.rng = rng or random.Random()
        self.verbose = verbose

    def handle_node_requests(self, region_id: str, node_requests: List[Dict[str,Any]], tick: int = 0) -> Dict[str,Any]:
        """
        Top-level entry: process a list of node_requests and commit produced intents.
        Returns summary: {'intents': [...], 'results': [...], 'errors': [...]}
        """
        all_intents = []
        errors = []
        results = []

        for nr in node_requests:
            try:
                node = nr.get("node") if isinstance(nr, dict) and "node" in nr else nr
                intents = self._process_node_request(region_id, node, tick)
                if intents:
                    all_intents.extend(intents)
            except Exception as e:
                errors.append({"node": nr, "error": str(e)})
                traceback.print_exc()

        # commit all intents via executor
        try:
            commit_res = self.executor.apply_intents(region_id, all_intents, tick=tick)
            results = commit_res
        except Exception as e:
            errors.append({"commit_error": str(e)})
            traceback.print_exc()

        return {"intents": all_intents, "results": results, "errors": errors}

    # -------------------- internal helpers --------------------

    def _wrap_label_as_cell(self, label_or_obj: Any):
        """
        If input is a plain mapping/label dict, wrap into a simple cell-like object.
        If it's already an object with `.meta` or `.id`, return as-is.
        """
        if label_or_obj is None:
            return None
        # if dict-like -> wrap
        if isinstance(label_or_obj, dict):
            return _LabelWrapper(label_or_obj)
        # if it already looks cell-like, return directly
        if hasattr(label_or_obj, "meta") or hasattr(label_or_obj, "id"):
            return label_or_obj
        # fallback: try to build wrapper from __dict__
        try:
            d = dict(vars(label_or_obj))
            return _LabelWrapper(d)
        except Exception:
            # last resort: return original
            return label_or_obj

    def _process_node_request(self, region_id: str, node: Dict[str,Any], tick: int) -> List[Intent]:
        """
        Process a single node dict:
         - parse behavior name/meta/payload
         - select targets
         - perform gene gating
         - run behavior per target (or once for aggregate)
         - normalize actions -> intents
        """
        behavior_name = node.get("behavior") or node.get("action") or node.get("name")
        node_meta = node.get("meta", {}) or {}
        node_payload = node.get("payload", {}) or {}

        # get candidate targets (may be label dicts or objects)
        targets = node.get("targets")
        if not targets:
            targets = self._select_targets(region_id, node_meta, node_payload)

        intents_out = []
        # early gate (node-level gating); allow() may return bool or (bool, details)
        try:
            allowed = self.gene_gate.allow({}, node_meta)
            if isinstance(allowed, tuple):
                allowed = bool(allowed[0])
            if not allowed:
                if self.verbose:
                    print("gene_gate blocked node:", behavior_name)
                return []
        except Exception:
            # if gate malfunctions, be permissive
            pass

        # behavior runner
        runner = self._resolve_runner(behavior_name)

        # if runner is None, nothing to do
        if runner is None:
            if self.verbose:
                print("No runner for behavior:", behavior_name)
            return []

        env = self.feedback if self.feedback is not None else self.space

        # Decide whether this node should be run aggregated or per-target
        run_per_target = bool(targets)

        if run_per_target:
            # pre-filter using gene_gate.batch_filter if available to reduce work
            try:
                targets = self.gene_gate.batch_filter(targets, node_meta) or targets
            except Exception:
                # fallback: leave targets as-is
                pass

            # optionally sample a fraction according to node_meta
            try:
                frac = node_meta.get("sample_fraction", None)
                if frac is not None:
                    sampled = self.gene_gate.sample_fraction(targets, fraction=float(frac), rng=self.rng)
                    targets = sampled or []
            except Exception:
                pass

            for t in targets:
                try:
                    # ensure we pass a cell-like object to behaviour implementations
                    cell_obj = self._wrap_label_as_cell(t)

                    # target-level gating by gene gate (use cell meta if available)
                    cell_meta = getattr(cell_obj, "meta", {}) if cell_obj is not None else {}
                    allowed = self.gene_gate.allow(cell_meta, node_meta)
                    if isinstance(allowed, tuple):
                        allowed = bool(allowed[0])
                    if not allowed:
                        if self.verbose:
                            print(f"gene_gate blocked target {getattr(cell_obj,'id', None)} for behavior {behavior_name}")
                        continue

                    # run behaviour: try registry.sample_and_run first, else call function
                    actions = self._run_behavior(behavior_name, runner, cell_obj, env, node_meta.get("params", {}), node_payload)
                    if self.verbose:
                        print(f"Ran behavior {behavior_name} on {getattr(cell_obj,'id', cell_obj)} -> actions: {actions}")
                    intents = self._normalize_actions_to_intents(actions, cell_obj)
                    intents_out.extend(intents)
                except Exception:
                    traceback.print_exc()
                    continue
        else:
            # aggregated run: pass a synthetic aggregator object (could be region summary)
            try:
                actions = self._run_behavior(behavior_name, runner, None, env, node_meta.get("params", {}), node_payload)
                intents_out.extend(self._normalize_actions_to_intents(actions, None))
            except Exception:
                traceback.print_exc()

        return intents_out

    def _resolve_runner(self, behavior_name: Optional[str]):
        if not behavior_name:
            return None
        try:
            # registry may be callable factory or object with .get
            reg = self.registry() if callable(self.registry) and not hasattr(self.registry, "get") else self.registry
            # try .get first
            runner = getattr(reg, "get", lambda n: None)(behavior_name)
            # fallback: behaviour_registry may expose direct lookup list/dict
            if not runner and hasattr(reg, "list") and behavior_name in reg.list():
                runner = getattr(reg, "get", lambda n: None)(behavior_name)
            # final fallback: registry could be dict-like
            if not runner and isinstance(reg, dict):
                runner = reg.get(behavior_name)
            return runner
        except Exception:
            return None

    def _run_behavior(self, behavior_name, runner, cell_obj, env, params, payload):
        """
        Execute behaviour via runner or registry helpers.
        Normalize to list of action dicts (or empty list).
        """
        # try registry.sample_and_run on registry object if present
        try:
            reg_obj = self.registry() if callable(self.registry) and not hasattr(self.registry, "get") else self.registry
            if hasattr(reg_obj, "sample_and_run"):
                out = reg_obj.sample_and_run(behavior_name, cell_obj, env, params=params, payload=payload)
                # normalize various return shapes
                if out is None:
                    return []
                if isinstance(out, dict):
                    if "actions" in out:
                        return out.get("actions") or []
                    if "result" in out:
                        return out.get("result") or []
                    # fallback: try to extract list-like keys
                    for k in ("actions", "result", "results"):
                        if k in out and isinstance(out[k], list):
                            return out[k]
                    # nothing list-like -> wrap
                    return [out]
                if isinstance(out, list):
                    return out
                return [out]
        except Exception:
            # ignore and fallback to runner callable
            pass

        # runner might be a callable behaviour
        try:
            if callable(runner):
                out = runner(cell_obj, env, params=params, payload=payload)
                if out is None:
                    return []
                if isinstance(out, list):
                    return out
                if isinstance(out, dict):
                    if "actions" in out:
                        return out.get("actions") or []
                    if "result" in out:
                        return out.get("result") or []
                    return [out]
                return [out]
        except Exception:
            traceback.print_exc()
        return []

    def _select_targets(self, region_id: str, node_meta: Dict[str,Any], node_payload: Dict[str,Any]) -> List[Any]:
        """Select candidate cells from space according to node_meta (target_cell_type, sample_fraction, coord/radius)"""
        try:
            # explicit type -> query canonical labels
            ttype = node_meta.get("target_cell_type")
            if ttype and hasattr(self.space, "get_labels_by_canonical"):
                cand = self.space.get_labels_by_canonical(region_id, ttype)
            else:
                cand = self.space.get_labels(region_id) if hasattr(self.space, "get_labels") else []

            # allow gene_gate to pre-filter batch (if implemented)
            try:
                cand = self.gene_gate.batch_filter(cand, node_meta) or cand
            except Exception:
                pass

            # sample fraction handled by sample_fraction higher up, but keep a safe fallback:
            frac = node_meta.get("sample_fraction", None)
            if frac is not None:
                try:
                    cand = self.gene_gate.sample_fraction(cand, fraction=float(frac), rng=self.rng)
                    return cand or []
                except Exception:
                    # fallback to simple sampling
                    try:
                        fracf = float(frac)
                        if fracf < 1.0:
                            k = max(1, int(len(cand) * fracf))
                            return random.sample(cand, min(k, len(cand)))
                    except Exception:
                        pass
            return cand
        except Exception:
            return []

    def _normalize_actions_to_intents(self, actions, src_cell):
        """
        Convert behavior actions into Intent instances (or plain dicts).
        For demo we return simple dicts that Executor understands.
        """
        intents = []
        for a in (actions or []):
            if a is None:
                continue
            # if already an Intent-like object
            if isinstance(a, Intent):
                intents.append(a)
                continue
            # action as dict with name/payload
            if isinstance(a, dict):
                name = a.get("name") or a.get("action") or "unknown"
                payload = a.get("payload") or a
                it = Intent(name=name, payload=payload, src_cell_id=getattr(src_cell, "id", None), coord=getattr(src_cell, "coord", None))
                intents.append(it)
            else:
                # fallback: wrap in generic Intent
                it = Intent(name=str(a), payload={"value": a}, src_cell_id=getattr(src_cell, "id", None), coord=getattr(src_cell, "coord", None))
                intents.append(it)
        return intents


# ----------------- simple __main__ self-check for local runs -----------------
if __name__ == "__main__":
    import sys
    import time

    print("Running CellMasterBase self-check demo...")

    # minimal fake space
    class FakeSpace:
        def __init__(self):
            self._labels = [
                {"id": "cell_1", "coord": (0.0, 0.0), "meta": {"viral_load": 5.0}},
                {"id": "cell_2", "coord": (1.0, 0.0), "meta": {"viral_load": 0.0}},
            ]
        def get_labels(self, region_id):
            return list(self._labels)
        def get_labels_by_canonical(self, region_id, canonical):
            # demo: return all labels if canonical matches "ALL", otherwise none
            if canonical == "ALL":
                return list(self._labels)
            return []

    # minimal fake registry exposing .get(name)
    class FakeRegistry:
        def __init__(self):
            pass
        def get(self, name):
            # simple behaviour that emits a single action per targeted cell
            def behaviour(cell, env, params=None, payload=None):
                cid = getattr(cell, "id", None) or (cell.get("id") if isinstance(cell, dict) else None)
                return [{"name":"demo_action", "payload": {"cell_id": cid, "detail": "demo"}}]
            return behaviour

    # fake executor that records calls
    class FakeExecutor:
        def __init__(self):
            self.calls = []
        def apply_intents(self, region_id, intents, tick=0):
            self.calls.append({"region": region_id, "count": len(intents), "tick": tick, "intents": intents})
            # return a simple summary similar to real executor
            return [{"applied": len(intents), "ok": True}]

    # Build CellMasterBase with fakes
    space = FakeSpace()
    reg = FakeRegistry()
    cm = CellMasterBase(space=space, behaviour_registry=reg, feedback_module=None, genotype={}, rng=random.Random(123), verbose=True)
    # replace executor with fake so we can inspect calls
    cm.executor = FakeExecutor()

    # node to run: no explicit targets -> will use space.get_labels
    node = {"behavior": "any_behaviour_name", "meta": {}, "payload": {}}

    start = time.time()
    out = cm.handle_node_requests("region_demo", [node], tick=1)
    dur = time.time() - start

    print("Self-check result summary (handle_node_requests):")
    print("  intents produced:", len(out.get("intents", [])))
    print("  executor results:", out.get("results"))
    print("  errors:", out.get("errors"))
    print("  executor fake recorded calls:", getattr(cm.executor, "calls", []))
    print(f"  elapsed: {dur:.4f}s")

    ok = False
    try:
        # success criteria: at least one intent produced and executor.apply_intents called
        if len(out.get("intents", [])) > 0 and getattr(cm.executor, "calls", []):
            ok = True
    except Exception:
        ok = False

    if ok:
        print("\nSELF-CHECK: PASS")
        sys.exit(0)
    else:
        print("\nSELF-CHECK: FAIL (no intents produced or executor not called)")
        sys.exit(2)

