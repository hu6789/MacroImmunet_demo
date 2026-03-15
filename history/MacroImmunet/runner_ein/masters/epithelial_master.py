# runner_ein/masters/epithelial_master.py
"""
EpithelialMaster: scan Field_Antigen_Density, choose hotspots, emit intents
(intent: attempt_infect) for orchestrator to handle.

Minimal, dependency-light: expects `space` to have:
 - space.id (str)
 - space.fields: dict mapping field name -> 2D list-like (indexed [y][x])
 - space.w, space.h (ints) or len(field) usage
`env` should provide emit_event(name,payload) (optional).

Configurable params (keys in params dict):
 - scan_threshold: float (antigen cell-level threshold to consider)
 - max_hotspots: int (top-K hotspots to return)
 - infection_intent_strength: float (scale factor mapping score->strength)
 - neighborhood_radius: int (radius for scoring; default 1 => 3x3)
 - name: optional master name for events
"""
from typing import List, Tuple, Any


class EpithelialMaster:
    def __init__(self, space: Any, env: Any, params: dict = None):
        self.space = space
        self.env = env
        self.params = params or {}
        self.mode = "healthy"
        # defaults
        self.scan_threshold = float(self.params.get("scan_threshold", 0.1))
        self.max_hotspots = int(self.params.get("max_hotspots", 3))
        self.strength_scale = float(self.params.get("infection_intent_strength", 0.1))
        self.neighborhood_radius = int(self.params.get("neighborhood_radius", 1))
        self.name = self.params.get("name", "EpithelialMaster")

    def tick(self) -> List[dict]:
        """
        One master tick: scan antigen field, compute scores, decide top hotspots,
        return list of intents (attempt_infect).
        """
        try:
            items = self._scan()
            scored = [(coord, self._score(coord)) for coord in items]
            intents = self._decide(scored)
            # emit summary event for debugging/observability
            try:
                if hasattr(self.env, "emit_event"):
                    self.env.emit_event("master_tick", {"master": self.name, "n_intents": len(intents)})
            except Exception:
                pass
            return intents
        except Exception:
            # don't let master crash calling orchestrator; emit a lightweight error event
            try:
                if hasattr(self.env, "emit_event"):
                    import traceback
                    self.env.emit_event("epithelial_master_error", {"master": self.name, "trace": traceback.format_exc()})
            except Exception:
                pass
            return []

    def _scan(self) -> List[Tuple[int, int]]:
        """
        Return a list of candidate coords for scoring.
        Coarse filter: cell value > scan_threshold.
        """
        fd = self.space.fields.get("Field_Antigen_Density")
        if not fd:
            return []
        h = len(fd)
        w = len(fd[0]) if h else 0
        candidates: List[Tuple[int, int]] = []
        thr = float(self.scan_threshold)
        for y in range(h):
            for x in range(w):
                try:
                    v = fd[y][x]
                    if v is None:
                        continue
                    if float(v) > thr:
                        candidates.append((x, y))
                except Exception:
                    # ignore malformed entries
                    continue
        return candidates

    def _score(self, coord: Tuple[int, int]) -> float:
        """
        Score a coordinate by summing antigen in the neighborhood (radius configurable).
        """
        fd = self.space.fields.get("Field_Antigen_Density")
        if not fd:
            return 0.0
        x, y = coord
        h = len(fd)
        w = len(fd[0]) if h else 0
        r = max(0, int(self.neighborhood_radius))
        s = 0.0
        for yy in range(max(0, y - r), min(h, y + r + 1)):
            for xx in range(max(0, x - r), min(w, x + r + 1)):
                try:
                    s += float(fd[yy][xx])
                except Exception:
                    pass
        return float(s)

    def _decide(self, scored_items: List[Tuple[Tuple[int, int], float]]) -> List[dict]:
        """
        From scored items pick top-k and produce attempt_infect intents.
        Each intent includes:
         - space, coord, action, strength, score, source
        """
        if not scored_items:
            return []
        # sort descending by score
        scored_items.sort(key=lambda t: t[1], reverse=True)
        topk = max(0, int(self.max_hotspots))
        out: List[dict] = []
        strength_scale = float(self.strength_scale)
        for (coord, score) in scored_items[:topk]:
            if score <= 0:
                continue
            intent = {
                "space": getattr(self.space, "id", None),
                "coord": coord,
                "action": "attempt_infect",
                "strength": float(score) * strength_scale,
                "score": float(score),
                "source": "epithelial",
                "master": self.name,
            }
            out.append(intent)
            # emit a small hotspot event for observability
            try:
                if hasattr(self.env, "emit_event"):
                    self.env.emit_event("hotspot_by_epithelium", {"coord": coord, "score": float(score), "master": self.name})
            except Exception:
                pass
        return out

