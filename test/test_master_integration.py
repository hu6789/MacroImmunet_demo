# test/test_master_integration.py
"""
Integration smoke test — robust caller that tolerates master APIs with
different method names (step/run/handle/tick/process/act/__call__).

Save as test/test_master_integration.py and run:
  PYTHONPATH=. python3 test/test_master_integration.py
"""

from typing import Any, List
import pprint
import random
from collections import defaultdict

pp = pprint.PrettyPrinter(indent=2)

# ------------------ friendly action-name helpers ---------------------------
def readable_action_name(a: Any) -> str:
    """
    Return a human-friendly name for a behaviour/action value `a`.
    Handles: dict actions, objects with .name, classes, basic types.
    """
    # dict-like action: prefer explicit 'name' then 'action' then 'type'
    try:
        if isinstance(a, dict):
            name = a.get("name") or a.get("action") or a.get("type")
            if name is not None:
                return str(name)
    except Exception:
        pass

    # object with attribute 'name' (Intent instances / objects)
    try:
        nm = getattr(a, "name", None)
        if nm is not None:
            return str(nm)
    except Exception:
        pass

    # some Intent implementations might expose a class-level 'NAME' or similar
    try:
        if isinstance(a, type):
            return a.__name__
        else:
            return a.__class__.__name__
    except Exception:
        pass

    # fallback to stringification
    try:
        return str(a)
    except Exception:
        return "<unprintable action>"

def collect_action_names(actions: List[Any]) -> List[str]:
    """
    Map a list of action values to human-friendly names using readable_action_name.
    """
    out = []
    for a in (actions or []):
        out.append(readable_action_name(a))
    return out

# ------------------ imports of masters (guarded) ---------------------------
# Epithelial master is expected
from cell_master.masters.epithelial_master import EpithelialMaster

# AntigenMaster may or may not exist or have different API; guard its import
try:
    from cell_master.masters.antigen_master import AntigenMaster
except Exception:
    AntigenMaster = None

# The rest we expect to exist
from cell_master.masters.dc_master import DCMaster
from cell_master.masters.native_t_master import NativeTMaster
from cell_master.masters.th1_master import Th1Master
from cell_master.masters.ctl_master import CTLMaster

# ------------------ tiny fake environment helpers -------------------------
class FakeAgent:
    def __init__(self, coord=(0,0), infectious=True, proto=None):
        self.coord = coord
        self.infectious = infectious
        self.proto = proto or {}

    def as_dict(self):
        return {"coord": self.coord, "infectious": bool(self.infectious), "proto": dict(self.proto)}

# ------------------ robust master caller ----------------------------------
def call_master(master_obj, coord, summary, cell_meta, rng):
    """
    Try to call a master object with a sensible API. Return list of actions or [].
    Tries method names in order: step, run, handle, tick, process, act, __call__.
    If none found, return [] and print available attributes for debugging.
    """
    if master_obj is None:
        return []

    # candidate callables (method names)
    candidates = ["step", "run", "handle", "tick", "process", "act", "__call__"]

    for name in candidates:
        fn = getattr(master_obj, name, None)
        if callable(fn):
            # Try several calling conventions to be tolerant
            # 1) keyword args (coord=..., summary=..., cell_meta=..., rng=...)
            try:
                return fn(coord=coord, summary=summary, cell_meta=cell_meta, rng=rng)
            except TypeError:
                pass
            except Exception as e:
                print(f"[WARN] exception while calling {master_obj}.{name} (kw): {e}")
                return []

            # 2) positional full
            try:
                return fn(coord, summary, cell_meta, rng)
            except TypeError:
                pass
            except Exception as e:
                print(f"[WARN] exception while calling {master_obj}.{name} (pos): {e}")
                return []

            # 3) shorter positional variants
            try:
                return fn(coord, summary, rng)
            except Exception:
                pass

            try:
                return fn(coord, summary)
            except Exception:
                pass

            # 4) call with single summary (some masters expect only a context)
            try:
                return fn(summary)
            except Exception:
                pass

            # 5) call with no args if nothing else worked
            try:
                return fn()
            except Exception:
                pass

    # no callable found — print available attributes to help debug
    print(f"[WARN] master object {master_obj!r} has no recognized callable entry (tried step/run/handle/tick/process/act/__call__).")
    attrs = [n for n in dir(master_obj) if not n.startswith("_")]
    print("       available attributes/methods:", attrs[:60])
    return []

# ------------------ instantiate masters and fake world --------------------
rng = random.Random(42)
epi_master = EpithelialMaster({"debug": False})
ant_master = AntigenMaster({"debug": False}) if AntigenMaster else None
dc_master = DCMaster()
native_t = NativeTMaster()
th1_master = Th1Master()
ctl_master = CTLMaster()

