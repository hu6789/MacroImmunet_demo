# test/test_quick_behaviour_call.py
import sys, os
sys.path.append(os.path.abspath("."))

# behaviour registry / loader API (demo project uses registry object)
# we avoid pkgutil/__path__ scanning and rely on the package-exported registry
try:
    from cell_master.behaviour_library import registry as reg_mod
except Exception:
    # fallback if package layout differs
    reg_mod = None

# minimal fake cell & env (covers needs of multiple behaviours)
class FakeCell:
    def __init__(self):
        self.id = "cell_demo_1"
        self.coord = (0.0, 0.0)
        self.position = self.coord
        # meta fields commonly used by behaviors
        self.meta = {
            "viral_load": 10,
            "infection_timer": 0,
            "antigen_load": 0
        }
        # for present_v1
        self.captured_antigens = [{"epitopes":[{"seq":"PEPSEQ1"}], "sequence": "AAAAAAAAA"}]
        # for tcr_scan
        self.tcr_repertoire = [{"target_peptide": "PEPSEQ1"}]
        # other convenience attributes
        self.state = None
        self.present_list = []

        # ===== added: default current target so perforin behavior has something to aim at =====
        # this makes the perforin_apoptosis_v1 smoke-test deterministic-friendly
        self.current_target = "dummy_target_0"

class FakeEnv:
    def __init__(self):
        self.events = []
        self.fields = {}
        self.intents = []
        self.spawned = []
        self.tick = 0
        # storage for pMHC collect / sampling
        self._pmhcs = []

    # field helpers
    def add_to_field(self, field, coord, amount):
        self.fields.setdefault(field, 0.0)
        try:
            self.fields[field] += amount
        except Exception:
            # defensive: if field stored as int, convert
            self.fields[field] = float(self.fields[field]) + float(amount)

    def read_field(self, field, coord):
        return float(self.fields.get(field, 0.0))

    def has_field(self, name):
        # demo: pretend common fields exist
        return True

    # event / intent / spawn helpers
    def emit_event(self, name, payload):
        self.events.append((name, payload))

    def emit_intent(self, name, payload):
        self.intents.append((name, payload))

    def spawn_cell(self, coord, cell_type="child", meta=None):
        cid = f"{cell_type}_{len(self.spawned)}"
        self.spawned.append({"id": cid, "coord": coord, "cell_type": cell_type, "meta": meta or {}})
        return cid

    def get_cell(self, cid):
        # test stub: no other cells present
        return None

    # --- added for TCR_scan compatibility ---
    def collect_pMHC_near(self, coord, radius):
        """
        Return list of pMHC candidate dicts near coord.
        Tests will seed self._pmhcs when needed.
        Each pMHC should be a dict with keys like 'pMHC_id','peptide_id','mhc_type'.
        """
        # ignore radius for simplicity (demo)
        return list(self._pmhcs)

    def compute_affinity(self, pmhc, tcr):
        """
        Minimal affinity: if tcr is dict with 'target_peptide' and it equals pmhc['peptide_id'],
        return high affinity (1.0), else 0.0.
        Accepts (pmhc, tcr) or (tcr, pmhc) signatures; handle both.
        """
        try:
            # common signature (pmhc, tcr)
            pid = pmhc.get("peptide_id") or pmhc.get("epitope_seq")
            if isinstance(tcr, dict):
                target = tcr.get("target_peptide")
                return 1.0 if (target and pid and target == pid) else 0.0
            return 0.0
        except Exception:
            # maybe called with (tcr, pmhc)
            try:
                pid = tcr.get("peptide_id") or tcr.get("epitope_seq")
                if isinstance(pmhc, dict):
                    target = pmhc.get("target_peptide")
                    return 1.0 if (target and pid and target == pid) else 0.0
            except Exception:
                pass
        return 0.0

# helper assertion for tests
def expect(ok, msg):
    if not ok:
        print("[FAIL]", msg)
        raise AssertionError(msg)
    else:
        print("[OK]", msg)

