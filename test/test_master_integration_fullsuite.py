# test/test_master_integration_fullsuite.py
import time
import random
from scan_master.behavior_to_intent import normalize_action
from cell_master.masters.epithelial_master import EpithelialMaster
from cell_master.masters.dc_master import DCMaster
from cell_master.masters.native_t_master import NativeTMaster
from cell_master.masters.th1_master import Th1Master
from cell_master.masters.ctl_master import CTLMaster

# tiny fake world like demo uses (keep compatibility)
class TinySpace:
    def __init__(self):
        self._local_agents = []
        self._local_labels = []

    def add_agent(self, a):
        self._local_agents.append(a if isinstance(a, dict) else a.as_dict())

    def add_label(self, l):
        self._local_labels.append(l)

    def snapshot(self):
        return {"agents": list(self._local_agents), "labels": list(self._local_labels)}

# Setup
rng = random.Random(2025)
epi_master = EpithelialMaster({"debug": False})
dc_master = DCMaster()
native_t = NativeTMaster()
th1_master = Th1Master()
ctl_master = CTLMaster()

world = TinySpace()
# seed
world.add_label({"id": "epi_1", "coord": (0.0,0.0), "meta": {"type":"EPITHELIAL", "state":"infected_productive", "viral_load": max(25.0, epi_master.initial_viral_load*5.0), "release_timer":0}})
world.add_label({"id": "dc_1", "coord": (1.8,0.0), "meta": {"type":"DC"}})
world.add_label({"id": "t_naive_1", "coord": (5.0,5.0), "meta":{"type":"NAIVE_T"}})
for i in range(3):
    world.add_agent({"coord": (1.9 - 0.02*i, 0.0 + 0.01*i), "infectious": True, "proto": {"amount":1.0}})

TYPE_TO_MASTER = {"EPITHELIAL": epi_master, "DC": dc_master, "NAIVE_T": native_t, "TH1": th1_master, "CTL": ctl_master}

# metrics to assert
seen_release = False
seen_pmhc_label = False
dc_did_handle = False

TICKS = 40
for tick in range(1, TICKS+1):
    snap = world.snapshot()
    labels = list(snap.get("labels", []))
    agents = list(snap.get("agents", []))

    nodes = [{"node_id": l.get("id"), "coord": l.get("coord"), "meta": l.get("meta"), "summary":{"agents":agents}} for l in labels]
    for node in nodes:
        nid = node["node_id"]
        meta = node["meta"] or {}
        master = TYPE_TO_MASTER.get(meta.get("type"))
        if not master:
            continue

        # try a few call entrypoints (compat)
        acts = []
        for name in ("step","handle","run","process","tick","act","__call__"):
            fn = getattr(master, name, None)
            if callable(fn):
                try:
                    acts = fn(coord=node["coord"], summary=node["summary"], cell_meta=meta, rng=rng) or []
                except TypeError:
                    try:
                        acts = fn(node["coord"], node["summary"], meta, rng) or []
                    except Exception:
                        try:
                            acts = fn(node["coord"], node["summary"], meta) or []
                        except Exception:
                            acts = []
                except Exception:
                    acts = []
                break

        # normalize & enact simple env effects
        for a in acts or []:
            n = normalize_action(a, src=master.__class__.__name__)
            t = n.get("type","").lower()
            if "release" in t or "spawn" in t:
                seen_release = True
                amt = n.get("payload", {}).get("amount", 1.0)
                for i in range(3):
                    world.add_agent({"coord": (node["coord"][0] + 0.02*(i+1), node["coord"][1] + 0.01*(i+1)), "infectious": True, "proto":{"amount":amt}})
            if "pmhc" in t or "present" in t:
                # create a pmhc label
                pmhc_label = {"id": f"pmhc_{int(time.time()*1000)%100000}", "coord": node["coord"], "meta": {"type":"MHC_PEPTIDE", "pMHC": n.get("payload", {}).get("pMHC", {"peptide_id":"X"})}}
                world.add_label(pmhc_label)
                seen_pmhc_label = True
            if "phag" in t or "consume" in t or "ingest" in t:
                dc_did_handle = True
                # remove one agent if exists
                if world._local_agents:
                    world._local_agents.pop(0)

# assertions
print("Assertions:")
print(" seen_release:", seen_release)
print(" seen_pmhc_label:", seen_pmhc_label)
print(" dc_did_handle:", dc_did_handle)

if not seen_release:
    raise SystemExit("FAIL: no antigen release observed")
if not seen_pmhc_label:
    raise SystemExit("FAIL: no pMHC label generated")
if not dc_did_handle:
    raise SystemExit("FAIL: DC never consumed/phagocytosed")
print("OK: integration checks passed")

