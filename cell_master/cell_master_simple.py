# cell_master/cell_master_simple.py

from typing import Dict, List, Any


class CellMasterSimple:
    """
    Step3.1: Minimal CellMaster

    Responsibility:
    - receive node_input from ScanMaster
    - make a trivial decision
    - emit semantic intents (NO execution)
    """

    def __init__(self, cell_type: str, antigen_threshold: float = 1.0):
        self.cell_type = cell_type
        self.antigen_threshold = antigen_threshold

    def process_node(self, node_input: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        node_input example:
        {
            "coord": (x, y),
            "antigen_density": float,
            "cell_summary": {...},
            "event_flag": "hotspot"
        }
        """
        intents = []

        antigen = node_input.get("antigen_density", 0.0)
        coord = node_input.get("coord")

        if antigen >= self.antigen_threshold:
            intents.append({
                "target_cell": self.cell_type,
                "coord": coord,
                "action": "activate",
                "strength": min(1.0, antigen / self.antigen_threshold),
                "source": "CellMasterSimple"
            })

        return intents

