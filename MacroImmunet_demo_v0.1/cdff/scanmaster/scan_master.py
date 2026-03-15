# cdff/scanmaster/scan_master.py

from .interaction_library import INTERACTION_RULES
from .event_builder import build_node_input


class ScanMaster:

    def __init__(self, world):

        self.world = world

    def scan_cell(self, cell):

        events = []

        neighbors = self.world.get_neighbors(cell)

        for neighbor in neighbors:

            for rule in INTERACTION_RULES:

                if rule.get("source_cell") != cell["type"]:
                    continue

                if "target_cell" in rule:

                    if neighbor["type"] != rule["target_cell"]:
                        continue

                event = {

                    "type": rule["name"],

                    "source": cell["id"],
                    "target": neighbor["id"],

                    "signal": rule["signal"],
                    "strength": rule["strength"]
                }

                events.append(event)

        return build_node_input(events)
