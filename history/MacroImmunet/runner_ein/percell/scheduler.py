# runner_ein/percell/scheduler.py
"""
Per-cell scheduler for runner_ein demo with support for:
 - submit(..., latency_ticks=...) -> schedule percell evaluation
 - advance(current_tick) -> return due scheduled entries (not executed)
 - process_intents(...) -> convenience immediate execution of a list of intents

Enhancements:
 - has_pending(cell_id=None, percell_type=None) -> bool
 - cancel_pending(cell_id=None, percell_type=None) -> List[entry]
 - duplicate protection: Scheduler(params={'allow_duplicates': False}) will
   avoid scheduling duplicate (cell_id, percell_type, due_tick) entries.
 - submit(..., allow_duplicates=True) can override the scheduler default.

Behavior:
 - submit schedules entries into an internal queue sorted by due_tick.
 - advance(current_tick) returns and removes items with due_tick <= current_tick.
 - submit supports kwargs merging (percell_type, params, latency_ticks, current_tick,
   execute_immediately). execute_immediately (bool) when True and latency==0 will
   call the percell handler immediately and return actions (list). Otherwise [].
 - The scheduler is defensive: failures emit env.emit_event('percell_error', {...})
"""

from typing import Any, Dict, List, Optional
import importlib
import traceback
import bisect

DEFAULT_ACTION_EVENT_PREFIX = "percell_action"

