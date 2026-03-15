#!/usr/bin/env python3
# run_scenario.py  （改进版 — spawn 真实 epi，回退 epi 实现，兼容 prob/probability）
import sys
import traceback
import random

from runner_ein.loader import load_scenario
from runner_ein.percell.scheduler import Scheduler
from runner_ein.orchestrator_demo import merge_attempt_infects  # reuse helper if present

# Try to import real epithelial cell class; otherwise provide a minimal fallback.
try:
    from runner_ein.cells.epithelial import EpithelialCell as RealEpithelialCell
except Exception:
    RealEpithelialCell = None

# Try real DC and CTL classes if available for spawn events
try:
    from runner_ein.cells.simple_cells import DendriticCell
except Exception:
    DendriticCell = None

try:
    from runner_ein.cells.simple_cells import CTL
except Exception:
    CTL = None

class FallbackInfectedEpi:
    """Minimal epithelial cell fallback:
    - cell_type = 'EpithelialCell'
    - has coord, id, infected flag and infection_load
    - tick(space, env) will release antigen immediately and emit lysis (demo)
    """
    cell_type = "EpithelialCell"
    def __init__(self, cid, coord, infected=False, infection_load=0.0):
        self.id = cid
        self.coord = tuple(coord)
        self.infected = infected
        self.infection_load = float(infection_load or 0.0)
        self._lysed = False

    def tick(self, space, env):
        # simple demo: if infected and not lysed, release antigen and lyse
        if self.infected and (not self._lysed):
            x,y = self.coord
            # deposit a burst of antigen (make configurable if needed)
            amt = 5.0
            space.fields.setdefault("Field_Antigen_Density", [[0.0]*space.w for _ in range(space.h)])
            space.fields["Field_Antigen_Density"][y][x] += amt
            env.emit_event("epi_released_antigen", {"cell_id": self.id, "coord": self.coord, "amount": amt})
            env.emit_event("epithelial_lysis", {"cell_id": self.id, "coord": self.coord})
            # mark removed: remove from space in run loop after tick if desired
            self._lysed = True

def spawn_epithelial(space, env, cid, coord, infected=False, infection_load=0.0):
    """Create an epithelial cell instance and register it in space.cells.
       Prefer the real class; otherwise use fallback.
    """
    if RealEpithelialCell:
        try:
            # try constructor signatures: (id, coord, **kwargs) — tolerant
            epi = RealEpithelialCell(cid, tuple(coord))
            # try to set infection attributes if available
            try:
                setattr(epi, "infected", infected)
                setattr(epi, "infection_load", float(infection_load))
            except Exception:
                pass
        except Exception:
            epi = FallbackInfectedEpi(cid, coord, infected=infected, infection_load=infection_load)
    else:
        epi = FallbackInfectedEpi(cid, coord, infected=infected, infection_load=infection_load)

    # register
    space.cells[cid] = epi
    if infected:
        env.emit_event("epi_spawn_infected", {"cell_id": cid, "coord": tuple(coord), "load": float(infection_load)})
    else:
        env.emit_event("epi_spawned", {"cell_id": cid, "coord": tuple(coord)})
    return epi

