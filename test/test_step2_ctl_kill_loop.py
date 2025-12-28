# test/test_step2_ctl_kill_loop.py
# -*- coding: utf-8 -*-

import random

from cell_master.masters.epithelial_master import EpithelialMaster
from cell_master.masters.native_t_master import NativeTMaster


def test_step2_ctl_kills_epithelial():
    rng = random.Random(123)

    epi = EpithelialMaster(config={
        "initial_viral_load": 6.0,
        "release_interval": 1,
    })

    ctl = NativeTMaster(config={
        "force_type": "CTL",
        "p_kill_on_contact": 1.0,
    })

    # --------------------
    # initial states
    # --------------------
    epi_meta = {
        "state": "infected_productive",
        "viral_load": 10.0,
        "release_timer": 0,
    }

    ctl_meta = {
        "type": "CTL",
        "activation_level": 1.0,
    }

    coord = (0, 0)

    # --------------------
    # Tick 1: CTL attacks
    # --------------------
    ctl_actions = ctl.step(
        coord=coord,
        summary={
            "infected_cells": 1,
            "targets": [coord],
        },
        cell_meta=ctl_meta,
        rng=rng
    )

    kill_intents = [a for a in ctl_actions if a["name"] == "external_apoptosis"]
    assert kill_intents, "CTL did not emit kill intent"

    # --------------------
    # Tick 2: Epithelial receives kill
    # --------------------
    epi_actions = epi.step(
        coord=coord,
        summary={
            "external_intents": kill_intents
        },
        cell_meta=epi_meta,
        rng=rng
    )

    # epithelial should die
    assert epi_meta["state"] in ("apoptotic", "dead")

    # no more viral release
    assert not any(a["name"] == "release_antigen" for a in epi_actions)

    print("[Step2.2] Epithelial killed by CTL, state =", epi_meta["state"])