class Scheduler:
    def __init__(self, env: Any = None, params: Dict = None):
        """
        params (optional) may contain:
          - percell_map: { 'Th2': 'runner_ein.percell.th2_percell', ... }
          - default_params: dict passed through to percell.decide
          - percell_params: dict-of-dicts for percell-specific defaults
          - allow_duplicates: bool (default False) -- whether to permit scheduling duplicates
        """
        self.env = env
        self.params = params or {}
        self.percell_map = self.params.get("percell_map", {}) or {}
        self.default_params = self.params.get("default_params", {}) or {}
        self.percell_params = self.params.get("percell_params", {}) or {}
        # control duplicates globally (can be overridden per-submit)
        self.allow_duplicates = bool(self.params.get("allow_duplicates", False))

        # internal queue: list of tuples (due_tick, seq, entry)
        # seq breaks ties to preserve FIFO for same due_tick
        self._queue: List[tuple] = []
        self._seq = 0

    # ---------- import helpers ----------
    def _import_percell_module(self, percell_type: str):
        if not percell_type:
            return None, "missing_percell_type"
        mod_path = self.percell_map.get(percell_type)
        if not mod_path:
            mod_path = f"runner_ein.percell.{percell_type.lower()}_percell"
        try:
            mod = importlib.import_module(mod_path)
            return mod, None
        except Exception as e:
            return None, f"import_error: {mod_path}: {e}"

    def _find_cell_by_id(self, space: Any, cell_id: str):
        if cell_id is None:
            return None
        try:
            if hasattr(space, "cells") and isinstance(space.cells, dict):
                c = space.cells.get(cell_id)
                if c:
                    return c
        except Exception:
            pass
        # fallback: iterate
        try:
            if hasattr(space, "cells") and isinstance(space.cells, dict):
                for c in space.cells.values():
                    if getattr(c, "id", None) == cell_id:
                        return c
        except Exception:
            pass
        # helper heuristics
        try:
            get_cells = getattr(space, "get_cells_of_type", None)
            if callable(get_cells):
                lowered = (cell_id or "").lower()
                for t in ["naive_cd4","naive_cd8","dendriticcell","macrophage","th1","th2","effector_ctl"]:
                    if t in lowered:
                        candidates = get_cells(t)
                        for c in candidates:
                            if getattr(c, "id", None) == cell_id:
                                return c
        except Exception:
            pass
        return None

    # ---------- duplicate helpers ----------
    def _entry_key(self, entry: Dict) -> tuple:
        """Return a tuple key that defines 'duplicates' for an entry."""
        cell_id = getattr(entry.get("cell"), "id", None) or entry.get("intent", {}).get("cell_id")
        ptype = entry.get("percell_type")
        due = entry.get("due_tick")
        return (cell_id, ptype, int(due) if due is not None else None)

    def has_pending(self, cell_id: Optional[str] = None, percell_type: Optional[str] = None) -> bool:
        """Return True if there exists at least one queued entry matching provided filters."""
        try:
            for _, _, entry in self._queue:
                cid = getattr(entry.get("cell"), "id", None) or entry.get("intent", {}).get("cell_id")
                p = entry.get("percell_type")
                if cell_id is not None and percell_type is not None:
                    if cid == cell_id and p == percell_type:
                        return True
                elif cell_id is not None:
                    if cid == cell_id:
                        return True
                elif percell_type is not None:
                    if p == percell_type:
                        return True
                else:
                    # no filters -> any pending
                    return True
        except Exception:
            pass
        return False

    def cancel_pending(self, cell_id: Optional[str] = None, percell_type: Optional[str] = None) -> List[Dict]:
        """
        Remove pending entries matching the provided filters.
        Returns list of removed entries (the entry dicts).
        If no filters provided, cancels everything.
        """
        removed = []
        try:
            new_queue = []
            for due, seq, entry in self._queue:
                cid = getattr(entry.get("cell"), "id", None) or entry.get("intent", {}).get("cell_id")
                p = entry.get("percell_type")
                match = False
                if cell_id is not None and percell_type is not None:
                    match = (cid == cell_id and p == percell_type)
                elif cell_id is not None:
                    match = (cid == cell_id)
                elif percell_type is not None:
                    match = (p == percell_type)
                else:
                    match = True
                if match:
                    removed.append(entry)
                else:
                    new_queue.append((due, seq, entry))
            # replace queue
            self._queue = sorted(new_queue, key=lambda t: (t[0], t[1]))
            if removed and self.env and hasattr(self.env, "emit_event"):
                for e in removed:
                    try:
                        self.env.emit_event("percell_cancelled", {"cell_id": getattr(e.get("cell"), "id", None), "percell_type": e.get("percell_type"), "due_tick": e.get("due_tick")})
                    except Exception:
                        pass
        except Exception as e:
            if self.env and hasattr(self.env, "emit_event"):
                self.env.emit_event("percell_error", {"reason":"cancel_exception","error":str(e),"trace":traceback.format_exc()})
        return removed

    # ---------- scheduling API ----------
    def submit(self, *, cell: Optional[Any] = None, intent: Optional[Dict] = None,
               space: Optional[Any] = None, env: Optional[Any] = None, **kwargs) -> List[Dict]:
        """
        Schedule a percell evaluation.

        kwargs may include:
          - percell_type: str
          - params: dict (handler params)
          - latency_ticks: int (0 means due now)
          - current_tick: int (required if scheduling with latency)
          - execute_immediately: bool (if True and latency==0 -> call decide immediately)
          - allow_duplicates: bool (override scheduler default)
        Returns:
          - If execute_immediately True and latency==0: returns list of actions from percell.decide()
          - Otherwise returns [] (scheduling acknowledged)
        """
        env = env or self.env

        if intent is None:
            if kwargs:
                intent = dict(kwargs)
            else:
                if env and hasattr(env, "emit_event"):
                    env.emit_event("percell_error", {"reason":"no_intent_provided"})
                return []

        # merge kwargs into intent (kwargs override)
        try:
            tmp = dict(intent)
            tmp.update(kwargs)
            intent = tmp
        except Exception:
            pass

        # resolve cell if not provided
        if cell is None and space is not None:
            cid = intent.get("cell_id") or intent.get("target_cell") or intent.get("cell")
            if cid:
                cell = space.cells.get(cid) if hasattr(space, "cells") else None
                if cell is None:
                    cell = self._find_cell_by_id(space, cid)

        # check action
        action_name = intent.get("action") or intent.get("type")
        if action_name not in ("percell_evaluate","percell","percell_decide","percell_eval"):
            # not a percell intent
            return []

        percell_type = intent.get("percell_type") or intent.get("type_name") or intent.get("type")
        cell_id = intent.get("cell_id") or intent.get("target_cell") or intent.get("cell")
        if cell is None and space is not None and cell_id:
            cell = self._find_cell_by_id(space, cell_id)

        if cell is None:
            if env and hasattr(env, "emit_event"):
                env.emit_event("percell_error", {"reason":"cell_not_found","cell_id":cell_id,"intent":intent})
            return []

        # compute handler params (merge default / percell_params / intent.params / explicit params)
        handler_params = {}
        handler_params.update(self.default_params)
        handler_params.update(self.percell_params.get(percell_type, {}) or {})
        if isinstance(intent.get("params"), dict):
            handler_params.update(intent.get("params"))
        # also allow top-level explicit params (duplicate safe)
        explicit = intent.get("params") if isinstance(intent.get("params"), dict) else {}
        if isinstance(explicit, dict):
            handler_params.update(explicit)

        # parse latency + tick
        latency = int(intent.get("latency_ticks", intent.get("latency", 0) or 0))
        current_tick = intent.get("current_tick", intent.get("tick", None))
        if latency is None:
            latency = 0

        # execute immediately option
        exec_immediate = bool(intent.get("execute_immediately", False))

        # import module now to allow immediate execution if requested
        per_mod, err = self._import_percell_module(percell_type)
        if per_mod is None:
            if env and hasattr(env, "emit_event"):
                env.emit_event("percell_error", {"reason":"module_import_failed","detail":err,"percell_type":percell_type})
            return []

        decide_fn = getattr(per_mod, "decide", None)
        if not callable(decide_fn):
            if env and hasattr(env, "emit_event"):
                env.emit_event("percell_error", {"reason":"no_decide_fn","percell_type":percell_type})
            return []

        # immediate execution path
        if latency <= 0 and exec_immediate:
            try:
                result = decide_fn(cell, env, intent, handler_params)
            except Exception as e:
                if env and hasattr(env, "emit_event"):
                    env.emit_event("percell_error", {"reason":"decide_exception","percell_type":percell_type,"cell_id":getattr(cell,"id",None),"error":str(e),"trace":traceback.format_exc()})
                return []
            # normalize
            if result is None:
                result = []
            if isinstance(result, dict):
                result = [result]
            # emit percell action events
            for a in result:
                try:
                    ev_name = f"{DEFAULT_ACTION_EVENT_PREFIX}:{a.get('name','action')}"
                    if env and hasattr(env, "emit_event"):
                        env.emit_event(ev_name, {"cell_id": getattr(cell, "id", None), "action": a})
                except Exception:
                    if env and hasattr(env, "emit_event"):
                        env.emit_event("percell_action_emitted", {"cell_id": getattr(cell, "id", None), "action": a})
            return result

        # otherwise schedule into internal queue
        if current_tick is None:
            # best-effort: try to use env.tick if available
            try:
                current_tick = getattr(env, "tick", None)
            except Exception:
                current_tick = None
        if current_tick is None:
            # fallback to 0
            current_tick = 0

        due = int(current_tick) + int(latency)
        entry = {
            "due_tick": due,
            "cell": cell,
            "intent": intent,
            "percell_type": percell_type,
            "params": handler_params,
            "scheduled_at": int(current_tick)
        }

        # duplicate protection
        allow_dup = bool(intent.get("allow_duplicates", self.allow_duplicates))
        if not allow_dup:
            # consider duplicates by (cell_id, percell_type, due_tick)
            key = (getattr(cell, "id", None) or cell_id, percell_type, due)
            for _, _, e in self._queue:
                ek = (getattr(e.get("cell"), "id", None) or e.get("intent", {}).get("cell_id"), e.get("percell_type"), e.get("due_tick"))
                if ek == key:
                    # duplicate found -> skip scheduling
                    if env and hasattr(env, "emit_event"):
                        try:
                            env.emit_event("percell_skipped_duplicate", {"cell_id": key[0], "percell_type": key[1], "due_tick": key[2]})
                        except Exception:
                            pass
                    return []

        # insert keeping queue sorted by (due_tick, seq)
        bisect.insort(self._queue, (entry["due_tick"], self._seq, entry))
        self._seq += 1

        if env and hasattr(env, "emit_event"):
            try:
                env.emit_event("percell_scheduled", {"cell_id": getattr(cell, "id", None), "percell_type": percell_type, "due_tick": due})
            except Exception:
                pass
        return []

    def advance(self, current_tick: int) -> List[Dict]:
        """
        Advance the scheduler to `current_tick` and return list of due entries (entries removed).
        Each returned entry is the dict that was scheduled (has keys: cell,intent,percell_type,params,due_tick).
        The orchestrator/demo will typically call percell decide() on these entries.
        """
        due_list = []
        try:
            while self._queue and self._queue[0][0] <= int(current_tick):
                _, _, entry = self._queue.pop(0)
                due_list.append(entry)
                if self.env and hasattr(self.env, "emit_event"):
                    try:
                        self.env.emit_event("percell_due", {"cell_id": getattr(entry["cell"], "id", None), "percell_type": entry.get("percell_type"), "due_tick": entry.get("due_tick")})
                    except Exception:
                        pass
        except Exception as e:
            if self.env and hasattr(self.env, "emit_event"):
                self.env.emit_event("percell_error", {"reason":"advance_exception","error":str(e),"trace":traceback.format_exc()})
        return due_list

    # ---------- bulk immediate processor (compat) ----------
    def process_intents(self, intents: List[Dict], space: Any, env: Any = None) -> List[Dict]:
        """
        Immediately process a list of percell-style intents (synchronous).
        Returns flattened list of actions produced.
        """
        env = env or self.env
        actions = []
        if not intents:
            return actions

        for intent in intents:
            try:
                action = intent.get("action") or intent.get("type")
                if action not in ("percell_evaluate","percell","percell_decide","percell_eval"):
                    continue
                percell_type = intent.get("percell_type") or intent.get("type_name") or intent.get("type")
                cell_id = intent.get("cell_id") or intent.get("target_cell") or intent.get("cell")
                cell = self._find_cell_by_id(space, cell_id)
                if cell is None:
                    if env and hasattr(env, "emit_event"):
                        env.emit_event("percell_error", {"reason":"cell_not_found","cell_id":cell_id,"intent":intent})
                    continue
                per_mod, err = self._import_percell_module(percell_type)
                if per_mod is None:
                    if env and hasattr(env, "emit_event"):
                        env.emit_event("percell_error", {"reason":"module_import_failed","detail":err,"percell_type":percell_type})
                    continue
                decide_fn = getattr(per_mod, "decide", None)
                if not callable(decide_fn):
                    if env and hasattr(env, "emit_event"):
                        env.emit_event("percell_error", {"reason":"no_decide_fn","percell_type":percell_type})
                    continue

                # build handler params
                handler_params = {}
                handler_params.update(self.default_params)
                handler_params.update(self.percell_params.get(percell_type, {}) or {})
                if isinstance(intent.get("params"), dict):
                    handler_params.update(intent.get("params"))

                try:
                    result_actions = decide_fn(cell, env, intent, handler_params)
                except Exception as e:
                    if env and hasattr(env, "emit_event"):
                        env.emit_event("percell_error", {"reason":"decide_exception","percell_type":percell_type,"cell_id":cell_id,"error":str(e),"trace":traceback.format_exc()})
                    result_actions = []

                if result_actions is None:
                    result_actions = []
                if isinstance(result_actions, dict):
                    result_actions = [result_actions]

                for a in result_actions:
                    try:
                        if env and hasattr(env, "emit_event"):
                            ev_name = f"{DEFAULT_ACTION_EVENT_PREFIX}:{a.get('name','action')}"
                            env.emit_event(ev_name, {"cell_id": getattr(cell, "id", None), "action": a})
                    except Exception:
                        if env and hasattr(env, "emit_event"):
                            env.emit_event("percell_action_emitted", {"cell_id": getattr(cell, "id", None), "action": a})
                    actions.append(a)

            except Exception as e_main:
                if env and hasattr(env, "emit_event"):
                    env.emit_event("percell_scheduler_error", {"error": str(e_main), "trace": traceback.format_exc(), "intent": intent})
                continue

        return actions