def run(path, n_ticks=10):
    space, env, masters, cfg = load_scenario(path)
    scheduler = Scheduler(env=env)
    infection_scale = float(cfg.get("infection_load_scale", 200.0)) if cfg else 200.0
    debug_spawn_ctl = bool(cfg.get("debug_spawn_ctl", False)) if cfg else False

    # identify antigen master if present
    antigen_master = None
    other_masters = []
    for m in masters:
        if m.__class__.__name__.lower().startswith("antigen"):
            antigen_master = m
        else:
            other_masters.append(m)

    print(f"Scenario loaded: {path}, masters: {[m.__class__.__name__ for m in masters]}")
    for tick in range(n_ticks):
        env.tick = tick
        print("\n=== TICK", tick, "===")
        # 1) antigen master: apply deposit intents now, collect attempt_infect intents for later merge
        saved_attempts = []
        if antigen_master:
            try:
                intents = antigen_master.tick()
                for it in intents:
                    if it.get("action") == "deposit":
                        fld = it.get("field")
                        x,y = it.get("coord")
                        space.fields.setdefault(fld, [[0.0]*space.w for _ in range(space.h)])
                        space.fields[fld][y][x] += it.get("amount", 0.0)
                        env.emit_event("deposit", {"field": fld, "coord": it.get("coord"), "amount": it.get("amount")})
                    elif it.get("action") == "attempt_infect":
                        saved_attempts.append(it)
                    else:
                        env.emit_event("master_intent", it)
            except Exception:
                env.emit_event("antigen_master_error", {"trace": traceback.format_exc()})

        # 2) run other masters, collect their intents
        collected = []
        for m in other_masters:
            try:
                its = m.tick()
                collected.extend(its)
            except Exception:
                env.emit_event("master_error", {"master": getattr(m,"__class__",None).__name__, "trace": traceback.format_exc()})

        all_intents = []
        all_intents.extend(saved_attempts)
        all_intents.extend(collected)

        # 3) merge attempt_infects
        others, merged = merge_attempt_infects(all_intents, policy="max")
        for it in merged:
            # emit merged attempt
            env.emit_event("merged_attempt_infect", {"coord": it.get("coord"), "strength": it.get("strength"), "score": it.get("score")})
            # apply simple degradation of antigen at that coord
            try:
                x,y = it.get("coord")
                fld = space.fields.get("Field_Antigen_Density")
                if fld:
                    fld[y][x] = max(0.0, fld[y][x] - float(it.get("score", 0.0))*0.5)
            except Exception:
                pass

            # --- NEW: spawn / infect epithelial cell (real object) ---
            try:
                coord = tuple(it.get("coord"))
                strength = float(it.get("strength", 0.0))
                score = float(it.get("score", 0.0))
                # compute viral/infection load
                load = strength * infection_scale
                # try find existing epithelial cell at coord
                existing_epi = None
                for c in space.cells.values():
                    try:
                        if getattr(c, "cell_type", None) == "EpithelialCell" and tuple(getattr(c, "coord", (None,None))) == coord:
                            existing_epi = c
                            break
                    except Exception:
                        continue
                if existing_epi is not None:
                    # mark infected if not already
                    try:
                        if not getattr(existing_epi, "infected", False):
                            setattr(existing_epi, "infected", True)
                            setattr(existing_epi, "infection_load", load)
                            env.emit_event("epi_infected", {"cell_id": getattr(existing_epi,"id",None), "coord": coord, "load": float(load)})
                    except Exception:
                        env.emit_event("epi_infect_error", {"coord": coord, "cell": getattr(existing_epi,"id",None), "trace": traceback.format_exc()})
                else:
                    # spawn new infected epithelial cell
                    cid = f"epi_spawn_{coord[0]}_{coord[1]}_{tick}"
                    spawn_epithelial(space, env, cid, coord, infected=True, infection_load=load)
                # optional debug: spawn CTL to see killing (if requested)
                if debug_spawn_ctl and (strength > 0.0):
                    try:
                        if CTL:
                            ctl_id = f"ctl_test_{coord[0]}_{coord[1]}_{tick}"
                            ctl = CTL(ctl_id, coord)
                            space.cells[ctl_id] = ctl
                            env.emit_event("ctl_spawned", {"cell_id": ctl_id, "coord": coord})
                        else:
                            # fallback: emit event only
                            env.emit_event("ctl_spawned", {"cell_id": f"ctl_test_{coord[0]}_{coord[1]}_{tick}", "coord": coord})
                    except Exception:
                        env.emit_event("ctl_spawn_error", {"coord": coord, "trace": traceback.format_exc()})

            except Exception:
                env.emit_event("epi_spawn_error", {"trace": traceback.format_exc()})

        # 4) apply other intents (deposit/recruit/percell tcell intents will be ignored here for simplicity)
        for it in others:
            action = it.get("action")
            # deposits (cytokines or general)
            if action in ("deposit_cytokine","deposit"):
                fld = it.get("field")
                x,y = it.get("coord")
                try:
                    space.fields.setdefault(fld, [[0.0]*space.w for _ in range(space.h)])
                    space.fields[fld][y][x] += it.get("amount", 0.0)
                    env.emit_event("deposit", {"field": fld, "coord": it.get("coord"), "amount": it.get("amount")})
                except Exception:
                    pass

            # recruitment (apc / recruit)
            if action in ("recruit_apc","recruit"):
                # accept either 'probability' or 'prob' as key
                p = float(it.get("probability", it.get("prob", 0.0)))
                if random.random() <= p:
                    # create a simple DC in space near coord
                    try:
                        cid = f"dc_{tick}_{len(space.cells)}"
                        if DendriticCell:
                            dc = DendriticCell(cid, tuple(it.get("coord")))
                            space.cells[cid] = dc
                        else:
                            # fallback minimal DC with tick stub
                            class FallbackDC:
                                cell_type = "DendriticCell"
                                def __init__(self, cid, coord):
                                    self.id = cid
                                    self.coord = tuple(coord)
                                def tick(self, space, env):
                                    pass
                            dc = FallbackDC(cid, tuple(it.get("coord")))
                            space.cells[cid] = dc
                        env.emit_event("apc_spawned", {"coord": it.get("coord"), "cell_type": "DendriticCell", "cell_id": cid})
                    except Exception:
                        env.emit_event("apc_spawn_error", {"coord": it.get("coord"), "trace": traceback.format_exc()})
                else:
                    env.emit_event("apc_recruit_skipped", {"coord": it.get("coord"), "prob": p})

        # 5) tick all cells (movement, antigen release, killing) - cell.tick should emit events
        # collect cells that flagged themselves as lysed/removed (fallback epi sets _lysed)
        to_remove = []
        for c in list(space.cells.values()):
            try:
                c.tick(space, env)
                # remove fallback lysed epithelium if flagged (prevents infinite linger)
                if getattr(c, "_lysed", False):
                    to_remove.append(getattr(c, "id", None))
            except Exception:
                env.emit_event("cell_tick_error", {"cell_id": getattr(c,"id",None), "trace": traceback.format_exc()})
        for cid in to_remove:
            if cid and cid in space.cells:
                try:
                    del space.cells[cid]
                except Exception:
                    pass

        # 6) advance scheduler and run due percell decisions (basic)
        due = scheduler.advance(env.tick)
        for entry in due:
            cell = entry.get("cell")
            intent = entry.get("intent")
            ptype = entry.get("percell_type")
            params = entry.get("params", {}) or {}
            try:
                # try percell dynamic import path used by scheduler
                per_mod, err = scheduler._import_percell_module(ptype)
                actions = []
                if per_mod and hasattr(per_mod,"decide"):
                    actions = getattr(per_mod,"decide")(cell, env, intent, params)
                # process secrete/differentiate minimal
                if actions:
                    if isinstance(actions, dict):
                        actions = [actions]
                    for a in actions:
                        if a.get("name") == "secrete":
                            payload = a.get("payload",{}) or {}
                            sub = payload.get("substance")
                            amt = float(payload.get("amount",1.0))
                            if sub:
                                x,y = getattr(cell,"coord",(None,None))
                                if x is not None:
                                    space.fields.setdefault(f"Field_{sub}", [[0.0]*space.w for _ in range(space.h)])
                                    space.fields[f"Field_{sub}"][y][x] += amt
                                    env.emit_event("secrete", {"cell_id": getattr(cell,"id",None), "substance": sub, "amount": amt})
                        if a.get("name") == "differentiate":
                            env.emit_event("cell_differentiated", {"cell_id": getattr(cell,"id",None), "target_state": a.get("payload",{}).get("target_state")})
            except Exception:
                env.emit_event("percell_error", {"trace": traceback.format_exc()})

        # brief summary
        # count cell types
        counts = {}
        for c in space.cells.values():
            counts[getattr(c,"cell_type", getattr(c,"__class__",None).__name__)] = counts.get(getattr(c,"cell_type", getattr(c,"__class__",None).__name__),0) + 1
        print("Cell counts:", counts)
        # small antigen slice
        print("Antigen sample row 1-3:")
        ag = space.fields.get("Field_Antigen_Density", [])
        for y in range(min(len(ag),4)):
            print("y=%d:"%y, ag[y][:12])

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 run_scenario.py path/to/scenario.yaml [n_ticks]")
        sys.exit(1)
    path = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) >=3 else 10
    run(path, n)

