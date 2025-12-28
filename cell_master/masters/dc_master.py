# cell_master/masters/dc_master.py
# -*- coding: utf-8 -*-
from typing import List, Dict, Any, Optional, Tuple
from cell_master.intents import Intent
from cell_master.gene_gate import GeneGate
import copy
import uuid
import time
import math
import random

Coord = Tuple[float, float]


def _clamp_coord(c: Coord):
    # small helper to coerce numeric coords
    try:
        return (float(c[0]), float(c[1]))
    except Exception:
        return (0.0, 0.0)


def _random_step(origin: Coord, step_size: float, rng: random.Random):
    # produce a new coord via random direction step of magnitude up to step_size
    theta = rng.random() * 2.0 * math.pi
    r = rng.random() * float(step_size)
    return (origin[0] + r * math.cos(theta), origin[1] + r * math.sin(theta))


class DCMaster:
    """
    Minimal dendritic cell master.

    Responsibilities (minimal):
      - trigger phagocytosis intent when label.meta has captured_antigens
      - generate pMHC_presented intents for processed antigens
      - emit movement intents:
          * if presented something -> directed move to LN or hotspot
          * otherwise -> random walk (within step_size)
    Configurable via `config` dict and `node_meta`:
      - config keys: mhc_type (default "MHC_I"), process_limit (int), default_ln_coord (Coord),
                     random_step_size (float)
      - node_meta may override: process_limit, hotspot_coord, target ("LN"|'hotspot'|coord tuple),
                                 step_size
    """
    def __init__(
        self,
        space: Any = None,
        registry: Any = None,
        feedback: Any = None,
        gene_gate: Optional[GeneGate] = None,
        config: Optional[Dict[str, Any]] = None,
        rng: Optional[random.Random] = None,
    ):
        self.space = space
        self.registry = registry
        self.feedback = feedback
        self.gene_gate = gene_gate or GeneGate({})
        self.config = dict(config or {})
        # default capture radius (used by compatibility shim)
        if "capture_radius" not in self.config:
            self.config["capture_radius"] = 1.5
        self.rng = rng or random.Random()

    def _make_pmhc(self, antigen: Dict[str, Any], presenter_id: str) -> Dict[str, Any]:
        pmhc_id = f"pm_{uuid.uuid4().hex[:8]}"
        peptide = None
        if isinstance(antigen, dict):
            eps = antigen.get("epitopes") or antigen.get("epitope") or []
            if eps and isinstance(eps, list):
                first = eps[0]
                peptide = first.get("seq") if isinstance(first, dict) else str(first)
            else:
                peptide = antigen.get("sequence") or antigen.get("seq")
        peptide = peptide or "UNKNOWN"
        return {
            "pMHC_id": pmhc_id,
            "peptide_id": peptide,
            "mhc_type": self.config.get("mhc_type", "MHC_I"),
            "presenter": presenter_id,
            "ts": time.time(),
        }

    def handle_label(self, region_id: str, label: Dict[str, Any], node_meta: Optional[Dict[str, Any]] = None, tick: int = 0) -> List[Intent]:
        """
        Main entrypoint for per-label handling.
        Returns list of Intent instances (possibly empty).
        """
        node_meta = node_meta or {}
        intents: List[Intent] = []

        # node-level gate
        ok, details = self.gene_gate.allow({}, node_meta)
        if not ok:
            return []

        meta = dict(label.get("meta") or {})
        captured = meta.get("captured_antigens") or meta.get("antigens") or []

        # respect process limit
        limit = int(node_meta.get("process_limit", self.config.get("process_limit", 1)))

        presented_count = 0
        processed = []

        # If antigens present -> phagocytose intent + present pMHCs
        if captured:
            # phagocytose intent: signal that this DC will internalize antigens
            phago_payload = {"cell_id": label.get("id"), "source": "captured", "count": min(len(captured), limit)}
            intents.append(Intent(name="phagocytose", payload=phago_payload, src_cell_id=label.get("id"), coord=label.get("coord")))

            # process up to limit antigens and create pMHC presented intents
            for antigen in captured[:limit]:
                pmhc = self._make_pmhc(antigen, presenter_id=label.get("id") or label.get("name"))
                payload = {"presenter": label.get("id"), "pMHC": pmhc}
                intents.append(Intent(name="pMHC_presented", payload=payload, src_cell_id=label.get("id"), coord=label.get("coord")))
                presented_count += 1
                processed.append(antigen)

        # Movement logic:
        # - If we presented anything -> directed move toward LN or hotspot (prefer node_meta hotspot)
        # - Else -> random walk step
        curr_coord = label.get("coord") or label.get("position") or (0.0, 0.0)
        try:
            curr_coord = _clamp_coord(curr_coord)
        except Exception:
            curr_coord = (0.0, 0.0)

        if presented_count > 0:
            # directed target selection: node_meta overrides config
            hotspot = node_meta.get("hotspot_coord")
            explicit_target = node_meta.get("target")  # could be "LN", "hotspot" or a coord tuple
            ln_coord = tuple(node_meta.get("ln_coord", self.config.get("default_ln_coord", (100.0, 100.0))))
            target_coord = None

            if explicit_target:
                if isinstance(explicit_target, (list, tuple)) and len(explicit_target) >= 2:
                    target_coord = _clamp_coord((explicit_target[0], explicit_target[1]))
                elif isinstance(explicit_target, str) and explicit_target.upper() == "LN":
                    target_coord = _clamp_coord(ln_coord)
                elif explicit_target == "hotspot" and hotspot:
                    target_coord = _clamp_coord(hotspot)
            if target_coord is None:
                if hotspot:
                    target_coord = _clamp_coord(hotspot)
                else:
                    target_coord = _clamp_coord(ln_coord)

            move_payload = {"from": curr_coord, "to": target_coord, "mode": "directed", "reason": "presented_antigen"}
            intents.append(Intent(name="move_to", payload=move_payload, src_cell_id=label.get("id"), coord=curr_coord))
        else:
            # random walk
            step_size = float(node_meta.get("step_size", self.config.get("random_step_size", 1.0)))
            new_coord = _random_step(curr_coord, step_size, rng=self.rng)
            move_payload = {"from": curr_coord, "to": _clamp_coord(new_coord), "mode": "random", "reason": "patrol"}
            intents.append(Intent(name="move_to", payload=move_payload, src_cell_id=label.get("id"), coord=curr_coord))

        return intents


