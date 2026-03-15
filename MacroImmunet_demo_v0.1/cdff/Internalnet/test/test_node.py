from Internalnet.engine.node import Node


def test_node_basic():

    schema = {
        "node_id": "NFAT",
        "node_type": "tf",
        "inputs": ["pMHC"],
        "update_rule": "weighted_sum_sigmoid",
        "params": {"w_pMHC": 1.2}
    }

    node = Node(
        node_id=schema["node_id"],
        node_type=schema["node_type"],
        inputs=schema["inputs"],
        update_rule=schema["update_rule"],
        params=schema["params"]
    )

    assert node.node_id == "NFAT"
    assert node.node_type == "tf"
