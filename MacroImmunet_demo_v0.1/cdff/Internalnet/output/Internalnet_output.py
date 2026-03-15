class InternalNetOutput:
    """
    Standard output object of InternalNet.

    This object is the ONLY interface exposed to CellMaster.
    """

    def __init__(
        self,
        state_summary,
        filtered_behaviors,
        fate_actions
    ):
        self.state_summary = state_summary
        self.filtered_behaviors = filtered_behaviors
        self.fate_actions = fate_actions

    def to_dict(self):
        return {
            "state_summary": self.state_summary,
            "filtered_behaviors": self.filtered_behaviors,
            "fate_actions": self.fate_actions
        }
