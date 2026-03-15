class NodeInput:
    """
    Input from ScanMaster to CellMaster / ASI.
    """

    def __init__(self, signals=None, events=None, context=None):

        self.signals = signals or {}
        self.events = events or []
        self.context = context or {}

    def to_dict(self):
        return {
            "signals": self.signals,
            "events": self.events,
            "context": self.context
        }
