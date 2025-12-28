# test/test_antigen_master.py
"""
Smoke & unit-ish tests for cell_master.masters.antigen_master.AntigenMaster

Run as:
    PYTHONPATH=. python3 test/test_antigen_master.py
"""

from typing import List, Dict, Any, Tuple
import math
import random
import sys
import time

# simple expect helper like other tests in repo
def expect(ok, msg):
    if not ok:
        print("[FAIL]", msg)
        raise AssertionError(msg)
    else:
        print("[OK]", msg)


# Import the AntigenMaster implementation (placed under cell_master/masters/)
try:
    from cell_master.masters.antigen_master import AntigenMaster
except Exception as e:
    print("ERROR: cannot import AntigenMaster:", e)
    raise

# ----- FakeSpace for tests --------------------------------------------------
class FakeSpace:
    def __init__(self):
        # region -> list of label dicts
        self.regions = {}

    @staticmethod
    def _dist(a: Tuple[float,float], b: Tuple[float,float]) -> float:
        return math.hypot(a[0]-b[0], a[1]-b[1])

    def add_label(self, region: str, label: Dict[str, Any]):
        self.regions.setdefault(region, []).append(label)

    def get_labels(self, region: str) -> List[Dict[str,Any]]:
        # return the actual stored label dicts
        return self.regions.get(region, [])

    def get_labels_in_radius(self, region: str, center: Tuple[float,float], radius: float) -> List[Dict[str,Any]]:
        out = []
        for l in self.regions.get(region, []):
            coord = l.get("coord") or l.get("position") or None
            if coord is None:
                continue
            if self._dist(tuple(coord), tuple(center)) <= float(radius):
                out.append(l)
        return out

# ----- Tests ---------------------------------------------------------------

def test_spawn_and_list():
    s = FakeSpace()
    am = AntigenMaster(space=s, rng=random.Random(123), config={"default_step_size": 0.01})
    aid = am.spawn_agent((0.0, 0.0), viral_load=2.0)
    got = am.list_agents()
    ids = {a["id"] for a in got}
    expect(aid in ids, "spawn_agent produced agent visible via list_agents()")
    expect(len(got) == 1, "one agent present after single spawn")

def test_move_action_emitted():
    s = FakeSpace()
    rng = random.Random(42)
    am = AntigenMaster(space=s, rng=rng, config={"default_step_size": 0.5, "infection_radius": 0.1})
    aid = am.spawn_agent((0.0, 0.0), viral_load=1.0)
    actions = am.step("regionX", tick=0)
    # must include a move action for our agent
    move_actions = [a for a in actions if a.get("name") == "agent_moved" and a.get("agent_id") == aid]
    expect(len(move_actions) == 1, "step emitted single agent_moved for agent")
    mv = move_actions[0]
    expect("from" in mv and "to" in mv, "move action has from/to coordinates")
    expect(mv["from"] != mv["to"], "agent actually moved (from != to)")

def test_infect_and_consume_when_cell_present():
    s = FakeSpace()
    # put a susceptible cell inside infection radius
    cell = {"id": "cell_A", "coord": (0.0, 0.0), "meta": {}}  # not infected
    s.add_label("r1", cell)

    rng = random.Random(7)  # deterministic
    am = AntigenMaster(space=s, rng=rng, config={"default_step_size": 0.0, "infection_radius": 0.5, "invasion_efficiency": 1.0, "consume_on_infection": True})
    aid = am.spawn_agent((0.0, 0.0), viral_load=3.0)

    # step should produce agent_infected_cell and agent_consumed
    actions = am.step("r1", tick=1)
    names = [a.get("name") for a in actions]
    expect("agent_infected_cell" in names, "agent_infected_cell action emitted when susceptible cell present")
    expect("agent_consumed" in names, "agent_consumed emitted when consume_on_infection True")
    # agent state should be updated
    aobj = am.agents.get(aid)
    expect(aobj is not None and aobj.get("state") == "consumed", "agent state set to 'consumed' after infection")

def test_no_infect_if_cell_already_infected():
    s = FakeSpace()
    # cell already marked infected -> should not cause infection action
    cell = {"id": "cell_B", "coord": (0.0, 0.0), "meta": {"infected": True}}
    s.add_label("r2", cell)

    rng = random.Random(1)
    am = AntigenMaster(space=s, rng=rng, config={"default_step_size": 0.0, "infection_radius": 0.5, "invasion_efficiency": 1.0, "consume_on_infection": True})
    aid = am.spawn_agent((0.0, 0.0), viral_load=2.0)

    actions = am.step("r2", tick=2)
    names = [a.get("name") for a in actions]
    expect("agent_infected_cell" not in names, "no agent_infected_cell when nearby cell already infected")
    # agent should remain active (not consumed) because nothing consumed it
    aobj = am.agents.get(aid)
    expect(aobj is not None and aobj.get("state") == "active", "agent remains active when no infection happened")

# ----- runner --------------------------------------------------------------
if __name__ == "__main__":
    print("Running AntigenMaster tests...")
    test_spawn_and_list()
    test_move_action_emitted()
    test_infect_and_consume_when_cell_present()
    test_no_infect_if_cell_already_infected()
    print("\nAll AntigenMaster tests passed.")

