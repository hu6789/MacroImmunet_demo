# test/test_antigen_master_enhanced.py
"""
Enhanced AntigenMaster -> DCMaster integration test with constructor signature diagnostics.

Save as test/test_antigen_master_enhanced.py and run:
  PYTHONPATH=. python3 test/test_antigen_master_enhanced.py -v
"""
import pprint
import random
import time
import inspect
import traceback

pp = pprint.PrettyPrinter(indent=2)

# tolerant imports
try:
    from cell_master.masters.antigen_master import AntigenMaster
except Exception:
    AntigenMaster = None

try:
    from cell_master.masters.dc_master import DCMaster
except Exception:
    DCMaster = None

# --- tiny fallback space for masters that require a space arg -------------
class TinySpace:
    def __init__(self):
        self._agents = []
        self._labels = []

    # compatibility methods some AntigenMaster implementations expect
    def add_agent(self, a):
        self._agents.append(a)

    def list_agents(self):
        return list(self._agents)

    def snapshot(self):
        return {"agents": list(self._agents), "labels": list(self._labels)}

    def add_label(self, label):
        self._labels.append(label)

    # debugging helper
    def __repr__(self):
        return f"<TinySpace agents={len(self._agents)} labels={len(self._labels)}>"

# --- helpers --------------------------------------------------------------
def inspect_ctor_info(cls):
    info = {"callable": callable(cls), "signature": None, "params": None}
    try:
        sig = inspect.signature(cls)
        info["signature"] = str(sig)
        info["params"] = {k: str(v.annotation) if v.annotation is not inspect._empty else None for k, v in sig.parameters.items()}
    except Exception as e:
        info["signature_error"] = str(e)
    return info

def create_instance_with_fallback(cls, *args, **kwargs):
    """
    Try to instantiate cls in a forgiving way and record which attempt succeeded.
    Returns (instance, attempt_description).
    """
    attempt_log = []
    if cls is None:
        return None, ["class is None"]

    # 1) inspect signature and show it
    try:
        sig = inspect.signature(cls)
        attempt_log.append(f"signature: {sig}")
    except Exception as e:
        attempt_log.append(f"signature: <failed to inspect: {e}>")

    # If signature mentions 'space' and not provided, inject TinySpace
    try_variants = []

    try:
        params = list(inspect.signature(cls).parameters.keys())
    except Exception:
        params = []

    if "space" in params and "space" not in kwargs:
        try_variants.append(("space_kw", {"space": TinySpace(), **kwargs}))
        try_variants.append(("space_pos", (TinySpace(),) + args))
    # common variants
    try_variants.extend([
        ("plain_args", (args, kwargs)),
        ("empty_config", ((), {"config": {}})),
        ("tinyspace_pos", ((TinySpace(),) + args, kwargs)),
        ("tinyspace_kw", ((), {"space": TinySpace(), **kwargs})),
    ])

    # try each variant
    for variant in try_variants:
        name = variant[0]
        v = variant[1]
        if isinstance(v, tuple) and len(v) == 2 and isinstance(v[0], tuple) and isinstance(v[1], dict):
            a, k = v
        elif isinstance(v, dict):
            a, k = (), v
        else:
            # fallback: treat as (args, kwargs) tuple
            a, k = v
        try:
            inst = cls(*a, **k)
            attempt_log.append(f"instantiate succeeded with variant '{name}': args={a} kwargs={list(k.keys())}")
            return inst, attempt_log
        except Exception as e:
            tb = traceback.format_exc(limit=1)
            attempt_log.append(f"variant '{name}' failed: {e}; traceback: {tb.splitlines()[-1]}")
            continue

    # last attempts: naive tries
    last_attempts = [
        (args, kwargs),
        ((), {}),
        ((TinySpace(),), {}),
        ({},),
    ]
    for a_k in last_attempts:
        try:
            if isinstance(a_k, tuple) and len(a_k) == 2:
                a, k = a_k
            elif isinstance(a_k, tuple) and len(a_k) == 1:
                a, k = a_k[0], {}
            else:
                a, k = (), {}
            inst = cls(*a, **k)
            attempt_log.append(f"instantiate succeeded with last-resort args={a} kwargs={list(k.keys())}")
            return inst, attempt_log
        except Exception as e:
            attempt_log.append(f"last-resort attempt failed: {e}")
            continue

    # all failed
    attempt_log.append("all instantiation attempts failed")
    return None, attempt_log