# --- compatibility shim: provide .step(...) if underlying class uses handle_label(...) ---
def _dc_step_compat(self, coord, summary, cell_meta, rng=None, *args, **kwargs):
    """
    Compatibility wrapper that accepts the demo-style call:
      step(coord, summary, cell_meta, rng)
    and attempts to translate `summary` into the label/meta expected by handle_label.

    Behavior:
     - If self.handle_label exists, prefer calling it.
     - If summary contains 'agents', gather nearby agents as 'captured_antigens'
       (simple Euclidean check against coord, radius configurable as self.config['capture_radius']).
     - Fallback to trying other common callables (process/run/act/tick/handle/step).
    """
    tick = kwargs.get("tick", 0)

    # Prefer calling handle_label if available
    if hasattr(self, "handle_label") and callable(self.handle_label):
        # If summary already resembles a label dict, try to call directly
        try:
            if isinstance(summary, dict) and summary.get("meta") and summary.get("id"):
                try:
                    return self.handle_label(region_id=summary.get("id"), label=summary, node_meta=cell_meta or {}, tick=tick)
                except TypeError:
                    return self.handle_label(summary, cell_meta or {}, tick)
        except Exception:
            pass

        # If summary has 'agents', attempt to convert nearby agents into captured_antigens
        try:
            agents = (summary or {}).get("agents", []) or []
            if agents:
                radius = float(getattr(self, "config", {}).get("capture_radius", 1.5))
                captured = []
                for a in agents:
                    try:
                        # agent may be dict-like or object-like
                        if isinstance(a, dict):
                            acoord = a.get("coord")
                        else:
                            acoord = getattr(a, "coord", None)
                        if acoord is None:
                            continue
                        dx = float(acoord[0]) - float(coord[0])
                        dy = float(acoord[1]) - float(coord[1])
                        if dx * dx + dy * dy <= radius * radius:
                            # normalize antigen representation: prefer 'proto' dict or use mass/type
                            antigen = {}
                            if isinstance(a, dict):
                                antigen = a.get("proto") or {"mass": a.get("mass", 1.0)}
                            else:
                                antigen = getattr(a, "proto", {"mass": getattr(a, "mass", 1.0)})
                            # ensure it's a plain dict
                            if antigen is None:
                                antigen = {"mass": 1.0}
                            captured.append(dict(antigen))
                    except Exception:
                        # ignore malformed agent entries
                        continue

                if captured:
                    label = {"id": kwargs.get("label_id", "dc_auto"), "coord": coord, "meta": {"captured_antigens": captured}}
                    try:
                        return self.handle_label(region_id=label.get("id"), label=label, node_meta=cell_meta or {}, tick=tick)
                    except TypeError:
                        return self.handle_label(label, cell_meta or {}, tick)
        except Exception:
            pass

        # final best-effort call with empty meta
        try:
            return self.handle_label(region_id=str(coord), label={"id": str(coord), "coord": coord, "meta": {}}, node_meta=cell_meta or {}, tick=tick)
        except Exception:
            pass

    # fallback: try other common method names
    for name in ("process", "run", "act", "tick", "handle", "step"):
        fn = getattr(self, name, None)
        if callable(fn):
            try:
                # try a few calling conventions
                try:
                    return fn(coord, summary, cell_meta, rng)
                except TypeError:
                    try:
                        return fn(coord=coord, summary=summary, cell_meta=cell_meta, rng=rng)
                    except Exception:
                        return fn()
            except Exception:
                continue

    # nothing we can do — return empty list
    return []


# bind shim to class for compatibility
try:
    DCMaster.step = _dc_step_compat
except Exception:
    pass

