class Space:

    def __init__(self, size=(5, 5)):
        self.size = size

        # grid[x][y] = field dict
        self.grid = {}

        for x in range(size[0]):
            for y in range(size[1]):
                self.grid[(x, y)] = {
                    "IFN": 0.0,
                    "IL6": 0.0,
                    "TNF": 0.0,
                    "virus": 0.0
                }

        self.cell_positions = {}  # cell_id → (x, y)

    # =========================
    # 🔹 cell 管理
    # =========================
    def diffuse(self):
        new_grid = {}

        for pos, fields in self.grid.items():

            neighbors = self.get_neighbors(pos)

            for f, v in fields.items():
                avg = v * 0.5

                for n in neighbors:
                    avg += self.grid.get(n, {}).get(f, 0.0) * 0.5 / len(neighbors)

                new_grid.setdefault(pos, {})[f] = avg

        self.grid = new_grid
    def place_cell(self, cell_id, pos):
        self.cell_positions[cell_id] = pos

    def get_cell_pos(self, cell_id):
        return self.cell_positions.get(cell_id, (0, 0))

    # =========================
    # 🔹 field 操作
    # =========================

    def get_local_field(self, pos, key):
        return self.grid[pos].get(key, 0.0)

    def add_local_field(self, pos, key, value):
        self.grid[pos][key] += value

    # =========================
    # 🔹 diffusion（下一步）
    # =========================

    def diffuse(self):
        pass  # 先留空
