# tests/cell_tests/common/fake_env.py
"""
Minimal fake engine for cell unit tests.
Provides: read_field, set_field_point, add_to_field, emit_event, emit_intent, neighbor helpers, simple logging.
"""
from collections import defaultdict
import json

class FakeEnv:
    def __init__(self, grid_size=(11,11)):
        self.fields = defaultdict(dict)  # field_id -> { coord_tuple: value }
        self.events = []   # list of (tick, event_type, payload)
        self.intents = []  # list of (tick, intent_type, payload)
        self.tick = 0
        self.grid_size = grid_size

    # Field helpers
    def set_field_point(self, field_id, coord, value):
        self.fields[field_id][tuple(coord)] = float(value)
    def read_field(self, field_id, coord):
        return float(self.fields.get(field_id, {}).get(tuple(coord), 0.0))
    def add_to_field(self, field_id, coord, amount):
        old = self.read_field(field_id, coord)
        self.fields[field_id][tuple(coord)] = old + float(amount)
        return self.fields[field_id][tuple(coord)]

    # Neighbor helpers (4-neighborhood)
    def get_neighbor_coords(self, coord):
        x,y = coord
        cand = [(x+1,y),(x-1,y),(x,y+1),(x,y-1)]
        # keep within grid bounds
        xs, ys = self.grid_size
        valid = [c for c in cand if 0 <= c[0] < xs and 0 <= c[1] < ys]
        return valid

    def find_best_neighbor_by_field_gradient(self, coord, field_id, max_dist=1):
        cur = self.read_field(field_id, coord)
        best = None; best_v = cur
        for nb in self.get_neighbor_coords(coord):
            v = self.read_field(field_id, nb)
            if v > best_v:
                best_v = v; best = nb
        return best

    # Logging / events / intents
    def emit_event(self, event_type, payload):
        self.events.append((self.tick, event_type, payload))
    def emit_intent(self, intent_type, payload):
        self.intents.append((self.tick, intent_type, payload))
    def log_event(self, tick, name, payload):
        # keep in events as well for easy test introspection
        self.events.append((tick, name, payload))

    # Dump helper (useful in failing tests)
    def snapshot(self):
        return {
            'tick': self.tick,
            'fields': {k: dict(v) for k,v in self.fields.items()},
            'events': list(self.events),
            'intents': list(self.intents),
        }

    # advance tick (optional)
    def step(self):
        self.tick += 1

