# Internalnet/cell/cell_instance.py

class Cell:

    def __init__(self, config):

        self.cell_id = "cell_1"
        self.cell_type = config.get("cell_type", "unknown")

        self.node_state = config.get("init_node_state", {}).copy()

        self.capability = config.get("capability", {})
        self.feature_params = config.get("feature_params", {})

        # runtime
        self.cell_state = {}
        self.meta = {"alive": True}