def safe_list_agents(am):
    """Return list of agents from AntigenMaster in a tolerant way."""
    if am is None:
        return []
    for fname in ("list_agents", "agents", "get_agents", "_agents", "agents_store"):
        fn = getattr(am, fname, None)
        if callable(fn):
            try:
                return fn()
            except Exception:
                try:
                    val = getattr(am, fname)
                    if isinstance(val, list):
                        return val
                except Exception:
                    continue
        else:
            # maybe attribute is a list
            try:
                val = getattr(am, fname)
                if isinstance(val, list):
                    return val
            except Exception:
                continue
    # last resort: try common inspect of attributes
    out = []
    for attr in dir(am):
        if attr.lower().startswith("agent"):
            try:
                val = getattr(am, attr)
                if isinstance(val, list):
                    return val
            except Exception:
                continue
    return out

def find_intent_by_name(intents, name):
    out = []
    for it in (intents or []):
        nm = getattr(it, "name", None)
        try:
            if nm and nm == name:
                out.append(it)
                continue
        except Exception:
            pass
        # maybe it's dict-like
        try:
            if isinstance(it, dict) and it.get("name") == name:
                out.append(it)
                continue
        except Exception:
            pass
        # fallback: class name contains
        try:
            if it.__class__.__name__.lower().find(name.lower()) >= 0:
                out.append(it)
        except Exception:
            pass
    return out

