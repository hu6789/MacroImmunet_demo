# runner_ein/cells/simple_cells.py
from typing import Tuple
import random
import math
import traceback

class BaseCell:
    def __init__(self, cid: str, coord: Tuple[int,int]=(0,0), cell_type: str="Cell"):
        self.id = cid
        self.coord = tuple(coord)
        self.cell_type = cell_type
        self.state = "resting"   # restful, activated, infected, effector, dead
        self.meta = {}

    def tick(self, space, env):
        # override in subclasses
        return

    def distance_to(self, coord):
        x,y = self.coord
        tx,ty = coord
        return abs(x-tx) + abs(y-ty)

    def __repr__(self):
        return f"<{self.__class__.__name__} id={self.id} coord={self.coord} state={self.state}>"

# ---------- helpers ----------
def _neighborhood_coords(coord, w, h):
    x,y = coord
    out = []
    for dx,dy in ((0,0),(1,0),(-1,0),(0,1),(0,-1)):
        nx,ny = x+dx, y+dy
        if 0 <= nx < w and 0 <= ny < h:
            out.append((nx,ny))
    return out

def _best_neighbor_by_field(coord, field, w, h):
    """Return best neighbor coord (including self) and its value (4-neighbor + self)."""
    best = coord
    best_val = 0.0
    x0,y0 = coord
    for dx,dy in ((0,0),(1,0),(-1,0),(0,1),(0,-1)):
        nx,ny = x0+dx, y0+dy
        if 0 <= nx < w and 0 <= ny < h:
            try:
                v = float(field[ny][nx])
            except Exception:
                v = 0.0
            if v > best_val:
                best_val = v
                best = (nx,ny)
    return best, best_val

# ---------- cell classes ----------
class DendriticCell(BaseCell):
    def __init__(self, cid, coord):
        super().__init__(cid, coord, cell_type="DendriticCell")
        self.motility = 1

    def random_walk(self, space, env):
        x,y = self.coord
        w,h = space.w, space.h
        dirs = [(0,1),(0,-1),(1,0),(-1,0),(0,0)]
        dx,dy = random.choice(dirs)
        nx,ny = max(0,min(w-1,x+dx)), max(0,min(h-1,y+dy))
        if (nx,ny) != self.coord:
            self.coord = (nx,ny)
            try:
                env.emit_event("dc_moved", {"cell_id": self.id, "to": self.coord, "reason":"random"})
            except Exception:
                pass

    def move_towards(self, target, space, env, reason="gradient"):
        if target is None:
            return
        x,y = self.coord
        tx,ty = target
        dx = 0 if tx==x else (1 if tx>x else -1)
        dy = 0 if ty==y else (1 if ty>y else -1)
        # prefer larger axis
        if abs(tx-x) >= abs(ty-y):
            nx,ny = x+dx, y
        else:
            nx,ny = x, y+dy
        nx = max(0,min(space.w-1,nx)); ny = max(0,min(space.h-1,ny))
        if (nx,ny) != self.coord:
            self.coord = (nx,ny)
            try:
                env.emit_event("dc_moved", {"cell_id": self.id, "to": self.coord, "reason": reason})
            except Exception:
                pass

    def tick(self, space, env):
        try:
            w,h = space.w, space.h
            ag_field = space.fields.get("Field_Antigen_Density", [[0.0]*w for _ in range(h)])
            il12_field = space.fields.get("Field_IL12", [[0.0]*w for _ in range(h)])

            # find best neighbor by antigen and IL12 (local 4-neigh)
            best_ag_coord, best_ag_val = _best_neighbor_by_field(self.coord, ag_field, w, h)
            best_il_coord, best_il_val = _best_neighbor_by_field(self.coord, il12_field, w, h)

            # choose which gradient to follow
            if best_ag_val > 0 and best_ag_val >= best_il_val and best_ag_coord != self.coord:
                self.move_towards(best_ag_coord, space, env, reason="antigen_gradient")
            elif best_il_val > 0 and best_il_coord != self.coord:
                self.move_towards(best_il_coord, space, env, reason="il12_gradient")
            else:
                # small prob random walk
                if random.random() < 0.5:
                    self.random_walk(space, env)
        except Exception:
            try:
                env.emit_event("cell_tick_error", {"cell_id": getattr(self, "id", None), "trace": traceback.format_exc()})
            except Exception:
                pass

