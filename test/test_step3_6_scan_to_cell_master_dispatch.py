# test/test_step3_6_scan_to_cell_master_dispatch.py

from cell_master.cell_master_base import CellMasterBase


class DummyCellMaster(CellMasterBase):
    def decide(self, node):
        # minimal decision logic
        return [{
            "name": "emit_label",
            "payload": {
                "type": "PMHC",
                "coord": node["meta"]["coord"],
                "mass": 1.0,
            }
        }]


def test_step3_6_scan_dispatch_to_cell_master():
    cm = DummyCellMaster(space=None)

    nodes = [{
        "behavior": "antigen_hotspot",
        "meta": {
            "coord": (1, 0),
            "antigen": 5.0,
        }
    }]

    cm.handle_nodes(nodes)

    assert len(cm.intent_queue) > 0

    intent = cm.intent_queue[0]
    assert intent["name"] == "emit_label"
    assert intent["payload"]["coord"] == (1, 0)

