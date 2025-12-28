"""
Step1 enhanced minimal loop — include NaiveT / Th1 / CTL sampling.

Saves you from having to hunt through many tests: this will explicitly
call EpithelialMaster, DCMaster, NativeTMaster, Th1Master, CTLMaster each tick
and print human-friendly action names.

Run:
  PYTHONPATH=. python3 test/test_step1_minicl_loop_with_Tcells.py -q
"""
import random
import time

# cell masters
from cell_master.masters.epithelial_master import EpithelialMaster
from cell_master.masters.dc_master import DCMaster
from cell_master.masters.native_t_master import NativeTMaster
from cell_master.masters.th1_master import Th1Master
from cell_master.masters.ctl_master import CTLMaster

# ----------------- small helpers -----------------
def action_name(a):
    if isinstance(a, dict):
        return a.get("name") or a.get("action") or a.get("type")
    return getattr(a, "name", None) or getattr(a, "__class__", None).__name__

def action_payload(a):
    if isinstance(a, dict):
        return a.get("payload") or {}
    return getattr(a, "payload", {}) or {}

def act_names(actions):
    return [action_name(a) for a in (actions or [])]

# ----------------- Tiny world --------------------
class TinySpace:
    def __init__(self):
        self._local_labels = []   # each: {"id","coord","meta","type"}
        self._local_agents = []   # each: {"coord","infectious","proto"}

    # label helpers
    def add_label(self, label):
        self._local_labels.append(label)

    def find_labels_by_type(self, typ):
        return [l for l in self._local_labels if (l.get("meta",{}).get("type") == typ or l.get("type")==typ)]

    def pop_labels_by_type(self, typ):
        found = []
        remaining = []
        for l in self._local_labels:
            if (l.get("meta",{}).get("type") == typ) or (l.get("type")==typ):
                found.append(l)
            else:
                remaining.append(l)
        self._local_labels = remaining
        return found

    # agent helpers
    def add_agent(self, coord=(0,0), amount=1.0):
        self._local_agents.append({"coord":coord, "infectious": True, "proto":{"amount": amount}})

    def pop_agent(self):
        try:
            return self._local_agents.pop(0)
        except Exception:
            return None

    def snapshot(self):
        # aggregator-style minimal snapshot
        return {
            "labels": list(self._local_labels),
            "agents": list(self._local_agents)
        }

# ----------------- instantiate masters & world -----------------
rng = random.Random(2025)
epi = EpithelialMaster({"debug": False})
dc = DCMaster()
native_t = NativeTMaster()
th1 = Th1Master()
ctl = CTLMaster()

world = TinySpace()

# seed: infected epithelial + DC + naive T + Th1 + CTL
world.add_label({"id":"epi_1","coord":(0.0,0.0),"meta":{"type":"EPITHELIAL","state":"infected_productive","viral_load":30.0,"release_timer":0}})
world.add_label({"id":"dc_1","coord":(1.8,0.0),"meta":{"type":"DC"}})
world.add_label({"id":"t_naive_1","coord":(5.0,5.0),"meta":{"type":"NAIVE_T"}})
world.add_label({"id":"th1_1","coord":(6.0,5.0),"meta":{"type":"TH1"}})
world.add_label({"id":"ctl_1","coord":(1.0,0.0),"meta":{"type":"CTL"}})

# small initial environment agents near DC
for i in range(3):
    world.add_agent(coord=(1.9 - 0.02*i, 0.0 + 0.01*i), amount=1.0)

# tracking flags
seen_release = False
seen_pmhc_label = False
naive_seen_activation = False

TICKS = 12
print(">>> running Step1 enhanced minimal loop for", TICKS, "ticks")

