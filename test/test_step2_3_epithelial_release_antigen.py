import random

from cell_master.masters.epithelial_master import EpithelialMaster


def test_step2_3_epithelial_release_antigen_on_apoptosis():
    rng = random.Random(42)

    epi = EpithelialMaster(config={})

    coord = (1, 1)

    # --------
    # initial epithelial state
    # --------
    cell_meta = {
        "state": "infected_productive",
        "viral_load": 12.5,
        "release_timer": 0,
    }

    # --------
    # external apoptosis intent (from CTL)
    # --------
    summary = {
        "external_intents": [
            {
                "name": "external_apoptosis",
                "mode": "CTL_kill",
                "source": "CTL",
            }
        ]
    }

    actions = epi.step(
        coord=coord,
        summary=summary,
        cell_meta=cell_meta,
        rng=rng,
    )

    # --------
    # assertions
    # --------
    assert cell_meta["state"] in ("apoptotic", "dead")

    die_actions = [a for a in actions if a["name"] == "die"]
    assert len(die_actions) == 1

    label_actions = [a for a in actions if a["name"] == "emit_label"]
    assert len(label_actions) == 1

    label = label_actions[0]["payload"]
    assert label["label"] == "ANTIGEN_RELEASE"
    assert label["amount"] == 12.5
    assert label["coord"] == coord

