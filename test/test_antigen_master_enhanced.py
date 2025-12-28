# test/test_antigen_master_enhanced.py
"""
Robust enhanced AntigenMaster -> DCMaster integration test.

This version:
 - actively tries to spawn agents using spawn_agent(...) (internal queue)
 - then calls step(...) with a region_id (or other plausible signatures) to flush agents into space
 - inspects ant.list_agents() (if available) and space.get_labels()/snapshot()
 - prints detailed diagnostics per attempt
"""
import time
import random
import traceback

# imports (fail loudly if Space missing)
try:
    from scan_master.space import Space
except Exception as e:
    raise RuntimeError("scan_master.space.Space is required but could not be imported") from e

from cell_master.masters.antigen_master import AntigenMaster
from cell_master.masters.dc_master import DCMaster

def labels_from_space(space):
    if hasattr(space, "get_labels") and callable(getattr(space, "get_labels")):
        try:
            return list(space.get_labels())
        except Exception:
            pass
    snap = getattr(space, "snapshot", None)
    if callable(snap):
        try:
            s = snap()
            if isinstance(s, dict):
                return s.get("labels", []) or []
        except Exception:
            pass
    return list(getattr(space, "_local_labels", []) or [])

def agents_from_space(space):
    if hasattr(space, "get_agents") and callable(getattr(space, "get_agents")):
        try:
            return list(space.get_agents())
        except Exception:
            pass
    snap = getattr(space, "snapshot", None)
    if callable(snap):
        try:
            s = snap()
            if isinstance(s, dict):
                return s.get("agents", []) or []
        except Exception:
            pass
    return list(getattr(space, "_local_agents", []) or [])

def looks_like_antigen_label(L):
    if not isinstance(L, dict):
        return False
    meta = L.get("meta", {}) if isinstance(L, dict) else {}
    t = (meta.get("type") or "").upper() if isinstance(meta, dict) else ""
    if any(k in t for k in ("ANTIGEN", "VIRUS", "ANTIGEN_PARTICLE")):
        return True
    if "antigen" in str(L.get("id","")).lower():
        return True
    return False

def looks_like_pmhc_label(L):
    if not isinstance(L, dict):
        return False
    meta = L.get("meta", {}) if isinstance(L, dict) else {}
    t = (meta.get("type") or "").upper() if isinstance(meta, dict) else ""
    if any(k in t for k in ("MHC", "PEPTIDE", "PMHC")):
        return True
    if isinstance(meta, dict) and meta.get("pMHC"):
        return True
    return False

def try_spawn_variants(ant, rng):
    """
    Try a set of plausible spawn_agent signatures until one doesn't raise TypeError.
    Return (succeeded, info_list) where info_list contains attempted patterns and exceptions/results.
    """
    attempts = []
    if not hasattr(ant, "spawn_agent"):
        return False, [("spawn_agent not present", False, "no spawn_agent")]
    patterns = [
        ("spawn_agent()", lambda: ant.spawn_agent()),
        ("spawn_agent(rng=rng)", lambda: ant.spawn_agent(rng=rng)),
        ("spawn_agent(coord=(0,0))", lambda: ant.spawn_agent(coord=(0.0,0.0))),
    ]
    for name, fn in patterns:
        try:
            res = fn()
            attempts.append((name, True, repr(res)))
            return True, attempts
        except TypeError as te:
            attempts.append((name, False, "TypeError: " + str(te)))
        except Exception as e:
            attempts.append((name, False, f"Exception: {e.__class__.__name__}: {e}"))
    return False, attempts

def try_step_with_region(ant, region_id, rng):
    """Try to call ant.step with plausible region/label id signatures to flush agents into space."""
    attempts = []
    candidates = [
        (f"step(region_id={region_id}, rng=rng)", lambda: ant.step(region_id=region_id, rng=rng)),
        (f"step({region_id})", lambda: ant.step(region_id) if False else ant.step(region_id)),  # try positional if allowed
        (f"step(region_id={region_id})", lambda: ant.step(region_id=region_id)),
        ("step()", lambda: ant.step()),  # fallback - may require different args
    ]
    for name, fn in candidates:
        try:
            res = fn()
            attempts.append((name, True, repr(res)))
        except TypeError as te:
            attempts.append((name, False, "TypeError: " + str(te)))
        except AttributeError as ae:
            attempts.append((name, False, "AttributeError: " + str(ae)))
        except Exception as e:
            attempts.append((name, False, f"Exception: {e.__class__.__name__}: {e}"))
    return attempts

