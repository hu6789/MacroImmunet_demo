class NodeEngine:

    def __init__(self, graph):

        # graph: dict[node_id] -> Node
        self.graph = graph

        # build execution order
        self.execution_order = self.build_execution_order()

        print("InternalNet execution order:", self.execution_order)

    def build_execution_order(self):

        visited = set()
        order = []

        def dfs(node_id):

            if node_id in visited:
                return

            visited.add(node_id)

            node = self.graph[node_id]

            for dep in node.inputs:

                # only follow dependencies inside graph
                if dep in self.graph:
                    dfs(dep)

            order.append(node_id)

        for node_id in self.graph:
            dfs(node_id)

        return order

    def run(self, state):

        node_values = {}

        for node_id in self.execution_order:

            node = self.graph[node_id]

            inputs = {}

            for name in node.inputs:

                # priority: computed node_values
                if name in node_values:
                    inputs[name] = node_values[name]

                # fallback: state
                else:
                    inputs[name] = state.get(name, 0)

            value = node.compute(inputs)

            node_values[node_id] = value

        return node_values
