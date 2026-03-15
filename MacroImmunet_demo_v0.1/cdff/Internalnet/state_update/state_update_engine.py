class StateUpdateEngine:

    def update(self, state, node_values=None):

        new_state = dict(state)

        # --- baseline physiology update ---

        if "energy" in new_state:
            new_state["energy"] *= 0.95   # 每tick消耗5%

        if "stress" in new_state:
            new_state["stress"] += 0.01   # 基础压力

        # --- integrate node values ---
        if node_values:
            for k, v in node_values.items():
                new_state[k] = v

        return new_state
