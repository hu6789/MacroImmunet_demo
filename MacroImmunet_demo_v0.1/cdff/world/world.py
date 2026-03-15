class World:

    def __init__(self, width, height):
        self.width = width
        self.height = height

        # cell id -> CellInstance
        self.cells = {}

        # grid occupancy
        self.grid = {}

        # molecule fields
        self.fields = {}

    def add_cell(self, cell):
        self.cells[cell.id] = cell
        self.grid[cell.position] = cell.id

    def get_cell_at(self, pos):
        cid = self.grid.get(pos)
        if cid is None:
            return None
        return self.cells[cid]
