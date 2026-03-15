# cdff/demo/demo_world.py
# Minimal world for testing/demo purposes

class DemoWorld:
    """A minimal mock world for testing ScanMaster/CellMaster/etc."""

    def __init__(self):
        self.cells = [
            {"id": "cell_1", "type": "epithelial", "state": "healthy"},
            {"id": "cell_2", "type": "virus", "state": "free"},
        ]

    def get_neighbors(self, cell):
        """Return neighboring cells. For demo, all other cells except self."""
        return [c for c in self.cells if c["id"] != cell["id"]]

    def summary(self):
        """Return a simple summary of the world."""
        return [{"id": c["id"], "type": c["type"], "state": c["state"]} for c in self.cells]
