class InternalNet:

    def __init__(self):
        pass

    def forward(self, cell_state):

        # 兼容 ASI pipeline
        return {
            "behaviors": []
        }

    def step(self, cell_state, signals):

        behaviors = []

        if signals.get("pMHC"):
            behaviors.append({
                "type": "kill",
                "target": signals.get("target_cell")
            })

        return {
            "behaviors": behaviors
        }
