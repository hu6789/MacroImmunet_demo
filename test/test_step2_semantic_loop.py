# test/test_step2_semantic_loop.py
# -*- coding: utf-8 -*-

import random

from cell_master.masters.epithelial_master import EpithelialMaster
from cell_master.masters.dc_master import DCMaster
from cell_master.masters.native_t_master import NativeTMaster


def extract_pmhc_summary(dc_actions):
    """
    Convert DC intents -> summary fragment for T cell.
    """
    pmhcs = []
    for a in dc_actions:
        name = getattr(a, "name", None) or a.get("name")
        if name == "pMHC_presented":
            payload = getattr(a, "payload", None) or a.get("payload", {})
            pmhcs.append(payload.get("pMHC"))
    return {
        "pMHC_present": bool(pmhcs),
        "pMHCs": pmhcs,
        "DC_presenting": bool(pmhcs),
    }


def test_step2_semantic_closed_loop():
    rng = random.Random(123)

    epi = EpithelialMaster(config={
        "initial_viral_load": 6.0,
        "release_interval": 1,
    })

    dc = DCMaster(config={
        "process_limit": 1,
    })

    tcell = NativeTMaster(config={
        "p_differentiate_on_pmhc": 1.0,  # force
    })

    # --------------------
    # initial states
    # --------------------
    epi_meta = {
        "state": "infected_productive",
        "viral_load": 8.0,
        "release_timer": 0,
    }

    dc_coord = (0.5, 0.5)
    dc_meta = {"type": "DC"}

    t_meta = {"type": "NAIVE_T"}

    # --------------------
    # Tick 1: epithelial
    # --------------------
    epi_actions = epi.step(
        coord=(0, 0),
        summary={"agents": []},
        cell_meta=epi_meta,
        rng=rng
    )

    assert any(a["name"] == "release_antigen" for a in epi_actions)

    antigen_agents = [{
        "infectious": True,
        "coord": (0, 0),
        "proto": {"sequence": "VIRAL_PEPTIDE_X"}
    }]

    # --------------------
    # Tick 2: DC
    # --------------------
    dc_actions = dc.step(
        coord=dc_coord,
        summary={"agents": antigen_agents},
        cell_meta=dc_meta,
        rng=rng
    )

    semantic_summary = extract_pmhc_summary(dc_actions)
    assert semantic_summary["pMHC_present"]

    # --------------------
    # Tick 3: Naive T
    # --------------------
    t_actions = tcell.step(
        coord=(1, 1),
        summary=semantic_summary,
        cell_meta=t_meta,
        rng=rng
    )

    change_type = [a for a in t_actions if a["name"] == "change_type"]

    assert change_type
    assert t_meta["type"] in ("TH1", "CTL")

    print("[Step2.1] T differentiated to:", t_meta["type"])

