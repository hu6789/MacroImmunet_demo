#!/usr/bin/env python3
# runner_ein/orchestrator_demo.py
"""
Small orchestrator-style demo that shows:
 - masters producing intents
 - optional AntigenMaster producing antigen dynamics
 - simple immediate handling for epithelial / DC intents
 - scheduling of per-cell decisions via Scheduler
 - executing scheduled percell decisions and applying a couple of example effects

Run:
  PYTHONPATH=. python3 runner_ein/orchestrator_demo.py
"""
import importlib
import traceback
import random
from runner_ein.masters.epithelial_master import EpithelialMaster
from runner_ein.masters.dc_master import DCMaster
from runner_ein.masters.naive_tcell_master import NaiveTCellMaster

from runner_ein.percell.scheduler import Scheduler
from runner_ein.percell import th2_percell

# try to import simple cell types (you created runner_ein/cells/simple_cells.py)
try:
    from runner_ein.cells.simple_cells import DendriticCell, EpithelialCell, CTL
except Exception:
    DendriticCell = None
    EpithelialCell = None
    CTL = None


class FakeSpace:
    def __init__(self, id, w=12, h=6):
        self.id = id
        self.w = w
        self.h = h
        self.fields = {}
        self.fields["Field_Antigen_Density"] = [[0.0 for _ in range(w)] for __ in range(h)]
        self.fields["Field_Cell_Debris"] = [[0.0 for _ in range(w)] for __ in range(h)]
        self.fields["Field_IL12"] = [[0.0 for _ in range(w)] for __ in range(h)]
        self.fields["Field_CCL19"] = [[0.0 for _ in range(w)] for __ in range(h)]
        # optional: allocate IL4 field so percell secrete can write to it in demo
        self.fields["Field_IL4"] = [[0.0 for _ in range(w)] for __ in range(h)]
        self.cells = {}

    def get_cells_of_type(self, type_name):
        out = []
        for c in self.cells.values():
            t = getattr(c, "type", None) or (getattr(c, "meta", {}) or {}).get("type", None) or getattr(c, "cell_type", None)
            if t is None:
                if type_name.lower() in getattr(c, "id", "").lower():
                    out.append(c)
            else:
                # be permissive: accept substring matches both ways
                if str(type_name) in str(t) or str(t) in str(type_name):
                    out.append(c)
        return out


class EnvAdapter:
    def __init__(self):
        self.events = []
        self.tick = 0

    def emit_event(self, name, payload):
        # central logging for demo; scheduler/percell may also call this
        print("EVENT:", name, payload)
        self.events.append((name, payload))


# ---------- helper: merge attempt_infect intents ----------
def merge_attempt_infects(intents_list, policy="max"):
    """
    Merge multiple attempt_infect intents coming from different masters.
    Args:
      - intents_list: list of intent dicts (may include other actions)
      - policy:
          'max' -> keep the attempt_infect with max strength per coord (default)
          'sum' -> sum strengths per coord
          'prefer_epithelium' -> prefer intents that include 'master':'EpithelialMaster' if present
          'prefer_antigen' -> prefer intents that include 'master':'AntigenMaster' if present
    Returns:
      - (filtered_intents, merged_attempts) where:
         filtered_intents = original intents without attempt_infect entries
         merged_attempts = list of merged attempt_infect intents (one per coord)
    """
    attempts_by_coord = {}
    other_intents = []
    for it in intents_list:
        if it.get("action") == "attempt_infect":
            coord = tuple(it.get("coord"))
            entry = attempts_by_coord.get(coord, {"candidates": []})
            entry["candidates"].append(it)
            attempts_by_coord[coord] = entry
        else:
            other_intents.append(it)

    merged = []
    for coord, info in attempts_by_coord.items():
        cands = info.get("candidates", [])
        if not cands:
            continue
        if policy == "max":
            best = max(cands, key=lambda x: float(x.get("strength", 0.0)))
            merged.append(best)
        elif policy == "sum":
            total_strength = sum(float(x.get("strength", 0.0)) for x in cands)
            total_score = max(float(x.get("score", 0.0)) for x in cands)
            best = max(cands, key=lambda x: float(x.get("score", 0.0)))
            merged.append({"action": "attempt_infect", "coord": coord, "strength": total_strength, "score": total_score, "master": "merged"})
        elif policy == "prefer_epithelium":
            pref = [x for x in cands if str(x.get("master", "")).lower().startswith("epithel")]
            if pref:
                best = max(pref, key=lambda x: float(x.get("strength", 0.0)))
                merged.append(best)
            else:
                merged.append(max(cands, key=lambda x: float(x.get("strength", 0.0))))
        elif policy == "prefer_antigen":
            pref = [x for x in cands if "antigen" in str(x.get("master", "")).lower()]
            if pref:
                best = max(pref, key=lambda x: float(x.get("strength", 0.0)))
                merged.append(best)
            else:
                merged.append(max(cands, key=lambda x: float(x.get("strength", 0.0))))
        else:
            # fallback to max
            merged.append(max(cands, key=lambda x: float(x.get("strength", 0.0))))

    return other_intents, merged


