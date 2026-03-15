from Internalnet.engine.internalnet_engine import InternalNetEngine
from Internalnet.engine.node import Node


def test_engine_forward():

    node = Node(
        node_id="NFAT",
        node_type="tf",
        inputs=["pMHC"],
        update_rule="weighted_sum_sigmoid",
        params={"w0": 1.0}
    )

    graph = {
        "NFAT": node
    }

    engine = InternalNetEngine(graph)

    state = {
        "pMHC": 1.0
    }

    new_state = engine.forward(state)

    assert "NFAT" in new_state