# tiny population and meta stores
cells = {
    "epi_1": {"type": "EPITHELIAL", "coord": (0.0, 0.0), "meta": {}},
    "dc_1":  {"type": "DC",        "coord": (2.0, 0.0), "meta": {}},
    "t_naive_1": {"type": "NAIVE_T","coord": (5.0, 5.0), "meta": {}},
    "th1_1": {"type": "TH1",       "coord": (6.0, 5.0), "meta": {}},
    "ctl_1": {"type": "CTL",       "coord": (1.0, 0.0), "meta": {}},
}
cell_meta_store = {k: v["meta"] for k, v in cells.items()}
agents = []

def mk_summary_for_cell(cell_id):
    # include all agents and a simple neighbor summary for other cells
    s = {"agents": [a.as_dict() for a in agents],
         "cells": [
             {"coord": cells[cid]["coord"], "state": cell_meta_store[cid].get("state"), "id": cid}
             for cid in cells.keys() if cid != cell_id
         ]}
    return s

# ------------------ simulation loop ---------------------------------------
TICKS = 6
print(">>> Starting robust master integration smoke run for", TICKS, "ticks\n")

for tick in range(1, TICKS + 1):
    print("=== TICK", tick)
    produced_actions = defaultdict(list)

    # Epithelial masters
    for cid, meta in list(cell_meta_store.items()):
        if cells[cid]["type"] != "EPITHELIAL":
            continue
        summary = mk_summary_for_cell(cid)
        coord = cells[cid]["coord"]
        acts = call_master(epi_master, coord, summary, meta, rng) or []
        print(f"[EPI {cid}] actions:", collect_action_names(acts))
        produced_actions[cid].extend(acts)
        for a in acts:
            if isinstance(a, dict) and a.get("name") == "release_antigen":
                amt = a["payload"].get("amount", 1.0)
                new_agent = FakeAgent(coord=(coord[0]+0.2, coord[1]+0.1), infectious=True, proto={"amount": amt})
                agents.append(new_agent)
                print(f"  -> spawned antigen agent from epithelial ({amt})")

    # Antigen master (if present)
    if ant_master is not None:
        try:
            ant_res = call_master(ant_master, None, {"agents": [a.as_dict() for a in agents]}, {}, rng) or []
            if ant_res:
                print("[ANT] actions:", collect_action_names(ant_res))
        except Exception as e:
            print("[ANT] error calling AntigenMaster:", e)

    # DC masters
    for cid, meta in list(cell_meta_store.items()):
        if cells[cid]["type"] != "DC":
            continue
        coord = cells[cid]["coord"]
        summary = mk_summary_for_cell(cid)
        acts = call_master(dc_master, coord, summary, meta, rng) or []
        print(f"[DC {cid}] actions:", collect_action_names(acts))
        produced_actions[cid].extend(acts)

    # Naive T
    for cid, meta in list(cell_meta_store.items()):
        if cells[cid]["type"] != "NAIVE_T":
            continue
        coord = cells[cid]["coord"]
        summary = mk_summary_for_cell(cid)
        acts = call_master(native_t, coord, summary, meta, rng) or []
        print(f"[NAIVE_T {cid}] actions:", collect_action_names(acts))
        produced_actions[cid].extend(acts)
        for a in acts:
            if isinstance(a, dict) and a.get("name") == "differentiate":
                payload = a.get("payload", {})
                new_type = payload.get("to")
                print(f"  -> naive {cid} differentiates to {new_type}")

    # Th1
    for cid, meta in list(cell_meta_store.items()):
        if cells[cid]["type"] != "TH1":
            continue
        coord = cells[cid]["coord"]
        summary = mk_summary_for_cell(cid)
        acts = call_master(th1_master, coord, summary, meta, rng) or []
        print(f"[TH1 {cid}] actions:", collect_action_names(acts))
        produced_actions[cid].extend(acts)

    # CTL
    for cid, meta in list(cell_meta_store.items()):
        if cells[cid]["type"] != "CTL":
            continue
        coord = cells[cid]["coord"]
        summary = mk_summary_for_cell(cid)
        acts = call_master(ctl_master, coord, summary, meta, rng) or []
        print(f"[CTL {cid}] actions:", collect_action_names(acts))
        produced_actions[cid].extend(acts)

    # simple agent decay to avoid explosion (just for demo)
    if agents and rng.random() < 0.25:
        removed = agents.pop(0)
        print("  [env] antigen agent decayed/removed at end of tick")

    print("")  # blank line

print(">>> integration smoke run finished.")