class CTL(BaseCell):
    def __init__(self, cid, coord):
        super().__init__(cid, coord, cell_type="CTL")
        self.killing_power = 1.0

    def try_kill(self, space, env):
        # search 3x3 for infected epithelial
        x,y = self.coord
        targets = []
        for yy in range(max(0, y-1), min(space.h, y+2)):
            for xx in range(max(0, x-1), min(space.w, x+2)):
                for c in list(space.cells.values()):
                    if getattr(c, "cell_type", "") == "EpithelialCell" and getattr(c, "coord", None) == (xx, yy):
                        if getattr(c, "state","") in ("infected","compromised") or getattr(c, "viral_load", 0.0) > 0:
                            targets.append(c)
        if not targets:
            return False

        target = random.choice(targets)
        # probabilistic kill scaled by viral load
        vl = float(getattr(target, "viral_load", 1.0))
        prob = min(0.95, 0.2 + 0.12 * math.log1p(vl))
        r = random.random()
        killed = False
        if r <= prob:
            # mark as dead and produce debris; remove cell from space
            target.state = "dead"
            tx,ty = getattr(target, "coord", (None, None))
            try:
                space.fields.setdefault("Field_Cell_Debris", [[0.0]*space.w for _ in range(space.h)])
                debris_amt = max(0.5, vl * 0.5)
                if tx is not None:
                    space.fields["Field_Cell_Debris"][ty][tx] += debris_amt
                # remove target from space
                try:
                    del space.cells[target.id]
                except Exception:
                    pass
                killed = True
                try:
                    env.emit_event("ctl_killed", {"ctl": self.id, "target": target.id, "coord": (tx,ty), "prob": prob})
                except Exception:
                    pass
            except Exception:
                try:
                    env.emit_event("cell_action_error", {"cell_id": getattr(self, "id", None), "trace": traceback.format_exc()})
                except Exception:
                    pass
        else:
            # attempted but failed
            try:
                env.emit_event("ctl_kill_failed", {"ctl": self.id, "target": getattr(target, "id", None), "coord": getattr(target, "coord", None), "prob": prob, "roll": r})
            except Exception:
                pass
        return killed

    def random_move_toward_antigen(self, space, env):
        # prefer local antigen gradient
        w,h = space.w, space.h
        ag_field = space.fields.get("Field_Antigen_Density", [[0.0]*w for _ in range(h)])
        best_coord, best_val = _best_neighbor_by_field(self.coord, ag_field, w, h)
        if best_coord != self.coord:
            self.coord = best_coord
            try:
                env.emit_event("ctl_moved", {"cell_id": self.id, "to": self.coord})
            except Exception:
                pass
        else:
            # random step
            x,y = self.coord
            dirs = [(0,1),(0,-1),(1,0),(-1,0),(0,0)]
            dx,dy = random.choice(dirs)
            nx,ny = max(0,min(space.w-1,x+dx)), max(0,min(space.h-1,y+dy))
            if (nx,ny) != self.coord:
                self.coord = (nx,ny)
                try:
                    env.emit_event("ctl_moved", {"cell_id": self.id, "to": self.coord, "reason":"random"})
                except Exception:
                    pass

    def tick(self, space, env):
        try:
            if not self.try_kill(space, env):
                # if no kill, move toward antigen or random walk
                self.random_move_toward_antigen(space, env)
        except Exception:
            try:
                env.emit_event("cell_tick_error", {"cell_id": getattr(self, "id", None), "trace": traceback.format_exc()})
            except Exception:
                pass

class EpithelialCell(BaseCell):
    def __init__(self, cid, coord):
        super().__init__(cid, coord, cell_type="EpithelialCell")
        self.state = "healthy"
        self.viral_load = 0.0
        # production fraction of viral_load released per tick (demo)
        self.prod_fraction = 0.1

    def become_infected(self, load, env=None):
        self.state = "infected"
        self.viral_load = float(load)
        try:
            if env and hasattr(env, "emit_event"):
                env.emit_event("epithelial_infected", {"cell_id": self.id, "coord": self.coord, "viral_load": self.viral_load})
        except Exception:
            pass

    def tick(self, space, env):
        try:
            if self.state in ("infected","compromised") or (self.viral_load and self.viral_load > 0):
                x,y = self.coord
                space.fields.setdefault("Field_Antigen_Density", [[0.0]*space.w for _ in range(space.h)])
                # amount to release (capped)
                amount = min(5.0, float(self.viral_load or 1.0) * self.prod_fraction)
                if amount > 0:
                    try:
                        space.fields["Field_Antigen_Density"][y][x] += amount
                        env.emit_event("epi_released_antigen", {"cell_id": self.id, "coord": (x,y), "amount": amount})
                    except Exception:
                        pass
                # simple growth/decay of viral load
                self.viral_load *= 1.02
                # optional: small natural decay
                self.viral_load *= 0.995
                # lysis when viral load huge
                if self.viral_load > 200.0:
                    try:
                        env.emit_event("epithelial_lysis", {"cell_id": self.id, "coord": self.coord})
                    except Exception:
                        pass
                    try:
                        # add debris and remove cell
                        space.fields.setdefault("Field_Cell_Debris", [[0.0]*space.w for _ in range(space.h)])
                        tx,ty = self.coord
                        space.fields["Field_Cell_Debris"][ty][tx] += max(1.0, self.viral_load * 0.5)
                    except Exception:
                        pass
                    try:
                        del space.cells[self.id]
                    except Exception:
                        pass
        except Exception:
            try:
                env.emit_event("cell_tick_error", {"cell_id": getattr(self, "id", None), "trace": traceback.format_exc()})
            except Exception:
                pass

