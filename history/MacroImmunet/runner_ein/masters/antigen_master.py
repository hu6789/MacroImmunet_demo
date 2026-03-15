# runner_ein/masters/antigen_master.py
"""
AntigenMaster

- seed / continuous influx
- local replication (multiplicative, capped)
- diffusion to 4-neighbors (discrete)
- decay
- emits hotspot_detected events
- returns deposit intents; optionally returns attempt_infect intents if emit_attempts=True
"""
from typing import Any, Dict, List, Optional
import random
import traceback

class AntigenMaster:
    def __init__(self, space: Any, env: Any, params: Optional[Dict]=None):
        self.space = space
        self.env = env
        self.params = params or {}
        self.name = self.params.get("name", "AntigenMaster")
        # behavior params
        self.seeds = list(self.params.get("seeds", []))
        self.influx_rate = float(self.params.get("continuous_influx_rate", 0.0))
        self.replication_rate = float(self.params.get("replication_rate", 0.0))
        self.replication_cap = float(self.params.get("replication_cap", 100.0))
        self.diffusion_rate = float(self.params.get("diffusion_rate", 0.2))
        self.decay = float(self.params.get("decay", 0.995))
        self.attempt_threshold = float(self.params.get("attempt_infect_threshold", 0.5))
        self.attempt_strength_scale = float(self.params.get("attempt_infect_strength_scale", 1.0))
        self.max_attempts = int(self.params.get("max_attempts_per_tick", 10))
        # NEW: whether to emit attempt_infect intents (default False)
        self.emit_attempts = bool(self.params.get("emit_attempts", False))

        # ensure field exists
        try:
            if getattr(self.space, "fields", None) is None:
                self.space.fields = {}
            self.space.fields.setdefault("Field_Antigen_Density", [[0.0]*self.space.w for _ in range(self.space.h)])
        except Exception:
            pass

    def _emit(self, name: str, payload: Dict):
        try:
            if hasattr(self.env, "emit_event"):
                self.env.emit_event(name, payload)
        except Exception:
            pass

    def _apply_seeds(self, tick: int) -> List[Dict]:
        intents = []
        try:
            for s in self.seeds:
                if int(s.get("tick", 0)) == int(tick):
                    coord = tuple(s.get("coord"))
                    amt = float(s.get("amount", 0.0))
                    x,y = coord
                    try:
                        self.space.fields.setdefault("Field_Antigen_Density", [[0.0]*self.space.w for _ in range(self.space.h)])
                        self.space.fields["Field_Antigen_Density"][y][x] += amt
                    except Exception:
                        pass
                    intents.append({"action":"deposit","field":"Field_Antigen_Density","coord":coord,"amount":amt, "source":"antigen"})
                    self._emit("antigen_seeded", {"coord":coord, "amount": amt, "tick": tick})
            # continuous influx
            if self.influx_rate > 0:
                targets = [tuple(s.get("coord")) for s in self.seeds if s.get("coord")]
                if not targets:
                    targets = [(random.randint(0,self.space.w-1), random.randint(0,self.space.h-1)) for _ in range(3)]
                per = float(self.influx_rate) / max(1, len(targets))
                for coord in targets:
                    x,y = coord
                    try:
                        self.space.fields.setdefault("Field_Antigen_Density", [[0.0]*self.space.w for _ in range(self.space.h)])
                        self.space.fields["Field_Antigen_Density"][y][x] += per
                    except Exception:
                        pass
                    intents.append({"action":"deposit","field":"Field_Antigen_Density","coord":coord,"amount":per, "source":"antigen"})
                    self._emit("antigen_influx", {"coord":coord, "amount": per, "tick": tick})
        except Exception as e:
            self._emit("antigen_master_error", {"error": str(e), "trace": traceback.format_exc()})
        return intents

    def _replicate(self):
        try:
            fld = self.space.fields.get("Field_Antigen_Density")
            if not fld:
                return
            h = len(fld)
            w = len(fld[0]) if h>0 else 0
            for y in range(h):
                for x in range(w):
                    v = float(fld[y][x] or 0.0)
                    if v <= 0:
                        continue
                    add = v * self.replication_rate
                    newv = min(self.replication_cap, v + add)
                    fld[y][x] = newv
        except Exception as e:
            self._emit("antigen_master_error", {"error": str(e), "trace": traceback.format_exc()})

    def _diffuse_and_decay(self):
        try:
            fld = self.space.fields.get("Field_Antigen_Density")
            if not fld:
                return
            h = len(fld)
            if h == 0:
                return
            w = len(fld[0])
            new = [[0.0]*w for _ in range(h)]
            rate = max(0.0, min(1.0, float(self.diffusion_rate)))
            for y in range(h):
                for x in range(w):
                    v = float(fld[y][x] or 0.0)
                    out = v * rate
                    keep = v - out
                    new[y][x] += keep
                    if out > 0:
                        share = out / 4.0
                        if x-1 >= 0:
                            new[y][x-1] += share
                        if x+1 < w:
                            new[y][x+1] += share
                        if y-1 >= 0:
                            new[y-1][x] += share
                        if y+1 < h:
                            new[y+1][x] += share
            dec = float(self.decay)
            for y in range(h):
                for x in range(w):
                    new[y][x] *= dec
            self.space.fields["Field_Antigen_Density"] = new
        except Exception as e:
            self._emit("antigen_master_error", {"error": str(e), "trace": traceback.format_exc()})

    def _emit_hotspot_intents(self) -> List[Dict]:
        intents: List[Dict] = []
        try:
            fld = self.space.fields.get("Field_Antigen_Density")
            if not fld:
                return intents
            h = len(fld)
            w = len(fld[0]) if h>0 else 0
            coords = []
            for y in range(h):
                for x in range(w):
                    v = float(fld[y][x] or 0.0)
                    if v >= self.attempt_threshold:
                        coords.append(((x,y), v))
            coords.sort(key=lambda p: p[1], reverse=True)
            for (x,y), v in coords[:self.max_attempts]:
                self._emit("hotspot_detected", {"coord":(x,y), "antigen": v})
                if self.emit_attempts:
                    strength = v * self.attempt_strength_scale
                    score = max(0.0, v * 10.0)
                    intents.append({"action":"attempt_infect","coord":(x,y),"strength": strength, "score": score, "source":"antigen"})
        except Exception as e:
            self._emit("antigen_master_error", {"error": str(e), "trace": traceback.format_exc()})
        return intents

    def tick(self) -> List[Dict]:
        intents: List[Dict] = []
        tick = getattr(self.env, "tick", 0)
        intents.extend(self._apply_seeds(tick))
        if self.replication_rate > 0.0:
            self._replicate()
        if self.diffusion_rate > 0.0 or self.decay < 1.0:
            self._diffuse_and_decay()
        intents.extend(self._emit_hotspot_intents())
        try:
            total = 0.0
            fld = self.space.fields.get("Field_Antigen_Density")
            if fld:
                for row in fld:
                    for v in row:
                        try:
                            total += float(v)
                        except Exception:
                            pass
            self._emit("master_tick", {"master": self.name, "n_intents": len(intents), "antigen_total": total})
        except Exception:
            pass
        return intents