def run_single_behavior(registry, name, cell, env, params=None, payload=None):
    """
    Use the registry wrapper to sample/run the behavior if available.
    Fallback: if registry.get returns a raw function, call it directly.
    Returns (actions, env_side_effects_summary)
    """
    params = params or {}
    payload = payload or {}

    # try registry API first
    runner = None
    try:
        # registry may be a callable factory or the registry object itself
        if callable(registry) and not hasattr(registry, "get"):
            # registry is a factory or constructor; call to obtain registry object
            try:
                registry_obj = registry()
            except Exception:
                registry_obj = registry
        else:
            registry_obj = registry
        # get runner (could be None)
        runner = getattr(registry_obj, "get", lambda n: None)(name)
    except Exception:
        runner = None

    actions = []
    # registry object in this project exposes sample_and_run or .run-like methods in some versions
    if runner:
        # prefer sample_and_run if present on registry object (some registries expose helpers)
        try:
            # if registry object exposes sample_and_run helper we should call on the registry,
            # otherwise try to call runner directly (it might be the callable function)
            if hasattr(registry, "sample_and_run"):
                out = registry.sample_and_run(name, cell, env, params=params, payload=payload)
            elif hasattr(registry_obj, "sample_and_run"):
                out = registry_obj.sample_and_run(name, cell, env, params=params, payload=payload)
            else:
                # runner might be a callable function itself
                out = runner(cell, env, params=params, payload=payload)
            # normalize
            if isinstance(out, dict) and "actions" in out:
                actions = out.get("actions") or out.get("result") or []
            else:
                actions = out or []
        except Exception:
            # fallback: runner may be a callable behavior function itself
            try:
                func = runner
                actions = func(cell, env, params=params, payload=payload) or []
            except Exception:
                actions = []
    else:
        # no registry entry: nothing to run
        actions = []

    # summarize env side-effects for lightweight assertions
    side_effects = {
        "events": list(env.events),
        "fields": dict(env.fields),
        "intents": list(env.intents),
        "spawned": list(env.spawned)
    }
    return actions, side_effects

def main():
    # obtain registry object (callable that returns registry in some layouts)
    if reg_mod is None:
        print("ERROR: could not import cell_master.behaviour_library.registry")
        return

    try:
        registry = reg_mod()
    except TypeError:
        # reg_mod might already be the registry object
        registry = reg_mod

    available = registry.list() if hasattr(registry, "list") else []
    print("behaviours loaded:", available)

    c = FakeCell()
    env = FakeEnv()

    # a prioritized list of demo behaviours to smoke-test (include the new ones)
    candidates = [
        # release/replicate family (existing)
        "handle_release_on_death",
        "antigen_release_v1",
        "replicate_intracellular",
        # new / additional behaviours we added
        "natural_apoptosis_v1",
        "random_walk_v1",
        "proliferate_v1",
        # other common demo behaviours
        "perforin_apoptosis_v1",
        "phagocytose_v1",
        "present_v1",
        "TCR_scan_v1",
        "differentiate_v1",
        "secrete_v1",
    ]

    # run each candidate that's available in registry
    any_run = False
    for name in candidates:
        print("\n--- trying behavior:", name)
        if not getattr(registry, "get", lambda n: None)(name):
            print("  not present in registry; skipping")
            continue
        any_run = True
        # prepare fresh cell/env per behavior to avoid cross-talk
        cell = FakeCell()
        env = FakeEnv()

        # --- seed antigen for phagocytose smoke test ---
        # minimal seeding so phagocytose_v1 has field to consume and produces observable side-effect
        if name == "phagocytose_v1":
            env.add_to_field("Field_Antigen_Density", cell.coord, 2)

        # --- seed pMHC for TCR_scan smoke test ---
        # minimal pMHC candidate that matches FakeCell.tcr_repertoire target_peptide
        if name == "TCR_scan_v1":
            env._pmhcs = [
                {"pMHC_id": "pm_0", "peptide_id": "PEPSEQ1", "mhc_type": "MHC_I"}
            ]

        # tweak params/payload depending on behavior to make deterministic-ish
        params = {}
        payload = {}
        if "release" in name or "replicate" in name:
            params = {"release_probability": 1.0, "burst_yield": 5, "replication_rate_per_tick": 1.2}
        if "proliferate" in name:
            # force proliferation
            params = {"probability": 1.0, "max_children": 1}
        if "random_walk" in name:
            params = {"step_size": 1}

        actions, side = run_single_behavior(registry, name, cell, env, params=params, payload=payload)
        print("  Returned actions:", actions)
        print("  Env fields:", env.fields)
        print("  Env events:", env.events)
        print("  Env intents:", env.intents)
        print("  Env spawned:", env.spawned)

        # Basic assertions: actions non-empty AND some side-effect observed
        expect(isinstance(actions, list), f"{name} returned actions list")
        expect(len(actions) > 0, f"{name} produced at least one action")

        side_present = bool(side["events"] or side["fields"] or side["intents"] or side["spawned"])
        expect(side_present, f"{name} produced observable side effect (events/fields/intents/spawned)")

    if not any_run:
        print("No behaviors available to run (registry empty?)")
    else:
        print("\nAll tested behaviours executed basic smoke checks.")

if __name__ == "__main__":
    main()

