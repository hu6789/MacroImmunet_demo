# runner_ein/masters/dc_master.py
"""
DCMaster: scan tissue for hotspots / antigen + debris, produce intents to:
 - recruit APCs (e.g., create 'recruit_apc' intent)
 - emit local cytokine deposits (write to Field_IL12 and optionally Field_CCL19)

Design notes / params:
 - il12_deposit_per_hotspot: base multiplier applied to raw score to compute deposit
 - deposit_cap: maximum deposit amount per intent (clamp)
 - recruit_prob_per_hotspot: base probability scaled by normalized score (0..1)
 - norm_score: value used to normalize raw score into 0..1 range (score/norm_score, clamped)
 - max_hotspots: maximum hotspots considered (top-K)
 - max_intents_per_tick: safety cap for number of intents produced each tick

Minimal adapter expectations:
 - space.fields is dict of 2D grids (list-of-list) for field names used
 - env.emit_event(name,payload) exists for observability (optional)
 - this master DOES NOT instantiate cells, it only emits intent dicts
"""
from typing import List, Tuple, Optional, Dict
from math import sqrt

class DCMaster:
    def __init__(self, space, env, params: Optional[Dict]=None):
        self.space = space
        self.env = env
        self.params = params or {}
        self.mode = "survey"

    def tick(self) -> List[dict]:
        """
        Perform a single master tick: find hotspots, build intents, and emit a
        master_tick event. Returns list of intent dicts.
        """
        hotspots = self._find_hotspots()
        intents: List[dict] = []

        # safety / tuning params
        max_intents = int(self.params.get("max_intents_per_tick", 6))
        norm = float(self.params.get("norm_score", 10.0)) or 10.0
        deposit_cap = float(self.params.get("deposit_cap", 6.0))
        base_deposit = float(self.params.get("il12_deposit_per_hotspot", 1.0))
        recruit_prob_base = float(self.params.get("recruit_prob_per_hotspot", 0.7))
        use_sqrt_scaling = bool(self.params.get("use_sqrt_scale_for_deposit", True))

        for coord, score in hotspots:
            if len(intents) >= max_intents:
                break

            # normalized score in 0..1 (approx)
            norm_score = min(1.0, max(0.0, score / norm))

            # compute deposit amount: optionally soften extreme scores with sqrt
            if use_sqrt_scaling:
                scaled_score = sqrt(score) if score > 0 else 0.0
                deposit_amount = base_deposit * scaled_score
            else:
                deposit_amount = base_deposit * score

            # clamp deposit
            deposit_amount = min(deposit_cap, deposit_amount)

            intents.append({
                "space": getattr(self.space, "id", None),
                "coord": coord,
                "action": "deposit_cytokine",
                "field": "Field_IL12",
                "amount": deposit_amount,
                "score": score
            })
            if len(intents) >= max_intents:
                break

            # recruit APC intent: scale probability by normalized score and clamp to [0,1]
            p = recruit_prob_base * norm_score
            p = max(0.0, min(1.0, p))

            intents.append({
                "space": getattr(self.space, "id", None),
                "coord": coord,
                "action": "recruit_apc",
                "cell_type": "DendriticCell_v1",
                "probability": p,
                "score": score
            })

        # observability event
        try:
            if hasattr(self.env, "emit_event") and callable(self.env.emit_event):
                self.env.emit_event("master_tick", {"master":"DCMaster", "n_intents": len(intents)})
        except Exception:
            # be robust: do not fail the master if emit_event raises
            pass

        return intents

    def _find_hotspots(self) -> List[Tuple[Tuple[int,int], float]]:
        """
        Find candidate coordinates by combining antigen + debris signals.
        Returns list of ((x,y), score) sorted descending by score, limited to top-K.
        """
        fd_ag = self.space.fields.get("Field_Antigen_Density")
        fd_debris = self.space.fields.get("Field_Cell_Debris")

        if fd_ag is None and fd_debris is None:
            return []

        # derive dims robustly
        h = 0
        w = 0
        if fd_ag:
            h = len(fd_ag)
            w = len(fd_ag[0]) if h > 0 else 0
        elif fd_debris:
            h = len(fd_debris)
            w = len(fd_debris[0]) if h > 0 else 0

        if h == 0 or w == 0:
            return []

        thr_ag = float(self.params.get("antigen_threshold", 0.5))
        thr_debris = float(self.params.get("debris_threshold", 0.1))
        found: List[Tuple[Tuple[int,int], float]] = []

        for y in range(h):
            for x in range(w):
                ag = 0.0
                db = 0.0
                try:
                    ag = float(fd_ag[y][x]) if fd_ag is not None else 0.0
                except Exception:
                    ag = 0.0
                try:
                    db = float(fd_debris[y][x]) if fd_debris is not None else 0.0
                except Exception:
                    db = 0.0

                # simple linear score combining antigen and debris (weight debris less)
                score = ag + 0.5 * db

                if ag >= thr_ag or db >= thr_debris:
                    found.append(((x, y), score))

        # sort descending and take top-K hotspots
        found.sort(key=lambda t: t[1], reverse=True)
        topk = int(self.params.get("max_hotspots", 4))
        return found[:topk]