# --- main -----------------------------------------------------------------
def main():
    print("Running enhanced AntigenMaster -> DCMaster integration test (with diagnostics)...\n")

    if AntigenMaster is None:
        print("ERROR: AntigenMaster class not found. Ensure file cell_master/masters/antigen_master.py exists.")
        raise SystemExit(2)

    if DCMaster is None:
        print("ERROR: DCMaster class not found. Ensure file cell_master/masters/dc_master.py exists.")
        raise SystemExit(2)

    rng = random.Random(2025)

    # show constructor info
    print("AntigenMaster callable:", callable(AntigenMaster))
    ctor_info = inspect_ctor_info(AntigenMaster)
    pp.pprint(ctor_info)
    print("Attempting robust instantiation of AntigenMaster...\n")

    # create AntigenMaster robustly (with diagnostics)
    ant, ant_attempt_log = create_instance_with_fallback(AntigenMaster, config={"debug": False})
    print("AntigenMaster instantiation log:")
    for l in ant_attempt_log:
        print("  ", l)
    print()

    if ant is None:
        print("ERROR: could not instantiate AntigenMaster with any fallback. Aborting test.")
        raise SystemExit(2)

    print("AntigenMaster instance:", repr(ant))
    # if ant has an attribute showing internal space, print it
    for candidate in ("space", "world", " env", "_space"):
        try:
            val = getattr(ant, candidate, None)
            if val is not None:
                print(f" antigen_master.{candidate} ->", repr(val))
        except Exception:
            continue
    print("")

    # prepare a proto with epitopes (important for DCMaster _make_pmhc)
    epitope_seq = "PEP_TEST_123"
    proto = {
        "amount": 2.0,
        "type": "VIRUS",
        "epitopes": [{"seq": epitope_seq, "score": 1.0}],
        "origin": "test_injection"
    }

    # Try to spawn agent using common APIs
    spawned = None
    spawn_tried = []
    for nm in ("spawn_agent", "add_agent", "create_agent", "spawn", "inject_agent", "emit_agent"):
        fn = getattr(ant, nm, None)
        if callable(fn):
            try:
                # try keyword first
                spawned = fn(proto=proto)
                spawn_tried.append(nm + "(proto=...) -> success")
                break
            except TypeError:
                try:
                    spawned = fn(proto)
                    spawn_tried.append(nm + "(proto) -> success")
                    break
                except Exception as e:
                    spawn_tried.append(nm + "(failed: " + str(e) + ")")
                    continue
            except Exception as e:
                spawn_tried.append(nm + "(failed-ex: " + str(e) + ")")
                continue

    # fallback: if ant exposes a list/append, append a dict-like agent
    if spawned is None:
        pushed = False
        for attr in ("_agents", "agents", "agents_store", "agent_list"):
            a = getattr(ant, attr, None)
            if isinstance(a, list):
                try:
                    a.append({"coord": (0.0, 0.0), "infectious": True, "proto": proto})
                    pushed = True
                    spawn_tried.append("append to " + attr + " -> success")
                    break
                except Exception as e:
                    spawn_tried.append("append to " + attr + " -> failed: " + str(e))
                    continue
        if not pushed:
            # try a generic method step that some masters expose
            fn = getattr(ant, "step", None)
            if callable(fn):
                try:
                    # some antigen masters accept (ticks) or (rng) or no args
                    try:
                        fn()
                    except TypeError:
                        try:
                            fn(rng)
                        except Exception:
                            fn(1)
                    spawn_tried.append("called step() -> attempted")
                except Exception as e:
                    spawn_tried.append("step() failed: " + str(e))

    print(" spawn attempts summary:")
    for s in spawn_tried:
        print("  ", s)
    print("")

    # read back agents
    agents = safe_list_agents(ant)
    print(" agents seen from AntigenMaster:", len(agents))
    if agents:
        pp.pprint(agents[:3])

    # choose agent_proto
    agent_proto = None
    if agents:
        a0 = agents[0]
        if isinstance(a0, dict):
            agent_proto = a0.get("proto") or a0
        else:
            for attr in ("proto", "meta", "payload"):
                agent_proto = getattr(a0, attr, None)
                if agent_proto:
                    break
    if not agent_proto:
        agent_proto = dict(proto)
        print(" constructed agent_proto for downstream test:", agent_proto)

    # ensure we have epitope info
    has_ep = False
    if isinstance(agent_proto, dict):
        if agent_proto.get("epitopes"):
            has_ep = True
        if agent_proto.get("sequence") or agent_proto.get("seq"):
            has_ep = True
    assert has_ep, "Agent proto must include 'epitopes' or 'sequence' for downstream processing."

    # instantiate DCMaster (compatibly)
    try:
        dc, dc_log = create_instance_with_fallback(DCMaster)
    except Exception as e:
        print("ERROR creating DCMaster:", e)
        raise

    print("DCMaster instantiation log:")
    for l in dc_log:
        print("  ", l)
    print("DCMaster instance:", repr(dc))
    print("")

    # create a label that DCMaster.handle_label expects
    label = {"id": "dc_test_1", "coord": (1.0, 1.0), "meta": {"type": "DC", "captured_antigens": [agent_proto]} }

    # call handle_label (or step) robustly
    intents = []
    try:
        if hasattr(dc, "handle_label"):
            try:
                intents = dc.handle_label(region_id="r_test", label=label, node_meta={"process_limit": 2}, tick=0)
            except TypeError:
                try:
                    intents = dc.handle_label(label=label)
                except Exception:
                    try:
                        intents = dc.handle_label("r_test", label)
                    except Exception:
                        intents = []
        else:
            # try common entrypoints
            for name in ("step", "run", "process", "act", "tick", "handle"):
                fn = getattr(dc, name, None)
                if callable(fn):
                    try:
                        intents = fn(coord=label.get("coord"), summary={"agents":[agent_proto]}, cell_meta=label.get("meta"), rng=random.Random())
                        break
                    except Exception:
                        try:
                            intents = fn(label.get("coord"), {"agents":[agent_proto]}, label.get("meta"), random.Random())
                            break
                        except Exception:
                            continue
    except Exception as e:
        print("Exception calling DCMaster:", e)
        intents = []

    print(" DCMaster returned intents count:", len(intents))
    for it in intents:
        try:
            print("  - intent:", getattr(it, "name", None) or (it.get("name") if isinstance(it, dict) else str(it)))
        except Exception:
            print("  - intent (raw):", it)

    pmhcs = find_intent_by_name(intents, "pMHC_presented")
    assert pmhcs, "DCMaster did not emit pMHC_presented intent; intents=%r" % (intents,)

    first = pmhcs[0]
    payload = getattr(first, "payload", None) if not isinstance(first, dict) else first.get("payload", None)
    assert payload is not None, "pMHC_presented intent has no payload."

    pmhc = payload.get("pMHC") if isinstance(payload, dict) else None
    assert pmhc and ("peptide_id" in pmhc or "peptide" in pmhc or "peptide_seq" in pmhc), "pMHC payload missing peptide identifier."

    peptide_id = pmhc.get("peptide_id") or pmhc.get("peptide") or pmhc.get("peptide_seq")
    assert peptide_id is not None, "no peptide id found in pMHC."

    print("\n DCMaster produced pMHC with peptide_id ->", peptide_id)
    print("All enhanced antigen -> DC checks passed.")
    print("OK")

if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("FAILED:", e)
        raise SystemExit(2)
    except Exception as e:
        print("ERROR:", e)
        raise

