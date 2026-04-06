# Internalnet/library/intent_library.py

INTENT_TYPES = {
    "damage_cell": {
        "required": ["source", "target", "strength"]
    },
    "add_field": {
        "required": ["field", "value", "source"]
    },
    "cell_die": {
        "required": ["target"]
    }
}


class IntentLibrary:

    def __init__(self):
        self.intents = INTENT_TYPES

    def get(self, intent_type):
        return self.intents.get(intent_type)

    def all(self):
        return self.intents
