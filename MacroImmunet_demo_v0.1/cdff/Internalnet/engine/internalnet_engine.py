from Internalnet.behavior.behavior_engine import BehaviorEngine
from Internalnet.hir.hir_engine import HIREngine
from Internalnet.state_update.state_update_engine import StateUpdateEngine
from collections import deque
class InternalNetEngine:

    def __init__(self, graph):

        self.graph = graph

        # Node computation
        self.node_engine = self

        # Behavior generator
        self.behavior_engine = BehaviorEngine()

        # HIR regulator
        self.hir_engine = HIREngine()

        # State update layer
        self.state_update_engine = StateUpdateEngine()

    def _topological_sort(self):

        indegree = {nid: 0 for nid in self.graph}

        for node in self.graph.values():
            for inp in node.inputs:
                if inp in indegree:
                    indegree[node.node_id] += 1

        queue = deque()

        for nid, deg in indegree.items():
            if deg == 0:
                queue.append(nid)

        order = []

        while queue:

            nid = queue.popleft()
            order.append(nid)

            for node in self.graph.values():

                if nid in node.inputs:

                    indegree[node.node_id] -= 1

                    if indegree[node.node_id] == 0:
                        queue.append(node.node_id)

        return order

    def forward(self, state):

        node_values = self.node_engine.run(state)

        hir_result = self.hir_engine.evaluate(node_values)

        behaviors = self.behavior_engine.generate(node_values, hir_result)

        new_state = self.state_update_engine.update(state, node_values)

        new_state["behaviors"] = behaviors

        return new_state
    def run(self, state):

        node_values = {}

        order = self._topological_sort()

        for node_id in order:

            node = self.graph[node_id]

            if node.node_type == "input":
                node_values[node_id] = state.get(node_id, 0.0)
                continue

            input_values = {}

            for inp in node.inputs:
                if inp in node_values:
                    input_values[inp] = node_values[inp]
                else:
                    input_values[inp] = state.get(inp, 0.0)

            value = node.compute(input_values)

            node_values[node_id] = value

        return node_values
