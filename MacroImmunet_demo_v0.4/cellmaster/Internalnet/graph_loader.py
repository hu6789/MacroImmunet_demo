import json
import os

class GraphLoader:
    def __init__(self, graph_dir):
        self.graph_dir = graph_dir
        self.cache = {}   # 🔥 缓存

    def load(self, graph_config):
        key = f"{graph_config['base']}|{graph_config['specific']}"

        # ✅ cache 命中
        if key in self.cache:
            return self.cache[key]

        print(f"[GraphLoader] Loading graph: {key}")

        base_path = os.path.join(self.graph_dir, f"{graph_config['base']}.json")
        specific_path = os.path.join(self.graph_dir, f"{graph_config['specific']}.json")

        base_graph = self._load_graph_file(base_path)
        specific_graph = self._load_graph_file(specific_path)

        merged = self._merge_graphs(base_graph, specific_graph)
        self._validate_graph(merged)

        # ✅ 存 cache
        self.cache[key] = merged

        return merged

    def _load_graph_file(self, path):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Graph file not found: {path}")
        with open(path, "r") as f:
            return json.load(f)

    def _merge_graphs(self, base, specific):
        merged = {}

        # -------------------------
        # 🔹 list → dict helper
        # -------------------------
        def nodes_list2dict(lst):
            return {n["node_id"]: n for n in lst}

        def behaviors_list2dict(lst):
            return {b["behavior_id"]: b for b in lst}

        # -------------------------
        # 🔹 nodes（🔥修复点）
        # -------------------------
        base_nodes = base.get("nodes", {})
        specific_nodes = specific.get("nodes", {})

        if isinstance(base_nodes, list):
            base_nodes = nodes_list2dict(base_nodes)
        if isinstance(specific_nodes, list):
            specific_nodes = nodes_list2dict(specific_nodes)

        merged["nodes"] = {
            **base_nodes,
            **specific_nodes
        }

        # -------------------------
        # 🔹 behaviors（你已经做了）
        # -------------------------
        base_behaviors = base.get("behaviors", [])
        specific_behaviors = specific.get("behaviors", [])
 
        if isinstance(base_behaviors, list):
            base_behaviors = behaviors_list2dict(base_behaviors)
        if isinstance(specific_behaviors, list):
            specific_behaviors = behaviors_list2dict(specific_behaviors)

        merged["behaviors"] = {
            **base_behaviors,
            **specific_behaviors
        }

        # -------------------------
        # edges
        # -------------------------
        base_edges = base.get("edges", [])
        spec_edges = specific.get("edges", [])

        base_node_edges, base_behavior_edges = self._split_edges(base_edges)
        spec_node_edges, spec_behavior_edges = self._split_edges(spec_edges)

        merged["node_edges"] = base_node_edges + spec_node_edges
        merged["behavior_edges"] = base_behavior_edges + spec_behavior_edges
        return merged
    def _split_edges(self, edge_list):
        node_edges = []
        behavior_edges = []

        for e in edge_list:
            if e["type"] == "node-node":
                node_edges.append({
                    "source": e["source"],
                    "target": e["target"],
                    "weight": e.get("weight", 1.0)
                })
            elif e["type"] == "node-behavior":
                behavior_edges.append({
                   "source": e["source"],
                   "behavior": e["target"],
                   "weight": e.get("weight", 1.0)
                })

        return node_edges, behavior_edges
    def _validate_graph(self, graph):
        # nodes
        if len(graph["nodes"]) != len(set(graph["nodes"].keys())):
            raise ValueError("Node IDs are not unique.")

        # behaviors
        if len(graph["behaviors"]) != len(set(graph["behaviors"].keys())):
            raise ValueError("Behavior IDs are not unique.")

        # node edges
        for edge in graph["node_edges"]:
            if edge["source"] not in graph["nodes"] or edge["target"] not in graph["nodes"]:
                raise ValueError(f"Invalid node edge: {edge}")

        # behavior edges
        for edge in graph["behavior_edges"]:
            if edge["behavior"] not in graph["behaviors"]:
                raise ValueError(f"Invalid behavior edge: {edge}")

        print(
            f"[GraphLoader] OK: "
            f"{len(graph['nodes'])} nodes | "
            f"{len(graph['behaviors'])} behaviors | "
            f"{len(graph['node_edges'])} edges"
        )
