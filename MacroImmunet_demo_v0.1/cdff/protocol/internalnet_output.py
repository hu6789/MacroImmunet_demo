class InternalNetOutput:
    """
    Output of InternalNet decision network.
    """

    def __init__(self, behaviors=None, state=None):

        self.behaviors = behaviors or []
        self.state = state or {}

    def to_dict(self):

        return {
            "behaviors": self.behaviors,
            "state": self.state
        }
