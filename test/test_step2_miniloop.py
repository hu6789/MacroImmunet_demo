# test/test_step2_miniloop.py
# -*- coding: utf-8 -*-

import random

from cell_master.masters.epithelial_master import EpithelialMaster
from cell_master.masters.dc_master import DCMaster
from cell_master.masters.native_t_master import NativeTMaster


def test_step2_minimal_closed_loop():
    """
    Step2.0 minimal causal loop test:

        epithelial (infected)
            -> release_antigen
            -> DC captures & presents pMHC
            -> naive T differentiates (TH1 or CTL)

    This test only checks:
      - signals propagate
      - masters respond causally
      - no orphan logic
    """

    rng = random.Random(42)

    # -------------------------------
    # 1) Instantiate masters
    # -------------------------------
    epi = EpithelialMaster(config={
        "initial_viral_load": 5.0,
        "replication_rate": 1.0,
        "release_interval": 1,
        "antigen_release_amount": 2.0,
        "debug": False,
    })

    dc = DCMaster(config={
        "process_limit": 2,
        "default_ln_coord": (10.0, 10.0),
    })

    tcell = NativeTMaster(config={
        "p_differentiate_on_pmhc": 1.0,  # force differentiation for test
        "debug": False,
    })

    # -------------------------------
    # 2) Fake world state
    # -------------------------------
    epi_coord = (0.0, 0.0)
    dc_coord = (0.5, 0.5)
    t_coord = (1.0, 1.0)

    epithelial_meta = {
        "state": "infected_productive",
        "viral_load": 10.0,
        "release_timer": 0,
    }

    dc_label = {
        "id": "dc_1",
        "coord": dc_coord,
        "meta": {}
    }

    t_meta = {
        "type": "NAIVE_T",
        "activated": False,
    }

    # -------------------------------
    # 3) Tick 1 — epithelial releases antigen
    # -------------------------------
    epi_actions = epi.step(
        coord=epi_coord,
        summary={"agents": []},
        cell_meta=epithelial_meta,
        rng=rng
    )

    release_actions = [a for a in epi_actions if a["name"] == "release_antigen"]
    assert release_actions, "Epithelial should release antigen"

    # Fake antigen agents from epithelial output
    antigen_agents = [{
        "infectious": True,
        "coord": epi_coord,
        "proto": {"sequence": "FAKE_VIRAL_PEPTIDE"}
    }]

    # -------------------------------
    # 4) Tick 2 — DC captures & presents
    # -------------------------------
    dc_actions = dc.step(
        coord=dc_coord,
        summary={"agents": antigen_agents},
        cell_meta={"type": "DC"},
        rng=rng
    )

    pmhc_actions = [
        a for a in dc_actions
        if getattr(a, "name", None) == "pMHC_presented"
        or (isinstance(a, dict) and a.get("name") == "pMHC_presented")
    ]

    assert pmhc_actions, "DC should present pMHC after antigen capture"

    # -------------------------------
    # 5) Tick 3 — Naive T sees pMHC and differentiates
    # -------------------------------
    t_summary = {
        "pMHC_present": True,
        "DC_presenting": True,
        "IL12": 2.0,
    }

    t_actions = tcell.step(
        coord=t_coord,
        summary=t_summary,
        cell_meta=t_meta,
        rng=rng
    )

    change_type = [a for a in t_actions if a["name"] == "change_type"]

    assert change_type, "Naive T should differentiate upon pMHC signal"
    assert t_meta["type"] in ("TH1", "CTL")

    # -------------------------------
    # 6) Final sanity output (optional)
    # -------------------------------
    print("\n[Step2.0] Differentiated T type:", t_meta["type"])

