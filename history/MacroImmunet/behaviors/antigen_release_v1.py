"""
Legacy wrapper for antigen_release_v1 that adapts the real implementation
to the framework's expected action/event names.

Behavior adapter responsibilities:
 - delegate to behaviors_impl.antigen_release.handle_release_on_death if present
 - accept constructor params (yaml params)
 - normalize/translate returned actions:
     * rename action name 'antigen_release' -> 'antigen_released'
     * if implementation returns no explicit antigen_released action, synthesize one:
         {'name': 'antigen_released', 'payload': {'cell_id': cell.id, 'yield': release_yield}}
   release_yield computed as: min(params['release_burst_yield'], cell.meta.get('viral_load',0)*0.8)
 - emit a diagnostic event 'antigen_release_no_impl' if no impl found
"""
try:
    from behaviors_impl.antigen_release import handle_release_on_death
except Exception:
    handle_release_on_death = None

class AntigenReleaseBehavior:
    def __init__(self, **init_params):
        self._init_params = dict(init_params or {})

    def _compute_release_yield(self, cell, params):
        # safe read of cell internal load
        try:
            internal = float(getattr(cell, "viral_load", None) or (getattr(cell, "meta", {}) or {}).get("viral_load", 0.0))
        except Exception:
            internal = 0.0
        try:
            burst = float(params.get("release_burst_yield", 0))
        except Exception:
            burst = 0.0
        return int(min(burst, internal * 0.8))

    def execute(self, cell, env, params=None, payload=None, **kw):
        merged = dict(self._init_params)
        if isinstance(params, dict):
            merged.update(params)

        actions = []
        # call implementation defensively
        if handle_release_on_death is not None:
            try:
                res = handle_release_on_death(cell, env, params=merged, payload=payload, **kw)
            except TypeError:
                # try older signatures
                try:
                    res = handle_release_on_death(cell, env, merged)
                except Exception:
                    try:
                        res = handle_release_on_death(cell, env)
                    except Exception:
                        res = []
            except Exception:
                res = []

            # normalize result to list of actions
            if res is None:
                res = []
            if isinstance(res, dict):
                res = [res]
            if not isinstance(res, (list, tuple)):
                res = []

            # translate/normalize action names and collect
            seen_released = False
            for a in res:
                if not isinstance(a, dict):
                    continue
                name = a.get("name")
                # translate legacy name -> expected name
                if name == "antigen_release":
                    a["name"] = "antigen_released"
                    seen_released = True
                elif name == "antigen_released":
                    seen_released = True
                actions.append(a)

            # if implementation didn't produce antigen_released action, synthesize one
            if not seen_released:
                rel_y = self._compute_release_yield(cell, merged)
                synth = {"name": "antigen_released", "payload": {"cell_id": getattr(cell, "id", None), "yield": rel_y}}
                actions.append(synth)

            return actions

        # no implementation: emit diag event and synthesize action
        try:
            if hasattr(env, "emit_event"):
                env.emit_event("antigen_release_no_impl", {
                    "cell_id": getattr(cell, "id", None),
                    "reason": "no_impl",
                    "tick": getattr(env, "tick", None)
                })
        except Exception:
            pass

        rel_y = self._compute_release_yield(cell, merged)
        return [{"name": "antigen_released", "payload": {"cell_id": getattr(cell, "id", None), "yield": rel_y}}]