def demo():
    space = FakeSpace("Lung_Tissue_2D", w=12, h=6)
    # seed fields (demo hotspots)
    space.fields["Field_Antigen_Density"][2][3] = 10.0
    space.fields["Field_Antigen_Density"][1][9] = 6.0
    space.fields["Field_Cell_Debris"][2][4] = 2.0
    space.fields["Field_Cell_Debris"][1][9] = 1.5

    env = EnvAdapter()

    # try to create AntigenMaster (optional). If present, instantiate with reasonable demo params.
    am = None
    try:
        from runner_ein.masters.antigen_master import AntigenMaster

        # Build seeds from existing seeded positions as default demo seeds
        seeds = [
            {"tick": 0, "coord": (3, 2), "amount": float(space.fields["Field_Antigen_Density"][2][3])},
            {"tick": 0, "coord": (9, 1), "amount": float(space.fields["Field_Antigen_Density"][1][9])},
        ]
        am = AntigenMaster(
            space,
            env,
            params={
                "seeds": seeds,
                "continuous_influx_rate": 0.0,
                "replication_rate": 0.05,
                "replication_cap": 100.0,
                "diffusion_rate": 0.2,
                "decay": 0.995,
                "attempt_infect_threshold": 0.5,
                "attempt_infect_strength_scale": 1.0,
                "max_attempts_per_tick": 10,
                "name": "AntigenMasterDemo",
            },
        )
    except Exception:
        # AntigenMaster absent or error; continue without failing demo
        am = None

    em = EpithelialMaster(space, env, params={"scan_threshold": 0.5, "max_hotspots": 2, "infection_intent_strength": 0.05})
    dm = DCMaster(
        space,
        env,
        params={
            "antigen_threshold": 0.5,
            "debris_threshold": 0.2,
            "max_hotspots": 3,
            "il12_deposit_per_hotspot": 2.0,
            "recruit_prob_per_hotspot": 0.8,
            "norm_score": 10.0,
        },
    )

    # simple naive CD4 cells (demo stand-ins)
    class SimpleCell:
        def __init__(self, cid, coord, cell_type="Naive_CD4"):
            self.id = cid
            self.coord = coord
            self.type = cell_type
            self.cell_type = cell_type
            self.meta = {}
            # repertoire: set of peptide ids this cell recognizes (demo)
            self.tcr_repertoire = [{"id": "cl1", "specificity": {"PepX"}}]
            self.co_stim = 0.0

    c1 = SimpleCell("naive_cd4_a", (3, 2))
    c2 = SimpleCell("naive_cd4_b", (8, 1))
    space.cells[c1.id] = c1
    space.cells[c2.id] = c2

    # Create minimal epithelial cells at seeded coords so infection maps to concrete objects
    if EpithelialCell:
        for coord in ((3, 2), (9, 1)):
            cid = f"epi_{coord[0]}_{coord[1]}"
            if cid not in space.cells:
                space.cells[cid] = EpithelialCell(cid, coord)
    else:
        # fallback: create simple objects
        for coord in ((3, 2), (9, 1)):
            cid = f"epi_{coord[0]}_{coord[1]}"
            if cid not in space.cells:
                class _E: pass
                e = _E()
                e.id = cid
                e.coord = coord
                e.cell_type = "EpithelialCell"
                e.state = "healthy"
                e.viral_load = 0.0
                space.cells[cid] = e

    # env helpers used by percell or masters in demo
    def collect_pMHC_near(coord, radius=1):
        x, y = coord
        try:
            val = space.fields["Field_Antigen_Density"][y][x]
        except Exception:
            val = 0.0
        if val >= 1.0:
            return [{"pMHC_id": "pm1", "peptide_id": "PepX", "mhc_type": "MHC_II", "presenter": "dc_demo"}]
        return []

    env.collect_pMHC_near = collect_pMHC_near

    def compute_affinity(pm, tcr):
        pid = pm.get("peptide_id") if isinstance(pm, dict) else None
        try:
            if isinstance(tcr, dict):
                spec = tcr.get("specificity", set())
                if pid in spec:
                    return 0.85
        except Exception:
            pass
        return 0.0

    env.compute_affinity = compute_affinity

    # scheduler for percell deferred decisions
    scheduler = Scheduler(env=env)

    # create NaiveTCellMaster instance (cleanly indented)
    tm = NaiveTCellMaster(
        space,
        env,
        params={
            "cell_types": ["Naive_CD4"],
            "affinity_threshold": 0.3,
            "percell_precedence": True,
            "enable_proliferation_intent": True,
            "scan_radius": 1,
            # optional: map naive types -> percell suggestions
            "percell_type_map": {"Naive_CD4": "Th2", "Naive_CD8": "CTL"},
            # you can add percell specific params under "percell" if you want demo to read them
            "percell": {"Th2": {"decision_latency_ticks": 2}},
        },
    )

    # Simulate orchestrator ticks: demonstrate latency
    current_tick = 0
    env.tick = current_tick

    # ---------------------------
    # 1) Run AntigenMaster if present, but only apply deposit intents immediately.
    #    Keep attempt_infect intents for merging later (we do NOT emit them now).
    # ---------------------------
    saved_attempt_intents = []
    try:
        if am is not None:
            a_intents = am.tick()
            for it in a_intents:
                try:
                    if it.get("action") == "deposit":
                        fld = it.get("field")
                        x, y = it.get("coord")
                        space.fields.setdefault(fld, [[0.0] * space.w for _ in range(space.h)])
                        space.fields[fld][y][x] += it.get("amount", 0.0)
                        env.emit_event("deposit", {"field": fld, "coord": it.get("coord"), "amount": it.get("amount")})
                    elif it.get("action") == "attempt_infect":
                        # save for merging, don't emit/apply yet
                        saved_attempt_intents.append(it)
                    else:
                        env.emit_event("master_intent", it)
                except Exception:
                    env.emit_event("antigen_intent_apply_error", {"intent": it, "trace": traceback.format_exc()})
    except Exception:
        env.emit_event("antigen_master_error", {"error": "antigen tick failed", "trace": traceback.format_exc()})

    # ---------------------------
    # 2) Run other masters, collect their intents (but don't apply attempt_infects yet).
    # ---------------------------
    e_intents = em.tick()
    d_intents = dm.tick()
    t_intents = tm.tick()

    # collect all intents across masters for merging
    all_master_intents = []
    # include saved antigen attempt intents
    all_master_intents.extend(saved_attempt_intents)
    # include epithelial intents
    all_master_intents.extend(e_intents)
    # include DC intents and others (we'll keep them in all_master_intents too; merge helper will skip non-attempts)
    all_master_intents.extend(d_intents)
    all_master_intents.extend(t_intents)

    # ---------------------------
    # 3) Merge attempt_infect intents (policy: 'max' by default)
    # ---------------------------
    other_intents, merged_attempts = merge_attempt_infects(all_master_intents, policy="max")

    # emit helper events for visibility
    for it in merged_attempts:
        env.emit_event("merged_attempt_infect", {"coord": it.get("coord"), "strength": it.get("strength"), "score": it.get("score")})

    # ---------------------------
    # 4) Apply merged attempt_infect intents (single per coord)
    #    Map attempt_infect -> infect an epithelial cell (create if missing)
    # ---------------------------
    for it in merged_attempts:
        coord = tuple(it.get("coord"))
        x, y = coord
        # infect an epithelial cell at coord (create if missing)
        epi = None
        for c in space.cells.values():
            if getattr(c, "cell_type", "") == "EpithelialCell" and getattr(c, "coord", None) == (x, y):
                epi = c
                break
        if epi is None:
            cid = f"epi_{x}_{y}"
            if EpithelialCell:
                epi = EpithelialCell(cid, (x, y))
                space.cells[cid] = epi
            else:
                class _E:
                    pass
                epi = _E()
                epi.id = cid
                epi.coord = (x, y)
                epi.cell_type = "EpithelialCell"
                epi.state = "healthy"
                epi.viral_load = 0.0
                space.cells[cid] = epi

        # map strength -> viral_load increment (demo heuristic)
        try:
            load = float(it.get("strength", 1.0))
        except Exception:
            load = 1.0

        if hasattr(epi, "become_infected"):
            epi.become_infected(load)
        else:
            epi.state = "infected"
            epi.viral_load = load

        # sample effect: reduce antigen at coord proportional to score (legacy demo semantics)
        try:
            nd = space.fields["Field_Antigen_Density"]
            nd[y][x] = max(0.0, nd[y][x] - float(it.get("score", 0.0)) * 0.5)
        except Exception:
            pass

        env.emit_event("attempt_infect", {"coord": coord, "strength": it.get("strength"), "score": it.get("score"), "cell_id": getattr(epi, "id", None)})

    # ---------------------------
    # 5) Now handle DC intents (deposit/recruit) from other_intents (non-attempts)
    #    Recruit -> instantiate a DendriticCell in space.cells
    # ---------------------------
    for it in other_intents:
        if it.get("action") in ("deposit_cytokine", "deposit"):
            fld = it.get("field")
            x, y = it.get("coord")
            try:
                space.fields.setdefault(fld, [[0.0] * space.w for _ in range(space.h)])
                space.fields[fld][y][x] += it.get("amount", 0.0)
            except Exception:
                pass
            env.emit_event("deposit", {"field": fld, "coord": it.get("coord"), "amount": it.get("amount")})
        if it.get("action") in ("recruit_apc", "recruit"):
            coord = tuple(it.get("coord"))
            prob = float(it.get("probability", 0.5))
            if random.random() <= prob:
                # instantiate DC and register
                new_id = f"dc_{len([k for k in space.cells.keys() if str(k).startswith('dc_')])+1}"
                if DendriticCell:
                    dc = DendriticCell(new_id, coord)
                    space.cells[new_id] = dc
                else:
                    class _D:
                        pass
                    dc = _D()
                    dc.id = new_id
                    dc.coord = coord
                    dc.cell_type = "DendriticCell"
                    space.cells[new_id] = dc
                env.emit_event("apc_spawned", {"coord": coord, "cell_type": "DendriticCell", "cell_id": new_id})
            else:
                env.emit_event("apc_recruit_skipped", {"coord": coord, "prob": prob})

    # ---------------------------
    # 6) Route TCell intents (from other_intents) -> schedule percell with latency
    # ---------------------------
    immediate_tcell_intents = []
    scheduled_count = 0
    for it in other_intents:
        if it.get("action") in ("percell_evaluate", "percell", "percell_decide", "percell_eval"):
            percell_conf = (tm.params.get("percell", {}) or {}).get(it.get("percell_type"), {})
            latency = int(percell_conf.get("decision_latency_ticks", 2))
            # schedule with latency; scheduler will emit percell_scheduled event
            scheduler.submit(
                cell=space.cells.get(it.get("cell_id")),
                intent=it,
                percell_type=it.get("percell_type"),
                latency_ticks=latency,
                params=percell_conf or {},
                current_tick=current_tick,
                execute_immediately=False,
                env=env,
                space=space,
            )
            scheduled_count += 1
        else:
            # keep immediate tcell-like intents for immediate handling
            immediate_tcell_intents.append(it)

    # handle immediate tcell intents
    for it in immediate_tcell_intents:
        if it.get("action") == "tcr_activation":
            env.emit_event("tcr_activation", {"cell_id": it.get("cell_id"), "affinity": it.get("best_affinity"), "pmhc": it.get("pmhc_summary")})
        if it.get("action") == "differentiate":
            # apply immediately if someone requested immediate differentiation
            cid = it.get("cell_id")
            target = it.get("target_state")
            cell = space.cells.get(cid)
            if cell:
                cell.state = "effector"
                cell.cell_type = f"Effector_{target}"
            env.emit_event("differentiate", {"cell_id": cid, "target_state": target, "prob": it.get("probability")})
        if it.get("action") == "proliferate":
            env.emit_event("proliferate", {"cell_id": it.get("cell_id"), "probability": it.get("probability")})

    print(f"\nScheduled {scheduled_count} percell task(s) with latency (demo).\n")

    # Advance scheduler to tick+1 (nothing due yet)
    env.tick = current_tick + 1
    due = scheduler.advance(env.tick)  # should be empty
    print("Advance to tick+1 -> due count:", len(due))

    # Advance scheduler to tick+2 (due entries appear)
    env.tick = current_tick + 2
    due2 = scheduler.advance(env.tick)
    print("Advance to tick+2 -> due count:", len(due2))

    # Execute due percell decisions (call percell module decide)
    merged_actions = []
    for entry in due2:
        cell = entry.get("cell")
        intent = entry.get("intent")
        ptype = entry.get("percell_type")
        params = entry.get("params", {}) or {}
        try:
            if ptype and str(ptype).lower().startswith("th2"):
                actions = th2_percell.decide(cell, env, intent, params)
            else:
                # try to import dynamically for unknown percell types
                actions = []
                try:
                    # attempt dynamic import using scheduler helper
                    per_mod, err = scheduler._import_percell_module(ptype)
                    if per_mod and hasattr(per_mod, "decide"):
                        actions = getattr(per_mod, "decide")(cell, env, intent, params)
                except Exception:
                    actions = []
        except Exception as ex:
            actions = []
            env.emit_event("percell_error", {"cell_id": getattr(cell, "id", None), "error": str(ex), "trace": traceback.format_exc()})

        # normalize and apply simple mapping
        if actions is None:
            actions = []
        if isinstance(actions, dict):
            actions = [actions]
        for a in actions:
            merged_actions.append({"cell_id": getattr(cell, "id", None), "name": a.get("name"), "payload": a.get("payload", {})})
            # apply secrete -> field update for IL4
            if a.get("name") == "secrete":
                payload = a.get("payload", {}) or {}
                sub = payload.get("substance")
                amt = float(payload.get("amount", 1.0))
                if sub == "IL4":
                    x, y = getattr(cell, "coord", (None, None))
                    if x is not None:
                        try:
                            space.fields["Field_IL4"][y][x] += amt
                        except Exception:
                            pass
                        env.emit_event("secrete", {"cell_id": getattr(cell, "id", None), "substance": sub, "amount": amt})
            if a.get("name") == "differentiate":
                # apply differentiation to the actual cell object (create effectors or spawn CTL)
                payload = a.get("payload", {}) or {}
                target = payload.get("target_state")
                if cell is not None:
                    # basic rule: if Th1/Th2 -> mark as effector on same cell
                    if isinstance(target, str) and ("Th" in target or "Th1" in target or "Th2" in target):
                        cell.state = "effector"
                        cell.cell_type = f"Effector_{target}"
                        env.emit_event("cell_differentiated", {"cell_id": getattr(cell, "id", None), "target_state": target})
                    # if CTL requested, spawn a CTL at same coord
                    elif isinstance(target, str) and ("CTL" in target or "CD8" in target):
                        nid = f"ctl_{len([k for k in space.cells.keys() if str(k).startswith('ctl_')])+1}"
                        if CTL:
                            new_ctl = CTL(nid, getattr(cell, "coord", (0, 0)))
                            space.cells[nid] = new_ctl
                        else:
                            class _C:
                                pass
                            new_ctl = _C()
                            new_ctl.id = nid
                            new_ctl.coord = getattr(cell, "coord", (0, 0))
                            new_ctl.cell_type = "CTL"
                            space.cells[nid] = new_ctl
                        env.emit_event("ctl_spawned", {"cell_id": nid, "from_cell": getattr(cell, "id", None), "coord": new_ctl.coord})
            if a.get("name") == "proliferate":
                payload = a.get("payload", {}) or {}
                prob = float(payload.get("probability", 0.5))
                if random.random() <= prob:
                    parent = cell
                    if parent is not None:
                        px, py = getattr(parent, "coord", (0, 0))
                        offs = [(1, 0), (-1, 0), (0, 1), (0, -1), (0, 0)]
                        dx, dy = random.choice(offs)
                        nx, ny = max(0, min(space.w - 1, px + dx)), max(0, min(space.h - 1, py + dy))
                        new_id = f"{str(parent.cell_type).lower()}_{len([k for k in space.cells.keys() if str(k).startswith(str(parent.cell_type).lower())])+1}"
                        # minimal clone creation
                        class _P:
                            pass
                        c = _P()
                        c.id = new_id
                        c.coord = (nx, ny)
                        c.cell_type = parent.cell_type
                        c.state = "resting"
                        space.cells[new_id] = c
                        env.emit_event("cell_proliferated", {"parent": getattr(parent, "id", None), "new": new_id, "coord": (nx, ny)})

    # diagnostics printout (merged actions)
    print("\nMerged Actions (for demo):")
    for ma in merged_actions:
        print(" -", ma)

    # ---------------------------
    # 7) Micro ticks: let created cells act (move, secrete, kill, produce antigen)
    # ---------------------------
    MICRO_STEPS = 3
    for micro in range(MICRO_STEPS):
        for cid, cell in list(space.cells.items()):
            try:
                if hasattr(cell, "tick"):
                    cell.tick(space, env)
            except Exception:
                env.emit_event("cell_tick_error", {"cell_id": cid, "trace": traceback.format_exc()})

    # diagnostics: fields and cells
    print("\nSample Field State (IL12 slice around hotspots):")
    s = space.fields.get("Field_IL12", [])
    for y in range(len(s)):
        print("y=%d:" % y, s[y])

    # Also print antigen slice (useful to verify antigen master effects)
    print("\nSample Field State (Antigen slice):")
    a = space.fields.get("Field_Antigen_Density", [])
    for y in range(len(a)):
        print("y=%d:" % y, a[y])

    # print a short summary of cell counts
    types_count = {}
    for c in space.cells.values():
        typ = getattr(c, "cell_type", "unknown")
        types_count[typ] = types_count.get(typ, 0) + 1
    print("\nCell counts:", types_count)


if __name__ == "__main__":
    demo()

