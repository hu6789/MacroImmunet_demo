# Internalnet/library/interaction_library.py

class InteractionLibrary:

    def __init__(self):
        self.rules = {}

    def load(self, path=None):
        # 预留
        pass

    def get(self, key):
        return self.rules.get(key)
