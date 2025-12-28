# cell_master/executor.py
"""
Executor: commit intents into the environment (feedback or space).

Demo-friendly implementation:
 - Accepts Intent instances or plain dict actions
 - Tries high-level apply_intent on provided feedback module if available
 - Otherwise tries common env APIs (add_to_field, spawn_cell, emit_event, emit_intent, get_cell)
 - Always returns a list of per-intent results for inspection
"""

from typing import Any, Dict, List, Optional
import time
import traceback

# Avoid circular import at module load-time; expect Intent dataclass exists in same package
try:
    from .intents import Intent
except Exception:
    Intent = None  # fallback, handle dynamically


class Executor:
    def __init__(self, space: Any, feedback_module: Optional[Any] = None, verbose: bool = False):
        """
        space: the core Space object (may expose add_to_field, spawn_cell, get_labels, etc.)
        feedback_module: optional higher-level module (scan_master.feedback) with apply_intent / emit_intent
        """
        self.space = space
        self.feedback = feedback_module
        self.verbose = verbose

    def _norm_intent(self, intent) -> Dict[str, Any]:
        """
        Normalize incoming intent (Intent instance, dict or string) into dict with keys:
         - name, payload, src_cell_id, coord, created_ts (if Intent provided preserve), priority
        """
        if Intent is not None and isinstance(intent, Intent):
            return {
                "name": intent.name,
                "payload": intent.payload or {},
                "src_cell_id": getattr(intent, "src_cell_id", None),
                "coord": getattr(intent, "coord", None),
                "created_ts": getattr(intent, "created_ts", time.time()),
                "priority": getattr(intent, "priority", 0),
                "raw": intent,
            }
        # dict-like
        if isinstance(intent, dict):
            name = intent.get("name") or intent.get("action") or intent.get("intent") or str(intent)
            payload = intent.get("payload") if "payload" in intent else intent
            return {
                "name": name,
                "payload": payload or {},
                "src_cell_id": intent.get("src_cell_id") or intent.get("src") or None,
                "coord": intent.get("coord") or intent.get("position") or None,
                "created_ts": intent.get("created_ts") or time.time(),
                "priority": intent.get("priority") or 0,
                "raw": intent,
            }
        # unknown type: wrap
        return {
            "name": str(intent),
            "payload": {"value": intent},
            "src_cell_id": None,
            "coord": None,
            "created_ts": time.time(),
            "priority": 0,
            "raw": intent,
        }

    def apply_intents(self, region_id: str, intents: List[Any], tick: int = 0) -> List[Dict[str, Any]]:
        """
        Apply a list of intents. Returns list of result dicts:
            { "intent": <name>, "ok": bool, "detail": str, "applied_payload": {} }
        This function catches exceptions and never propagates them.
        """
        results = []
        if not intents:
            return results

        # Prefer a single call if feedback exposes a bulk apply API
        try:
            fb = self.feedback
            if fb is not None and hasattr(fb, "apply_intents"):
                # call once; expect list-of-results or boolean
                try:
                    res = fb.apply_intents(region_id, intents, tick=tick)
                    # normalize when boolean
                    if isinstance(res, bool):
                        # assume success for all
                        for it in intents:
                            n = self._norm_intent(it)
                            results.append({"intent": n["name"], "ok": res, "detail": "delegated to feedback.apply_intents", "applied_payload": n["payload"]})
                        return results
                    # if list/dict, try to return as-is (but ensure mapping)
                    if isinstance(res, list):
                        return res
                    # fallback wrap
                    return [{"intent": str(res), "ok": True, "detail": "feedback.apply_intents returned non-list", "applied_payload": {}}]
                except Exception:
                    # if feedback.apply_intents fails, fallthrough to per-intent handling
                    if self.verbose:
                        traceback.print_exc()
        except Exception:
            pass

        # per-intent handling
        for it in intents:
            n = self._norm_intent(it)
            name = n["name"]
            payload = n["payload"] or {}
            coord = n.get("coord")
            res_entry = {"intent": name, "ok": False, "detail": None, "applied_payload": payload}
            try:
                applied = False
                # 1) try feedback.apply_intent(intent_name, payload)
                if self.feedback is not None and hasattr(self.feedback, "apply_intent"):
                    try:
                        ok = self.feedback.apply_intent(name, payload, region_id=region_id, tick=tick)
                        res_entry["ok"] = bool(ok)
                        res_entry["detail"] = "feedback.apply_intent"
                        applied = True
                    except TypeError:
                        # some apply_intent signatures may differ, try with fewer args
                        try:
                            ok = self.feedback.apply_intent(name, payload)
                            res_entry["ok"] = bool(ok)
                            res_entry["detail"] = "feedback.apply_intent"
                            applied = True
                        except Exception:
                            applied = False
                    except Exception:
                        # fallback to other handlers below
                        applied = False

                # 2) try environment 'emit_intent' / 'emit_event'
                if not applied and self.feedback is not None and hasattr(self.feedback, "emit_intent"):
                    try:
                        self.feedback.emit_intent(name, payload)
                        res_entry["ok"] = True
                        res_entry["detail"] = "feedback.emit_intent"
                        applied = True
                    except Exception:
                        applied = False

                # 3) common engine primitives (add_to_field / spawn_cell / emit_event)
                if not applied and self.feedback is not None:
                    fb = self.feedback
                    # handle add_to_field pattern
                    if name in ("add_to_field", "secrete_field", "secrete") and "field" in payload:
                        try:
                            field = payload.get("field")
                            amount = payload.get("amount") or payload.get("rate_per_tick") or payload.get("delta") or payload.get("rate") or 0.0
                            if hasattr(fb, "add_to_field"):
                                fb.add_to_field(field, coord, amount)
                                res_entry["ok"] = True
                                res_entry["detail"] = "feedback.add_to_field"
                                applied = True
                        except Exception:
                            applied = False
                    # spawn_cell / spawn
                    if not applied and name in ("spawn_cell", "spawned", "spawn"):
                        try:
                            c = payload.get("coord") or coord
                            ctype = payload.get("cell_type") or payload.get("type")
                            meta = payload.get("meta") or {}
                            if hasattr(fb, "spawn_cell"):
                                nid = fb.spawn_cell(c, cell_type=ctype, meta=meta)
                                res_entry["ok"] = True
                                res_entry["detail"] = f"feedback.spawn_cell -> {nid}"
                                applied = True
                        except Exception:
                            applied = False
                    # emit_event fallback
                    if not applied and hasattr(fb, "emit_event"):
                        try:
                            fb.emit_event(name, payload)
                            res_entry["ok"] = True
                            res_entry["detail"] = "feedback.emit_event"
                            applied = True
                        except Exception:
                            applied = False

                # 4) if still not applied, try calling space-level apis
                if not applied and self.space is not None:
                    sp = self.space
                    if hasattr(sp, "apply_intent"):
                        try:
                            ok = sp.apply_intent(name, payload, region_id=region_id, tick=tick)
                            res_entry["ok"] = bool(ok)
                            res_entry["detail"] = "space.apply_intent"
                            applied = True
                        except Exception:
                            applied = False
                    if not applied and hasattr(sp, "add_to_field") and name in ("add_to_field", "secrete_field", "secrete"):
                        try:
                            sp.add_to_field(payload.get("field"), coord, payload.get("amount") or payload.get("delta") or 0.0)
                            res_entry["ok"] = True
                            res_entry["detail"] = "space.add_to_field"
                            applied = True
                        except Exception:
                            applied = False
                    if not applied and hasattr(sp, "spawn_cell") and name in ("spawn_cell", "spawned", "spawn"):
                        try:
                            nid = sp.spawn_cell(payload.get("coord") or coord, payload.get("cell_type") or payload.get("type"), payload.get("meta"))
                            res_entry["ok"] = True
                            res_entry["detail"] = f"space.spawn_cell -> {nid}"
                            applied = True
                        except Exception:
                            applied = False
                    if not applied and hasattr(sp, "emit_event"):
                        try:
                            sp.emit_event(name, payload)
                            res_entry["ok"] = True
                            res_entry["detail"] = "space.emit_event"
                            applied = True
                        except Exception:
                            applied = False

                # 5) if still not applied, mark as emitted (best-effort) via feedback.emit_event if exists
                if not applied:
                    try:
                        if self.feedback is not None and hasattr(self.feedback, "emit_event"):
                            self.feedback.emit_event(name, payload)
                            res_entry["ok"] = True
                            res_entry["detail"] = "fallback feedback.emit_event"
                            applied = True
                    except Exception:
                        applied = False

                if not applied:
                    res_entry["ok"] = False
                    if res_entry["detail"] is None:
                        res_entry["detail"] = "no applicable API found to apply intent"
            except Exception as e:
                res_entry["ok"] = False
                res_entry["detail"] = f"exception: {str(e)}"
                if self.verbose:
                    traceback.print_exc()
            results.append(res_entry)
        return results
class DefaultIntentExecutor:
    def __init__(self, label_center=None):
        self.label_center = label_center

    def execute(self, intent):
        if self.label_center is not None:
            self.label_center.enqueue(intent)
            return {"status": "queued", "name": intent.get("name")}

        # fallback（兼容旧逻辑）
        return {"status": "ignored", "name": intent.get("name")}


