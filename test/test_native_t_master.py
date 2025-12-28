# test/test_native_t_master.py
import unittest
import random
from cell_master.masters.native_t_master import NativeTMaster

class TestNativeTMaster(unittest.TestCase):

    def mk_summary(self, extras=None):
        s = {"agents": [], "cells": []}
        if extras:
            s.update(extras)
        return s

    def test_il12_drives_th1_differentiation_and_handover(self):
        master = NativeTMaster(config={"il12_threshold": 0.5, "p_th1_given_il12": 1.0, "debug": False})
        summary = self.mk_summary({"IL12": 1.2})
        cell_meta = {"type": "NAIVE_T"}
        rng = random.Random(42)

        actions = master.step(coord=(0,0), summary=summary, cell_meta=cell_meta, rng=rng)
        names = [a.get("name") for a in actions]

        # should have mutated to TH1
        self.assertEqual(cell_meta.get("type"), "TH1")
        # actions should include change_type and handover_label and a secrete for IFNG/IL2
        self.assertIn("change_type", names)
        self.assertIn("handover_label", names)
        self.assertTrue(any(a.get("name") == "secrete" and a.get("payload", {}).get("label") == "IFNG" for a in actions))
        self.assertTrue(any(a.get("name") == "secrete" and a.get("payload", {}).get("label") == "IL2" for a in actions))

    def test_pmhc_drives_ctl_differentiation_and_handover(self):
        master = NativeTMaster(config={"p_differentiate_on_pmhc": 1.0, "p_th1_given_il12": 0.0})
        # provide a pMHC cue
        summary = self.mk_summary({"pMHC_present": True})
        cell_meta = {"type": "NAIVE_T"}
        rng = random.Random(123)

        actions = master.step(coord=(1,1), summary=summary, cell_meta=cell_meta, rng=rng)
        names = [a.get("name") for a in actions]

        self.assertEqual(cell_meta.get("type"), "CTL")
        self.assertIn("change_type", names)
        self.assertIn("handover_label", names)

    def test_th1_secretes_ifng_and_il2_when_active(self):
        master = NativeTMaster()
        # start as TH1 already
        cell_meta = {"type": "TH1", "activated": True}
        summary = self.mk_summary()
        rng = random.Random(7)

        actions = master.step(coord=(0,0), summary=summary, cell_meta=cell_meta, rng=rng)
        # expect secrete IFNG and IL2 and mark TH1_ACTIVE
        labels = [ (a.get("name"), a.get("payload",{}).get("label")) for a in actions if a.get("name") == "secrete" ]
        names = [a.get("name") for a in actions]
        self.assertIn("secrete", names)
        self.assertTrue(any(lbl == "IFNG" for (_, lbl) in labels))
        self.assertTrue(any(lbl == "IL2" for (_, lbl) in labels))
        self.assertTrue(any(a.get("name") == "mark" and a.get("payload", {}).get("flag") == "TH1_ACTIVE" for a in actions))

    def test_ctl_marks_active_when_activated_or_pmhc(self):
        master = NativeTMaster()
        # CTL with activation flag
        cell_meta = {"type": "CTL", "activated": True}
        summary = self.mk_summary()
        rng = random.Random(5)
        actions = master.step(coord=(2,2), summary=summary, cell_meta=cell_meta, rng=rng)
        self.assertTrue(any(a.get("name") == "mark" and a.get("payload", {}).get("flag") == "CTL_ACTIVE" for a in actions))

        # CTL with pMHC cue even if not marked activated
        cell_meta2 = {"type": "CTL"}
        summary2 = self.mk_summary({"pMHC_present": True})
        actions2 = master.step(coord=(2,2), summary=summary2, cell_meta=cell_meta2, rng=random.Random(6))
        self.assertTrue(any(a.get("name") == "mark" and a.get("payload", {}).get("flag") == "CTL_ACTIVE" for a in actions2))

    def test_naive_random_move_when_no_cues(self):
        master = NativeTMaster()
        summary = self.mk_summary()
        cell_meta = {"type": "NAIVE_T"}
        rng = random.Random(99)
        actions = master.step(coord=(5,5), summary=summary, cell_meta=cell_meta, rng=rng)
        # should emit a random_move action (name == "random_move")
        self.assertTrue(any(a.get("name") == "random_move" for a in actions))

if __name__ == "__main__":
    unittest.main()

