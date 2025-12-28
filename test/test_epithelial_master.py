# test/test_epithelial_master.py
import random
from cell_master.masters.epithelial_master import EpithelialMaster

def run_all():
    test_exposure_to_infection()
    test_productive_releases_antigen()
    test_necrosis_generates_fragments()
    test_ctl_interrupts_necrosis()
    print("All EpithelialMaster tests passed.")

def expect(cond, msg):
    if not cond:
        raise AssertionError(msg)

def test_exposure_to_infection():
    rng = random.Random(42)
    # make infection deterministic: p_infect_on_contact=1, incubation 1, establishment 1
    m = EpithelialMaster(config={
        "p_infect_on_contact": 1.0,
        "incubation_ticks": 1,
        "p_establish_infection": 1.0,
        "initial_viral_load": 2.0,
        "release_interval": 2
    })
    coord = (0.0, 0.0)
    cell_meta = {"state": "healthy"}
    # nearby infectious agent
    agent = {"infectious": True, "coord": (0.5, 0.0)}
    summary = {"agents": [agent]}

    # first step => either exposed or immediate infected depending on config (we set immediate infection)
    acts = m.step(coord, summary, cell_meta, rng=rng)
    # now cell should enter infected_productive
    expect(cell_meta.get("state") == "infected_productive", "exposure -> infected_productive")
    expect("viral_load" in cell_meta and cell_meta["viral_load"] >= 2.0, "viral_load initialized")

def test_productive_releases_antigen():
    rng = random.Random(123)
    m = EpithelialMaster(config={"release_interval": 1, "antigen_release_amount": 3.0, "replication_rate": 1.0})
    coord = (0.0, 0.0)
    cell_meta = {"state": "infected_productive", "viral_load": 1.0, "release_timer": 0}
    summary = {"agents": []}
    acts = m.step(coord, summary, cell_meta, rng=rng)
    # expect a release_antigen action
    names = [a["name"] for a in acts]
    assert "release_antigen" in names, f"expected release_antigen in {names}"
    # payload should have amount preserved
    ra = [a for a in acts if a["name"] == "release_antigen"][0]
    assert ra["payload"]["amount"] == 3.0

def test_necrosis_generates_fragments():
    rng = random.Random(1)
    # force necrosis path: set viral_load above threshold and prob_necrosis_on_death=1
    m = EpithelialMaster(config={"damage_to_necrosis_threshold": 5.0, "prob_necrosis_on_death": 1.0, "necrosis_delay": 0, "antigen_fragment_amount": 4})
    coord = (0,0)
    # put cell in infected_productive with very high viral load so it triggers necrosis
    cell_meta = {"state": "infected_productive", "viral_load": 6.0, "release_timer": 1}
    acts = m.step(coord, {"agents": []}, cell_meta, rng=rng)
    # after stepping, we expect "change_state" to necrosis_initiated and then spawn (necrosis_delay==0) spawn_antigen_agents
    names = [a["name"] for a in acts]
    assert "spawn_antigen_agents" in names, f"expected spawn_antigen_agents in {names}"
    sa = [a for a in acts if a["name"] == "spawn_antigen_agents"][0]
    assert sa["payload"]["count"] == 4

def test_ctl_interrupts_necrosis():
    rng = random.Random(2)
    m = EpithelialMaster(config={"necrosis_delay": 2, "antigen_fragment_amount": 5})
    coord = (0,0)
    # set cell to be mid-necrosis
    cell_meta = {"state": "necrosis_initiated", "necrosis_timer": 2}
    # simulate CTL triggering apoptosis by setting external_apoptosis flag before step
    cell_meta["external_apoptosis"] = True
    acts = m.step(coord, {"agents": []}, cell_meta, rng=rng)
    # should have converted to apoptosis_early and NOT spawned fragments
    assert cell_meta.get("state") == "apoptosis_early"
    names = [a["name"] for a in acts]
    assert "spawn_antigen_agents" not in names
    assert any(a["name"] == "change_state" for a in acts)

if __name__ == "__main__":
    run_all()

