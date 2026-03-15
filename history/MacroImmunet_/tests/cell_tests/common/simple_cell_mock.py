# tests/cell_tests/common/simple_cell_mock.py
class SimpleCellMock:
    def __init__(self, id="cellA", state="resting", position=(0,0), meta=None):
        self.id = id
        self.state = state
        self.position = tuple(position)
        self.meta = meta or {}
        self.actions = []

    def apply_action(self, action):
        # record action for assertions
        self.actions.append(action)

    def set_state(self, state):
        self.state = state

    def get_position(self):
        return self.position

    def get_meta(self, key, default=None):
        return self.meta.get(key, default)

    def set_meta(self, key, value):
        self.meta[key] = value

