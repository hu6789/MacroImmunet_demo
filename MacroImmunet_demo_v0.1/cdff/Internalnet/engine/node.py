from Internalnet.engine.node_rules import RULE_REGISTRY

class Node:
    """
    Basic InternalNet node.

    A node represents a biological variable inside the cell,
    such as signal, transcription factor, program, or state.
    """
    def __init__(self, node_id, node_type, inputs, update_rule, params=None):

        self.node_id = node_id
        self.node_type = node_type
        self.inputs = inputs
        self.update_rule = update_rule
        self.params = params or {}

    def set(self, v):
        """
        Directly set node value.
        Used for input signals.
        """
        self.value = float(v)

    def get(self):
        """
        Get node value.
        """
        return self.value

    def to_dict(self):
        """
        Export node state (for debugging / logging).
        """
        return {
            "id": self.node_id,
            "type": self.node_type,
            "value": self.value
        }

    def __repr__(self):

        return f"<Node {self.node_id} value={self.value:.3f}>"

    def compute(self, input_values):
 
        if self.update_rule not in RULE_REGISTRY:
            raise ValueError(f"Unknown update rule: {self.update_rule}")

        rule_func = RULE_REGISTRY[self.update_rule]

        return rule_func(self, input_values, self.params)