for tick in range(1, TICKS+1):
    snap = world.snapshot()
    print(f"\n=== TICK {tick}")

    # --- Epithelial labels ---
    for lab in [l for l in snap["labels"] if l.get("meta",{}).get("type")=="EPITHELIAL"]:
        cid = lab["id"]
        meta = lab["meta"]
        coord = lab.get("coord")
        acts = epi.step(coord=coord, summary=snap, cell_meta=meta, rng=rng)
        print(f"[{cid}] EPI ->", act_names(acts))
        for a in (acts or []):
            nm = action_name(a)
            pl = action_payload(a)
            if nm == "release_antigen":
                seen_release = True
                # spawn a few env agents near epithelial
                for i in range(2):
                    world.add_agent(coord=(coord[0]+0.02*(i+1), coord[1]+0.01*(i+1)), amount=pl.get("amount",1.0))
            if nm == "spawn_antigen_agents":
                cnt = int(pl.get("count",1))
                for i in range(cnt):
                    world.add_agent(coord=(coord[0]+0.01*(i+1), coord[1]+0.005*(i+1)), amount=1.0)

    # refresh snapshot after possible new agents
    snap = world.snapshot()

    # --- DC labels ---
    for lab in [l for l in snap["labels"] if l.get("meta",{}).get("type")=="DC"]:
        cid = lab["id"]
        meta = lab["meta"]
        coord = lab.get("coord")
        acts = dc.step(coord=coord, summary=snap, cell_meta=meta, rng=rng)
        print(f"[{cid}] DC ->", act_names(acts))
        for a in (acts or []):
            nm = action_name(a)
            pl = action_payload(a)
            if nm and "pmhc" in str(nm).lower() or nm == "pMHC_presented":
                # create a pMHC label for T-cell sampling
                pmhc = pl.get("pMHC") if isinstance(pl, dict) else pl
                label = {"id": f"pmhc_{int(time.time()*1000)%100000}", "coord": coord, "meta": {"type":"MHC_PEPTIDE","pMHC":pmhc}}
                world.add_label(label)
                seen_pmhc_label = True
            if nm and ("phag" in str(nm).lower() or nm=="phagocytose"):
                # consume an agent if available
                world.pop_agent()

    # refresh snapshot
    snap = world.snapshot()

    # --- T cell sampling: NaiveT, Th1, CTL get to see pMHC labels in world ---
    pmhcs = [l for l in snap["labels"] if l.get("meta",{}).get("type")=="MHC_PEPTIDE"]
    if pmhcs:
        # call naive T, th1, ctl once per tick; they may react to pMHC label(s)
        for tlabel in pmhcs:
            # native T
            nid = "t_naive_1"
            meta = next((l["meta"] for l in world._local_labels if l["id"]==nid), {})
            acts = native_t.step(coord=tuple(meta.get("coord",(5.0,5.0))), summary=snap, cell_meta=meta, rng=rng)
            nms = act_names(acts)
            print(f"[{nid}] NAIVE_T ->", nms)
            # if native_t emits differentiate/differentiate intent, mark activation
            if any("differentiat" in str(x).lower() for x in nms) or any("activate" in str(x).lower() for x in nms):
                naive_seen_activation = True

            # Th1
            nid2 = "th1_1"
            meta2 = next((l["meta"] for l in world._local_labels if l["id"]==nid2), {})
            acts2 = th1.step(coord=tuple(meta2.get("coord",(6.0,5.0))), summary=snap, cell_meta=meta2, rng=rng)
            print(f"[{nid2}] TH1 ->", act_names(acts2))

            # CTL
            nid3 = "ctl_1"
            meta3 = next((l["meta"] for l in world._local_labels if l["id"]==nid3), {})
            acts3 = ctl.step(coord=tuple(meta3.get("coord",(1.0,0.0))), summary=snap, cell_meta=meta3, rng=rng)
            print(f"[{nid3}] CTL ->", act_names(acts3))

    else:
        # still call them (so you see their baseline behaviour)
        acts = native_t.step(coord=(5.0,5.0), summary=snap, cell_meta=next((l["meta"] for l in world._local_labels if l["id"]=="t_naive_1"), {}), rng=rng)
        print("[t_naive_1] NAIVE_T ->", act_names(acts))
        acts2 = th1.step(coord=(6.0,5.0), summary=snap, cell_meta=next((l["meta"] for l in world._local_labels if l["id"]=="th1_1"), {}), rng=rng)
        print("[th1_1] TH1 ->", act_names(acts2))
        acts3 = ctl.step(coord=(1.0,0.0), summary=snap, cell_meta=next((l["meta"] for l in world._local_labels if l["id"]=="ctl_1"), {}), rng=rng)
        print("[ctl_1] CTL ->", act_names(acts3))

    # small decay/trim to avoid explosion
    if world._local_agents and rng.random() < 0.25:
        world._local_agents.pop(0)

# final summary
print("\nAssertions summary:")
print(" seen_release:", seen_release)
print(" seen_pmhc_label:", seen_pmhc_label)
print(" naive_seen_activation:", naive_seen_activation)
print("END")

