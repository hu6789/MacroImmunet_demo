# cell_master/cell_master_base.py
from typing import List, Dict, Any, Optional
from collections import defaultdict

import random
import traceback

# cell_master/cell_master_base.py
from scan_master.event import ScanEvent

from .intents import Intent
from .gene_gate import GeneGate
from .executor import DefaultIntentExecutor
from scan_master.scan_master_base import rank_events

class CellMasterBase:
    def __init__(
        self,
        space=None,
        *,
        behaviour_registry=None,
        gene_gate=None,
        executor=None,
        feedback=None,
        rng=None,
        verbose=False,
        budget=None,
        score_threshold=None,
    ):
        self.space = space
        self.behaviour_registry = behaviour_registry or {}

        self.gene_gate = gene_gate or GeneGate()
        self.executor = executor or DefaultIntentExecutor()

        self.feedback = feedback
        self.rng = rng
        self.verbose = verbose

        # Step4.4.x
        self.budget = budget
        self.score_threshold = score_threshold

        self.intent_queue = []


    def handle_node_requests(
        self,
        region_id: str,
        node_requests: List[Dict[str, Any]],
        tick: int = 0,
    ) -> Dict[str, Any]:
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


                # === Step4.4.5: scored node → direct intent ===
                if isinstance(node, dict) and "score" in node and "meta" in node:
                    score = node.get("score", 0.0)
                    if self.score_threshold is not None and score < self.score_threshold:
                        intents = []
                    else:
                        intents = [self.node_to_intent(node)]

                # === Step3.6 fallback: use decide() if present ===
                elif hasattr(self, "decide"):
                    intents = self.decide(node) or []

                else:
                    intents = self._process_node_request(region_id, node, tick)
                # ✅ collect intents
                if intents:
                    all_intents.extend(intents)

                # Step4.4.5: enforce budget
                if self.budget is not None:
                    all_intents = all_intents[: self.budget]

                # Step4.4.5: enforce budget
                if self.budget is not None:
                    all_intents = all_intents[: self.budget]

            except Exception as e:
                errors.append({"node": nr, "error": str(e)})
                traceback.print_exc()

        # Step3.6: local intent queue for Scan→CellMaster test
        if not hasattr(self, "intent_queue"):
            self.intent_queue = []

        self.intent_queue.extend(all_intents)
        # === Step4.4.6: execute intents ===
        if self.executor is not None:
            for it in all_intents:
                try:
                    res = self.executor.execute(it)
                    results.append(res)
                except Exception as e:
                    errors.append({
                        "intent": it,
                        "error": str(e),
                    })
                    if self.verbose:
                        traceback.print_exc()


        return {
            "intents": all_intents,
            "results": results,
            "errors": errors,
        }
        for it in all_intents:
            try:
                if self.executor:
                    self.executor.execute(it)
            except Exception:
                traceback.print_exc()


    def handle_nodes(self, nodes, region_id: str = "default", tick: int = 0):
        """
        ScanMaster-facing entrypoint.
        Accepts raw node list and dispatches to handle_node_requests.
        """
        return self.handle_node_requests(
            region_id=region_id,
            node_requests=nodes,
            tick=tick
        )
    # --- Backward compatibility for Step4.4.5 tests ---
    def process_nodes(self, nodes, region_id: str = "default", tick: int = 0):
        """
        Legacy API: return intents list directly (used by tests).
        """
        out = self.handle_nodes(nodes, region_id=region_id, tick=tick)
        if isinstance(out, dict):
            return out.get("intents", [])
        return out

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

        # get candidate targets
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
                    # gene_gate.sample_fraction expects (items, fraction, rng, max_select?)
                    sampled = self.gene_gate.sample_fraction(targets, fraction=float(frac), rng=self.rng)
                    targets = sampled or []
            except Exception:
                pass

            for t in targets:
                try:
                    # target-level gating by gene gate (use cell meta if available)
                    cell_meta = getattr(t, "meta", {}) if t is not None else {}
                    allowed = self.gene_gate.allow(cell_meta, node_meta)
                    if isinstance(allowed, tuple):
                        allowed = bool(allowed[0])
                    if not allowed:
                        continue
                    # run behaviour: try registry.sample_and_run first, else call function
                    actions = self._run_behavior(behavior_name, runner, t, env, node_meta.get("params", {}), node_payload)
                    intents = self._normalize_actions_to_intents(actions, t)
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
                    # maybe {'actions': [...]} or {'result': [...]} or {'actions':..., 'meta':...}
                    if "actions" in out:
                        return out.get("actions") or []
                    if "result" in out:
                        return out.get("result") or []
                    # otherwise try to interpret as list-like
                    return out.get("actions", []) if isinstance(out.get("actions", []), list) else []
                if isinstance(out, list):
                    return out
                # final fallback: wrap single result
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
                    # normalize dict->list if it contains actions/result
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
    def node_to_intent(self, node):
        """
        Step4.9
        Convert a scored node into an executable intent with explainability
        """
        meta = node.get("meta", {}) or {}
        coord = meta.get("coord")
        score = node.get("score", 0.0)
        explain = node.get("explain", {}) or {}

        return {
            "name": "emit_label",
            "payload": {
                "coord": coord,
                "label": "PMHC",
                "amount": 1.0,
            },
            "meta": {
                "source": self.__class__.__name__,
                "score": score,
 
            # —— Step4.9 新增 ——
                "coord": coord,
                "sources": meta.get("sources", []),
                "event_explain": explain,
                "decision_path": "rank→merge→node→budget",

            # —— 向后兼容（可选，但我建议保留）——
                "reason": explain,
            }
        }

    def event_to_node(self, event):
        """
        Step4.7.x
        Translate ScanEvent -> scored node for CellMaster
        """
        type_map = {
            "antigen_peak": "antigen",
            "cytokine_peak": "cytokine",
            "danger_signal": "danger",
        }

        node_type = type_map.get(event.type, event.type)

        return {
            "meta": {
                "coord": event.coord,
                "type": node_type,
                "tick": event.tick,
                "raw_type": event.type,
            },
            "score": event.value,
            "explain": {
                "source": "scan_event",
                "type": event.type,
            }
        }

    def consume_event(self, event):
        """
        Step4.8.0
        Consume a single ScanEvent
        """
        node = self.event_to_node(event)
        return self.process_nodes([node])

    def consume_events(self, events):
        """
        Step4.8.1
        Consume multiple ScanEvents in priority order
        """
        if not events:
            return []

        ranked = rank_events(events)

        intents_out = []

        for e in ranked:
            intents = self.consume_event(e) or []
            intents_out.extend(intents)

            if self.budget is not None and len(intents_out) >= self.budget:
                break

        return intents_out
    def consume_events(self, events):
        """
        Step4.8.4
        rank → merge → node → rank nodes → apply budget → intents
        """
        if not events:
            return []

        # 1. event-level 排序
        ranked_events = rank_events(events)

        # 2. 合并同 coord
        merged_events = self.merge_events(ranked_events)

        # 3. coord → node
        nodes = self.merge_events_to_nodes(merged_events)

        # 4. node-level 排序（关键）
        nodes = sorted(nodes, key=lambda n: n["score"], reverse=True)

        # 5. budget 作用在 coord / node 层
        if self.budget is not None:
            nodes = nodes[: self.budget]

        # 6. 统一处理
        return self.process_nodes(nodes)


    def merge_events(self, events):
        by_coord = defaultdict(list)
        for e in events:
            by_coord[e.coord].append(e)

        merged = []
        for coord, evs in by_coord.items():
            if len(evs) == 1:
                merged.append(evs[0])
            else:
                merged.append(
                    ScanEvent(
                        coord=coord,
                        value=sum(e.value for e in evs),
                        type="merged",
                        tick=max(e.tick for e in evs),
                    )
                )
        return merged

    def merge_events_to_nodes(self, events):
        """
        Step4.7
        Merge ScanEvents into scored nodes by coord
        """
        buckets = {}

        for e in events:
            coord = e.coord
            if coord not in buckets:
                buckets[coord] = []
            buckets[coord].append(e)

        nodes = []

        for coord, evs in buckets.items():
            score = sum(e.value for e in evs)
            explain = {}
            sources = []

            for e in evs:
                sources.append(e.type)
                explain[e.type] = {
                    "value": e.value,
                    "meta": e.meta
                }

            nodes.append({
                "meta": {
                    "coord": coord,
                    "sources": sources
               },
                "score": score,
                "explain": explain
            })

        return nodes

