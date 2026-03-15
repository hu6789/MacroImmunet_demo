# tests/cell_tests/common/fake_env.py
from collections import defaultdict
from copy import deepcopy

class ScalarField:
    def __init__(self, name, size=(20,20), default=0.0):
        self.name = name
        self.size = size
        self.grid = defaultdict(lambda: default)  # sparse storage: (x,y) -> value
        self.tags = {}  # optional: (x,y) -> tag/list

    def get_at(self, pos):
        return self.grid.get(tuple(pos), 0.0)

    def set_at(self, pos, value, tag=None):
        self.grid[tuple(pos)] = value
        if tag:
            self.tags[tuple(pos)] = tag

    def add_at(self, pos, delta):
        self.grid[tuple(pos)] = self.get_at(pos) + delta

class FakeEnv:
    def __init__(self, grid_size=(20,20)):
        self.grid_size = grid_size
        # minimal fields dict available by name -> ScalarField
        self.fields = {}
        # trace of applied actions for reporting / debugging
        self.action_trace = []

    # field management
    def add_field(self, name, field_obj=None):
        if field_obj is None:
            field_obj = ScalarField(name, size=self.grid_size)
        self.fields[name] = field_obj
        return field_obj

    def get_field(self, name):
        return self.fields.get(name)

    def set_field(self, name, pos, value, tag=None):
        if name not in self.fields:
            self.add_field(name)
        self.fields[name].set_at(pos, value, tag=tag)

    def get_at(self, name, pos):
        f = self.get_field(name)
        if f is None:
            return 0.0
        return f.get_at(pos)

    def add_to_field(self, name, pos, delta):
        if name not in self.fields:
            self.add_field(name)
        self.fields[name].add_at(pos, delta)

    def sample_local_fields(self, pos):
        # return a dict of field_name -> value at pos
        return {name: f.get_at(pos) for name, f in self.fields.items()}

    # actions application (very minimal; behaviours can emit 'field_update' actions)
    def apply_actions(self, actions):
        for a in actions:
            self.action_trace.append(a)
            if not isinstance(a, dict):
                continue
            if a.get("type") == "field_update":
                fname = a.get("field")
                pos = tuple(a.get("pos", (0,0)))
                delta = a.get("delta", 0.0)
                if fname:
                    self.add_to_field(fname, pos, delta)
