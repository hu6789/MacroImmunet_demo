from Internalnet.engine.graph_loader import load_node_schema
from Internalnet.engine.internalnet_engine import InternalNetEngine


def test_cd8_graph():

    graph = load_node_schema(
        "Internalnet/CD8_TCELL_INTERNALNET_GRAPH_v1"
    )

    engine = InternalNetEngine(graph)

    state = {
        "pMHC": 1.0
    }

    new_state = engine.forward(state)

    assert "IL2" in new_state
