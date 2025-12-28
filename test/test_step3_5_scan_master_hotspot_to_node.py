# test/test_step3_5_scan_master_hotspot_to_node.py

from scan_master.aggregator import ScanAggregator


def test_step3_5_scan_aggregator_detects_hotspot():
    """
    Step3.5:
    grid_summary -> node_input
    """

    # fake grid summary from LabelCenter
    grid_summary = {
        (0, 0): {
            "labels": {
                "ANTIGEN": 0.2,
                "IL12": 0.0,
            }
        },
        (1, 0): {
            "labels": {
                "ANTIGEN": 5.0,   # hotspot
                "IL12": 1.2,
            }
        },
        (0, 1): {
            "labels": {
                "ANTIGEN": 0.1,
            }
        }
    }

    scan = ScanAggregator(antigen_threshold=1.0)

    nodes = scan.build_nodes(grid_summary)

    # --- assertions ---
    assert isinstance(nodes, list)
    assert len(nodes) >= 1

    node = nodes[0]
    assert "behavior" in node
    assert "meta" in node
    assert "coord" in node["meta"]
    assert node["meta"]["coord"] == (1, 0)
    assert node["meta"]["antigen"] >= 1.0

