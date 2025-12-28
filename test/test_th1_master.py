# test/test_th1_master.py
import unittest
from cell_master.masters.th1_master import Th1Master
from cell_master.intents import Intent, Intent_move_to, Intent_random_move

# Try to import a specific secrete intent class if available
try:
    from cell_master.intents import Intent_secrete  # type: ignore
except Exception:
    Intent_secrete = None  # type: ignore


class TestTh1Master(unittest.TestCase):

    def mk_summary(self, extras=None):
        s = {"agents": [], "cells": []}
        if extras:
            s.update(extras)
        return s

    def test_move_to_pmhc_hotspot(self):
        m = Th1Master()
        summary = self.mk_summary({"pMHC_hotspot": (10, 10)})
        intents = m.step(coord=(0, 0), summary=summary, cell_meta={}, rng=None)
        self.assertTrue(any((isinstance(i, Intent_move_to) or (isinstance(i, dict) and i.get("name") == "move_to") ) for i in intents))

    def test_random_move_without_targets(self):
        m = Th1Master()
        summary = self.mk_summary()
        intents = m.step(coord=(5, 5), summary=summary, cell_meta={}, rng=None)
        self.assertTrue(any(isinstance(i, Intent_random_move) or (isinstance(i, dict) and i.get("name") == "random_move") for i in intents))

    def test_secrete_when_activated(self):
        m = Th1Master()
        summary = self.mk_summary()
        cm = {"activated": True}
        intents = m.step(coord=(1, 1), summary=summary, cell_meta=cm, rng=None)
        # accept either specialized Intent_secrete, generic Intent with name 'secrete', or dict shape
        ok = False
        for it in intents:
            if Intent_secrete is not None and isinstance(it, Intent_secrete):
                ok = True
                break
            if isinstance(it, Intent) and getattr(it, "name", None) == "secrete":
                ok = True
                break
            if isinstance(it, dict) and it.get("name") == "secrete":
                ok = True
                break
        self.assertTrue(ok, "expected a secrete intent when Th1 is activated")

    def test_move_to_nearby_bcell(self):
        m = Th1Master()
        # one B cell nearby
        b = {"coord": (3, 3), "type": "B"}
        summary = self.mk_summary({"cells": [b]})
        intents = m.step(coord=(2, 2), summary=summary, cell_meta={}, rng=None)
        self.assertTrue(any(isinstance(i, Intent_move_to) or (isinstance(i, dict) and i.get("name") == "move_to") for i in intents))


if __name__ == "__main__":
    unittest.main()