def main():
    rng = random.Random(2025)

    # make space for integration
    space = Space()

    # instantiate AntigenMaster robustly (try common ctor forms)
    ant = None
    try:
        ant = AntigenMaster(space=space, config={"debug": False})
    except TypeError:
        try:
            ant = AntigenMaster(space, {"debug": False})
        except Exception:
            try:
                ant = AntigenMaster({"debug": False})
            except Exception:
                ant = AntigenMaster()

    # instantiate DCMaster
    try:
        dc = DCMaster(space=space, config={"debug": False})
    except TypeError:
        try:
            dc = DCMaster(space)
        except Exception:
            dc = DCMaster()

    print("AntigenMaster callable sample:", [n for n in dir(ant) if not n.startswith("_")][:60])
    print("AntigenMaster has spawn_agent?:", hasattr(ant, "spawn_agent"))
    print("AntigenMaster has list_agents?:", hasattr(ant, "list_agents"))
    print("Space has snapshot?:", callable(getattr(space, "snapshot", None)))
    print("Space has get_labels?:", callable(getattr(space, "get_labels", None)))
    print("Space has get_agents?:", callable(getattr(space, "get_agents", None)))
    print("---- starting ticks ----\n")

    seen_antigen = False
    seen_pmhc = False
    dc_handled = False

    TICKS = 12
    for tick in range(1, TICKS + 1):
        info_msgs = []
        # 1) actively try to spawn a few agents each tick using variants
        spawn_ok, spawn_attempts = try_spawn_variants(ant, rng)
        info_msgs.append(("spawn_attempts", spawn_attempts))

        # 2) pick a region_id to call step with: prefer existing label ids or fallback to 'epi_1'
        labels_now = labels_from_space(space)
        if labels_now:
            region_id = labels_now[0].get("id")
        else:
            # try to detect local labels storage
            local = getattr(space, "_local_labels", None) or getattr(space, "labels", None) or []
            if local:
                try:
                    region_id = local[0].get("id")
                except Exception:
                    region_id = "epi_1"
            else:
                region_id = "epi_1"

        # 3) call step variants that include region_id (this is the crucial change)
        step_attempts = try_step_with_region(ant, region_id, rng)
        info_msgs.append(("step_attempts", step_attempts))

        # 4) inspect ant internal list_agents if present
        internal_agents = []
        if hasattr(ant, "list_agents") and callable(getattr(ant, "list_agents")):
            try:
                internal_agents = list(ant.list_agents())
            except Exception as e:
                internal_agents = [{"error": str(e)}]

        # 5) inspect space
        labels = labels_from_space(space)
        agents = agents_from_space(space)

        # 6) let DC try to handle labels
        handled_this_tick = False
        for L in labels:
            try:
                if hasattr(dc, "handle_label"):
                    out = dc.handle_label(region_id=L.get("id"), label=L, node_meta=L.get("meta", {}), tick=tick)
                    if out:
                        handled_this_tick = True
                else:
                    try:
                        out = dc.step(coord=L.get("coord"), summary={"agents": agents}, cell_meta=L.get("meta", {}), rng=rng)
                        if out:
                            handled_this_tick = True
                    except Exception:
                        pass
            except Exception:
                pass

        if handled_this_tick:
            dc_handled = True

        # update seen flags
        if any(looks_like_antigen_label(L) for L in labels):
            seen_antigen = True
        if any(looks_like_pmhc_label(L) for L in labels):
            seen_pmhc = True

        # Print diagnostics for this tick
        print("T%02d: labels=%d agents=%d internal_agents=%d  seen_antigen=%s seen_pmhc=%s dc_handled=%s  region_id=%r" % (
            tick, len(labels), len(agents), (len(internal_agents) if isinstance(internal_agents, list) else 0),
            seen_antigen, seen_pmhc, dc_handled, region_id
        ))
        # print brief attempt summary
        for k, v in info_msgs:
            print("   -", k, ":", v if len(str(v))<400 else (str(v)[:400]+"..."))
        # tiny pause
        time.sleep(0.01)

    # final asserts / summary
    print("\nAssertions summary:")
    print(" seen_antigen_release:", seen_antigen)
    print(" seen_pmhc_label:     ", seen_pmhc)
    print(" dc_handled:          ", dc_handled)

    if not seen_antigen:
        print("\nNOTE: No antigen labels were observed in Space. Check:")
        print(" - ant.list_agents() contents (we printed internal_agents length each tick).")
        print(" - ant.step(region_id=...) signature / required args.")
        raise SystemExit(2)

    if not seen_pmhc or not dc_handled:
        print("\nNOTE: Antigen(s) seen, but DC did not produce pMHC/presenting intents. Check DCMaster.handle_label signature and Label meta content.")
        raise SystemExit(3)

    print("All enhanced antigen->DC checks passed.")
    return 0

if __name__ == "__main__":
    main()

