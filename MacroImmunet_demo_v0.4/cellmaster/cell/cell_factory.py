# cellmaster/cell/cell_factory.py
import json
import os
import random
import numpy as np
from .cell_instance import Cell

class CellFactory:
    def __init__(self):
        base_dir = os.path.dirname(__file__)
        self.type_dir = os.path.join(base_dir, "cell_types")
        self._id_counter = 0

    def _generate_id(self):
        self._id_counter += 1
        return self._id_counter
    def _load_graph(self, graph_config):

        base_dir = os.path.dirname(__file__)
        graph_dir = os.path.join(base_dir, "../Internalnet/node/graph")

        base = graph_config.get("base")
        specific = graph_config.get("specific")

        graph = {
            "nodes": {},
            "node_edges": []
        }

        def load_one(name):
            if not name:
                return None
            path = os.path.join(graph_dir, f"{name}.json")
            if not os.path.exists(path):
                raise FileNotFoundError(f"Graph not found: {path}")
            with open(path) as f:
                return json.load(f)

        base_graph = load_one(base)
        spec_graph = load_one(specific)

        # 👉 merge
        for g in [base_graph, spec_graph]:
            if not g:
                continue
            graph["nodes"].update(g.get("nodes", {}))
            graph["node_edges"].extend(g.get("node_edges", []))
            graph.setdefault("behaviors", {}).update(g.get("behaviors", {}))

        return graph

    def create(self, position, cell_type="test_cell"):
        """
        position: tuple (x, y)
        cell_type: str, "cd8_t_cell" or "infected_cell"
        """
        path = os.path.join(self.type_dir, f"{cell_type}.json")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Cell type json not found: {path}")

        with open(path, "r") as f:
            config = json.load(f)

        cell = Cell(config)

        # Identity
        cell.cell_id = self._generate_id()
        cell.cell_type = cell_type
        cell.position = position
        cell.meta = {}

        # --------------------
        # Graph info
        # --------------------
        cell.graph = config.get("graph", {
            "nodes": {},       # 所有 node_id → node info
            "node_edges": [],  # 边列表
            "behaviors": {}    # graph允许的behavior
        })

        # --------------------
        # State flags
        # --------------------
        cell.state_flags = config.get("state_flags", {"alive": True})

        # --------------------
        # HIR state
        # --------------------
        cell.state = config.get("state", {"labels": [], "fate": "normal"})

        # --------------------
        # Node state with mean/std sampling
        # --------------------
        node_state_config = config.get("init_node_state", {})
        cell.node_state = {}
        for node, spec in node_state_config.items():
            if isinstance(spec, dict) and "mean" in spec:
                cell.node_state[node] = self._sample_param(spec)
            else:
                cell.node_state[node] = spec

        # --------------------
        # Capabilities / behavior / feature / receptor
        # --------------------
        cell.capability = config.get("capability", {}).copy()
        cell.behavior_switch = config.get("behavior_switch", {}).copy()
        cell.feature_params = self._apply_distribution_dict(config.get("feature_params", {}))
        cell.receptor_params = self._apply_distribution_dict(config.get("receptor_params", {}))
        cell.behavior_params = config.get("behavior_params", {}).copy()

        # --------------------
        # Subtype (optional)
        # --------------------
        subtypes = config.get("subtypes", {})
        if subtypes:
            subtype_name = random.choice(list(subtypes.keys()))
            subtype = subtypes[subtype_name]

            # Override params if subtype exists
            for k, spec in subtype.get("feature_params", {}).items():
                cell.feature_params[k] = self._sample_param(spec)
            for k, spec in subtype.get("receptor_params", {}).items():
                cell.receptor_params[k] = self._sample_param(spec)
            for k, v in subtype.get("behavior_params", {}).items():
                cell.behavior_params[k] = v

            cell.meta["subtype"] = subtype_name
        else:
            cell.meta["subtype"] = None  # 安全 fallback

        cell.cell_id = self._generate_id()

        return cell
    # --------------------
    # Sample param
    # --------------------
    def _sample_param(self, spec):
        if isinstance(spec, (int, float)):
            return spec
        mean = spec.get("mean", 1.0)
        std = spec.get("std", 0.0)
        dist = spec.get("dist", "normal")
        if dist == "normal":
            return max(0.0, random.gauss(mean, std))
        elif dist == "lognormal":
            return np.random.lognormal(mean=0, sigma=std) * mean
        else:
            return mean

    def _apply_distribution_dict(self, param_dict):
        result = {}
        for k, spec in param_dict.items():
            result[k] = self._sample_param(spec)
        return result
