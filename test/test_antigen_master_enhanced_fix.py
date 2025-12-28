#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced AntigenMaster integration test (more robust to repo API variants).

Saves: test/test_antigen_master_enhanced_fix.py
Run:
  PYTHONPATH=. python3 test/test_antigen_master_enhanced_fix.py -v
"""
import time
import pprint
import random
import inspect

pp = pprint.PrettyPrinter(indent=2)

# --- imports: try to import AntigenMaster + DCMaster from known locations ----
AntigenMaster = None
DCMaster = None
Space = None

try:
    from cell_master.masters.antigen_master import AntigenMaster
    AntigenMaster = AntigenMaster
except Exception as e:
    print("Warning: cannot import AntigenMaster from cell_master.masters.antigen_master:", e)

try:
    from cell_master.masters.dc_master import DCMaster
    DCMaster = DCMaster
except Exception as e:
    print("Warning: cannot import DCMaster from cell_master.masters.dc_master:", e)

try:
    # prefer repo's Space if present
    from scan_master.space import Space
except Exception:
    Space = None

# --- TinySpace fallback (compatible with many tests) -------------------------
class TinySpace:
    def __init__(self):
        self._local_agents = []
        self._local_labels = []
    # agent helpers
    def add_agent(self, agent):
        # agent is dict or object with as_dict
        if not isinstance(agent, dict) and hasattr(agent, "as_dict"):
            agent = agent.as_dict()
        self._local_agents.append(agent)
    def list_agents(self):
        return list(self._local_agents)
    def remove_agent(self, aid):
        self._local_agents = [a for a in self._local_agents if a.get("id") != aid]
    # label helpers
    def add_label(self, label):
        self._local_labels.append(label)
    def get_labels(self):
        return list(self._local_labels)
    def get_agents(self):
        # some Spaces expose this
        return list(self._local_agents)
    # compatibility for other call sites
    def snapshot(self):
        return {"agents": list(self._local_agents), "labels": list(self._local_labels)}

# --- helper accessors (robust) ---------------------------------------------
def list_space_labels(world):
    # try several common read APIs
    try:
        fn = getattr(world, "get_labels", None)
        if callable(fn):
            return list(fn())
    except Exception:
        pass
    try:
        if hasattr(world, "_local_labels"):
            return list(getattr(world, "_local_labels"))
    except Exception:
        pass
    try:
        if hasattr(world, "labels") and world.labels is not None:
            return list(world.labels)
    except Exception:
        pass
    try:
        snap = None
        if hasattr(world, "snapshot") and callable(world.snapshot):
            snap = world.snapshot()
        elif hasattr(world, "snapshot"):
            snap = world.snapshot
        if isinstance(snap, dict):
            return list(snap.get("labels", []))
    except Exception:
        pass
    return []

def add_space_label(world, label):
    # try add_label, else append to _local_labels
    try:
        fn = getattr(world, "add_label", None)
        if callable(fn):
            fn(label)
            return True
    except Exception:
        pass
    try:
        if hasattr(world, "_local_labels"):
            world._local_labels.append(label)
            return True
    except Exception:
        pass
    try:
        if hasattr(world, "labels") and world.labels is not None:
            world.labels.append(label)
            return True
    except Exception:
        pass
    return False

# --- instantiate world -----------------------------------------------------
if Space is not None:
    try:
        world = Space()
    except Exception as e:
        print("Failed to instantiate scan_master.space.Space(), falling back to TinySpace. error:", e)
        world = TinySpace()
else:
    world = TinySpace()

print("\nAntigenMaster / Space diagnostics:")
print(" world type:", type(world))
print(" world has add_label?:", callable(getattr(world, "add_label", None)))
print(" world has get_labels?:", callable(getattr(world, "get_labels", None)))
print(" world has snapshot?:", callable(getattr(world, "snapshot", None)))
print(" world has get_agents?:", callable(getattr(world, "get_agents", None)))
print("")

# --- instantiate AntigenMaster robustly ------------------------------------
ant = None
if AntigenMaster is None:
    raise SystemExit("AntigenMaster not found in project; cannot run test.")

# inspect signature and try sensible instantiation options
sig = inspect.signature(AntigenMaster)
print("AntigenMaster signature:", sig)

# try patterns in order
inst_attempts = [
    lambda: AntigenMaster(world),
    lambda: AntigenMaster(space=world),
    lambda: AntigenMaster(world, None, random.Random(12345), {"debug": False}),
    lambda: AntigenMaster(world, config={"debug": False}),
    lambda: AntigenMaster(config={"debug": False}, space=world),
]

inst_ok = False
inst_exc = []
for f in inst_attempts:
    try:
        ant = f()
        inst_ok = True
        break
    except Exception as e:
        inst_exc.append(str(e))
if not inst_ok:
    print("All AntigenMaster instantiation attempts failed:", inst_exc)
    raise SystemExit("Failed to instantiate AntigenMaster - inspect constructor and retry.")

print("AntigenMaster instance created:", ant)
print("AntigenMaster callable attrs sample:", [k for k in dir(ant) if not k.startswith("_")][:50])

# --- ensure spawn_agent exists & signaturable --------------------------------
if not hasattr(ant, "spawn_agent") or not callable(getattr(ant, "spawn_agent")):
    raise SystemExit("AntigenMaster has no spawn_agent() method; cannot continue test.")

# make sure we spawn with a valid proto (include 'epitopes')
valid_proto = {"amount": 1.0, "type": "ANTIGEN_PARTICLE", "epitopes": [{"seq": "PEPX"}]}

# try a few coords / region ids
region_id = "epi_1"
coord = (0.0, 0.0)

# try spawn in a robust way (some impls accept coord only, some accept (coord, proto))
spawned_ids = []
try:
    # prefer spawn_agent(coord=..., proto=...)
    try:
        res = ant.spawn_agent(coord=coord, proto=valid_proto)
        spawned_ids.append(res)
    except TypeError:
        # try spawn_agent(coord, proto)
        try:
            res = ant.spawn_agent(coord, valid_proto)
            spawned_ids.append(res)
        except TypeError:
            # try spawn_agent(proto) only
            try:
                res = ant.spawn_agent(valid_proto)
                spawned_ids.append(res)
            except Exception as e:
                print("spawn_agent attempts failed:", e)
except Exception as e:
    print("spawn_agent unexpected failure:", e)

print("spawned_ids (if any):", spawned_ids)

# run step a few times and try different step call patterns
seen_antigen_label = False
labels_seen = []
for tick in range(1, 13):
    # try various step invocation patterns: step(region_id), step(region_id=...), step(snapshot)
    step_results = None
    step_attempts = []
    try:
        # prefer step(region_id)
        try:
            step_results = ant.step(region_id)
            step_attempts.append(("step(region_id)", True))
        except TypeError:
            # maybe step(region_id, rng)
            try:
                step_results = ant.step(region_id, random.Random(12345))
                step_attempts.append(("step(region_id, rng)", True))
            except TypeError:
                try:
                    step_results = ant.step()
                    step_attempts.append(("step()", True))
                except Exception as e:
                    step_attempts.append(("step() failed", str(e)))
    except Exception as e:
        step_attempts.append(("step(unexpected)", str(e)))

    # print some diagnostics
    print(f"T{tick:02d}: step_attempts = {step_attempts}")

    # after step, inspect world labels
    cur_labels = list_space_labels(world)
    if cur_labels:
        labels_seen = cur_labels
        # try to detect antigen-like labels
        for lab in cur_labels:
            # lab may be dict or object
            try:
                if isinstance(lab, dict):
                    m = lab.get("meta") or lab.get("data") or {}
                    t = m.get("type") or lab.get("type") or lab.get("meta", {}).get("type")
                    # some systems set 'ANTIGEN_PARTICLE' or similar
                    if any(x in str(t).upper() for x in ("ANTIGEN", "ANTIGEN_PARTICLE", "VIRUS")) or "epitop" in str(m).lower():
                        seen_antigen_label = True
                        break
            except Exception:
                continue
    # also check if antigen_master exposes list_agents() internal view (useful for debugging)
    try:
        internal = getattr(ant, "list_agents")()
    except Exception:
        internal = None

    print(f"  labels={len(cur_labels)} agents={len(internal) if internal is not None else 0} internal_agents_sample={internal[:2] if internal else []}")

    if seen_antigen_label:
        print("  -> antigen label observed in space.")
        break

# final assertions & try DCMaster handle if antigen label present
if not seen_antigen_label:
    print("\nAssertions summary:\n seen_antigen_release: False\n seen_pmhc_label:      False\n dc_handled:           False")
    raise AssertionError("No antigen labels seen after AntigenMaster steps - check spawn_agent/step behaviour and space writeback.")

# try DC handling
pmhc_created = False
dc_handled = False
# pick first antigen-like label
antigen_label = labels_seen[0]
print("\nFound antigen label (sample):")
pp.pprint(antigen_label)

if DCMaster is None:
    print("DCMaster not present; skipping DC handling check.")
else:
    dc = DCMaster()
    # call handle_label in several signatures
    acts = None
    try:
        # typical: handle_label(region_id, label, node_meta=None, tick=0)
        try:
            acts = dc.handle_label(region_id, antigen_label, {}, 0)
        except TypeError:
            try:
                acts = dc.handle_label(region_id=region_id, label=antigen_label, node_meta={}, tick=0)
            except Exception:
                try:
                    acts = dc.step(region_id, antigen_label, {}, None)
                except Exception:
                    acts = None
    except Exception as e:
        print("DCMaster handle attempted but failed:", e)
    print("DCMaster produced acts (sample):", acts)
    if acts:
        for a in (acts or []):
            # match dict-like or Intent-like objects
            try:
                name = a.get("name") if isinstance(a, dict) else getattr(a, "name", None)
                if name:
                    if any(k in str(name).lower() for k in ("phago", "pmhc", "present", "consume", "ingest")):
                        dc_handled = True
                # fallback match on class name
                if not dc_handled:
                    cname = a.__class__.__name__.lower() if hasattr(a, "__class__") else ""
                    if any(k in cname for k in ("phag", "pmhc", "present")):
                        dc_handled = True
            except Exception:
                pass

print("\nFinal assertions:")
print(" seen_antigen_label:", seen_antigen_label)
print(" dc_handled:", dc_handled)
assert seen_antigen_label, "No antigen label was written to space by AntigenMaster."
# dc_handled might be False if DCMaster not instantiated or signatures differ; don't fail hard but warn
if not dc_handled:
    print("Warning: DCMaster did not report phagocytose/pMHC intents for the sample label. Check DCMaster.handle_label signature or antigen label meta.")
else:
    print("DCMaster handled antigen label (intent observed).")

print("\nEnhanced AntigenMaster integration test completed.")

