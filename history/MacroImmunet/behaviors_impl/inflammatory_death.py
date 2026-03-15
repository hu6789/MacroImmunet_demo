"""
behaviors_impl.inflammatory_death
Implementation for inflammatory_death_v1

Exports:
 - inflammatory_death_v1(cell, env, params=None, payload=None, rng=None, **kw)
 - InflammatoryDeathBehavior adapter class
 - inflammatory_death(...) helper
"""
import math
from typing import Any, Dict, Optional

def _get_cell_coord(cell):
    # try common coordinate attributes
    for attr in ("coord", "position", "pos"):
        val = getattr(cell, attr, None)
        if val is not None:
            return val
    # fallback: None
    return None

def _read_field(env, field_name, coord):
    # try flexible signatures: env.read_field(field, coord) or env.read_field(coord, field)
    try:
        if hasattr(env, "read_field"):
            try:
                return env.read_field(field_name, coord)
            except TypeError:
                try:
                    return env.read_field(coord, field_name)
                except Exception:
                    return None
    except Exception:
        return None
    return None

def _choose_weighted(rng, weights):
    # weights: dict->value. returns key chosen according to weights.
    total = 0.0
    for v in weights.values():
        try:
            total += float(v)
        except Exception:
            pass
    if total <= 0:
        # fallback equal weights
        keys = list(weights.keys())
        if not keys:
            return None
        idx = int(rng.random() * len(keys)) if hasattr(rng, "random") else 0
        return keys[idx % len(keys)]
    # draw
    pick = (rng.random() if hasattr(rng, "random") else 0.0) * total
    acc = 0.0
    for k, v in weights.items():
        try:
            acc += float(v)
        except Exception:
            continue
        if pick <= acc:
            return k
    # fallback last
    return list(weights.keys())[-1] if weights else None

def inflammatory_death_v1(cell, env, params=None, payload=None, rng=None, **kw):
    params = params or {}
    # resolve weights & thresholds dictionaries
    thresholds = params.get("thresholds") or {}
    weights = params.get("weights") or {}
    death_prob_at_threshold = float(params.get("death_prob_at_threshold", 0.7) or 0.7)
    integrate_window_ticks = float(params.get("integrate_window_ticks", 6) or 6)
    max_death_prob = float(params.get("max_death_prob", 0.95) or 0.95)
    death_mode_strategy = params.get("death_mode_strategy", "random")
    death_mode_weights = params.get("death_mode_weights", {"lysis": 0.5, "apoptosis": 0.5}) or {"lysis": 0.5, "apoptosis": 0.5}

    # RNG fallback
    if rng is None:
        try:
            import random as _r
            rng = _r
        except Exception:
            rng = None

    coord = _get_cell_coord(cell)
    # aggregate per-field values
    aggregated_signal = 0.0
    field_vals = {}
    for field, th in (thresholds.items() if isinstance(thresholds, dict) else []):
        val = _read_field(env, field, coord)
        try:
            v = float(val or 0.0)
        except Exception:
            v = 0.0
        field_vals[field] = v
        w = float((weights.get(field) if isinstance(weights, dict) else None) or 1.0)
        aggregated_signal += w * v

    # If thresholds dict empty, try reading known fields param or input naming
    if not field_vals:
        # try a few common field names
        for field in ("Field_DAMP", "Field_TNF", "Field_IL6"):
            val = _read_field(env, field, coord)
            try:
                v = float(val or 0.0)
            except Exception:
                v = 0.0
            field_vals[field] = v
            aggregated_signal += float((weights.get(field) if isinstance(weights, dict) else 1.0) or 1.0) * v

    # compute exponential decay integrator
    try:
        decay = math.exp(-1.0 / max(1.0, integrate_window_ticks))
    except Exception:
        decay = 0.9
    try:
        prev_integral = float(getattr(cell, "stress_integral", 0.0) or 0.0)
    except Exception:
        prev_integral = 0.0
    stress_integral = prev_integral * decay + aggregated_signal
    try:
        cell.stress_integral = stress_integral
    except Exception:
        pass

    # compute effective threshold: weighted mean if thresholds provided
    eff_threshold = None
    try:
        if isinstance(thresholds, dict) and thresholds:
            num = 0.0
            den = 0.0
            for f, t in thresholds.items():
                try:
                    w = float((weights.get(f) if isinstance(weights, dict) else 1.0) or 1.0)
                    num += w * float(t)
                    den += w
                except Exception:
                    continue
            if den > 0:
                eff_threshold = num / den
    except Exception:
        eff_threshold = None
    if eff_threshold is None:
        # fallback: mean of nonzero fields or 1.0
        vals = [v for v in field_vals.values() if v is not None]
        eff_threshold = (sum(vals) / max(1, len(vals))) if vals else 1.0

    # compute p
    try:
        p = death_prob_at_threshold * (stress_integral / (eff_threshold * 2.0))
    except Exception:
        p = 0.0
    try:
        p = max(0.0, min(float(p or 0.0), float(max_death_prob or 0.95)))
    except Exception:
        p = min(p, 0.95)

    draw = (rng.random() if hasattr(rng, "random") else 0.0)
    did_die = False
    chosen_mode = None

    if draw < p:
        # choose death mode
        if death_mode_strategy == "apoptosis_preferred":
            chosen_mode = "apoptosis"
        elif death_mode_strategy == "lysis_preferred":
            chosen_mode = "lysis"
        elif death_mode_strategy == "weighted":
            chosen_mode = _choose_weighted(rng, death_mode_weights)
        else:  # random or anything else
            chosen_mode = _choose_weighted(rng, death_mode_weights)

        if chosen_mode:
            # emit appropriate intent if engine supports emit_intent
            payload_out = {
                "cell_id": getattr(cell, "id", None),
                "p": p,
                "stress_integral": stress_integral,
                "tick": getattr(env, "tick", None),
                "cause": "inflammatory_integrator",
            }
            try:
                if hasattr(env, "emit_intent"):
                    env.emit_intent(chosen_mode, payload_out)
                elif hasattr(env, "emit_event"):
                    env.emit_event(chosen_mode, payload_out)
            except Exception:
                # swallow engine emission errors
                pass
            did_die = True

    # return actions for compatibility
    actions = []
    if did_die and chosen_mode:
        actions.append({"name": chosen_mode, "payload": {"p": p, "stress_integral": stress_integral}})
    return actions

class InflammatoryDeathBehavior:
    def __init__(self, **kwargs):
        self.params = kwargs or {}

    def execute(self, cell, env, params=None, payload=None, rng=None, **kw):
        merged = {}
        merged.update(self.params or {})
        if isinstance(params, dict):
            merged.update(params)
        return inflammatory_death_v1(cell, env, params=merged, payload=payload, rng=rng, **kw)

def inflammatory_death(cell, env, params=None, payload=None, rng=None, **kw):
    return inflammatory_death_v1(cell, env, params=params, payload=payload, rng=rng, **kw)
