class Intent:

    def __init__(self, intent_type, source, target=None, payload=None):

        self.intent_type = intent_type
        self.source = source
        self.target = target
        self.payload = payload or {}

    def to_dict(self):

        return {
            "intent_type": self.intent_type,
            "source": self.source,
            "target": self.target,
            "payload": self.payload
        }
