# -*- coding: utf-8 -*-

from cell_master.masters.epithelial_master import EpithelialMaster


def test_epithelial_master_contract_basic():
    """
    Step1 contract:
    - zero-arg construction
    - step exists
    - step returns list of action dicts with 'name'
    """
    em = EpithelialMaster()

    assert hasattr(em, "step")

    actions = em.step(
        coord=(0.0, 0.0),
        summary={},
        cell_meta={"state": "healthy"},
        rng=None,
    )

    assert isinstance(actions, list)
    for a in actions:
        assert isinstance(a, dict)
        assert "name" in a


def test_epithelial_master_infected_can_release_antigen():
    """
    infected_productive epithelial cell should be able to
    emit release_antigen.
    """
    em = EpithelialMaster({
        "replication_rate": 1.0,
        "release_interval": 1,
    })

    cell_meta = {
        "state": "infected_productive",
        "viral_load": 5.0,
        "release_timer": 1,
    }

    seen = False
    for _ in range(5):
        actions = em.step(
            coord=(0.0, 0.0),
            summary={},
            cell_meta=cell_meta,
            rng=None,
        )
        names = [a["name"] for a in actions]
        if "release_antigen" in names:
            seen = True
            break

    assert seen, "infected epithelial cell should release antigen"


def test_epithelial_master_necrosis_or_fragment_flow():
    """
    High viral load can trigger necrosis and fragment-related actions.
    """
    em = EpithelialMaster({
        "damage_to_necrosis_threshold": 1.0,
        "prob_necrosis_on_death": 1.0,
        "necrosis_delay": 0,
    })

    cell_meta = {
        "state": "infected_productive",
        "viral_load": 10.0,
    }

    actions = em.step(
        coord=(0.0, 0.0),
        summary={},
        cell_meta=cell_meta,
        rng=None,
    )

    names = [a["name"] for a in actions]

    assert (
        "change_state" in names
        or "spawn_antigen_agents" in names
        or "mark_fragment" in names
    ), "necrosis / fragment related action expected"

