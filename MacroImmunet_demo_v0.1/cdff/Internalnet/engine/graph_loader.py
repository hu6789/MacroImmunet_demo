import os
import json
from .node import Node


def load_node_schema(schema_dir):
    """
    读取 node_schema 目录中的所有 node 文件
    返回 Node 对象 dict
    """

    graph = {}

    for filename in os.listdir(schema_dir):

        path = os.path.join(schema_dir, filename)

        if not os.path.isfile(path):
            continue

        with open(path, "r") as f:
            data = json.load(f)

        node = Node(
            node_id=data.get("node_id", data.get("id")),
            node_type=data.get("node_type", data.get("type", "signal")),
            inputs=data.get("inputs", []),
            update_rule=data.get("update_rule", None),
            params=data.get("params", {})
        )

        graph[node.node_id] = node

    return graph
