from Internalnet.engine.graph_loader import load_node_schema


def test_loader():

    graph = load_node_schema(
        "Internalnet/CD8_TCELL_INTERNALNET_GRAPH_v1"
    )

    assert "NFAT" in graph
