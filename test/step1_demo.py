# step1_demo.py
from scan_master.space_adapter import SpaceAdapter

class DummySpace:
    def __init__(self):
        self.labels = [
            {"id": "L1", "type": "ANTIGEN", "mass": 2, "coord": (1, 2)},
            {"id": "L2", "type": "DEBRIS", "mass": 1, "coord": (1, 2)},
        ]
        self.agents = [
            {"id": "A1", "type": "DC", "coord": (0, 0)},
        ]

    def get_labels(self, region):
        return self.labels

    def get_agents(self, region):
        return self.agents

    def add_label(self, lb):
        self.labels.append(lb)

    def snapshot(self):
        return {
            "labels": self.labels,
            "agents": self.agents,
            "grid": None,
            "fields": {},
        }

if __name__ == "__main__":
    sp = DummySpace()
    ad = SpaceAdapter(sp)

    print("[labels]", ad.list_labels())
    print("[agents]", ad.list_agents())
    print("[summary]", ad.get_grid_summary())
    print("[snapshot]", ad.snapshot())

