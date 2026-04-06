class World:
    def __init__(self, width, height, grid_size=1.0, field_defs=None):

        self.width = width
        self.height = height
        self.grid_size = grid_size

        # 🔹 SSOT
        self.cells = {}   # id → cell
        self.fields = {}  # field_name → {(x,y): value}
        self.field_defs = field_defs or {}

        # 🔹 grid index
        self.grid = {}    # (i,j) → [cell_id]
        

    # =========================
    # 📦 cell 管理
    # =========================
    def add_cell(self, cell):
        self.cells[cell.cell_id] = cell
        self._add_to_grid(cell)

    def remove_cell(self, cid):
        cell = self.cells.pop(cid, None)
        if cell:
            self._remove_from_grid(cell)

    # =========================
    # 📍 grid 操作
    # =========================
    def _grid_key(self, position):
        x, y = position
        return (int(x / self.grid_size), int(y / self.grid_size))

    def _add_to_grid(self, cell):
        key = self._grid_key(cell.position)
        self.grid.setdefault(key, []).append(cell.cell_id)

    def _remove_from_grid(self, cell):
        key = self._grid_key(cell.position)
        if key in self.grid:
            if cell.id in self.grid[key]:
                self.grid[key].remove(cell.cell_id)

    # =========================
    # 🔄 移动
    # =========================
    def move_cell(self, cid, new_pos):
        cell = self.cells.get(cid)
        if not cell:
            return

        self._remove_from_grid(cell)
        cell.position = new_pos
        self._add_to_grid(cell)

    # =========================
    # 👀 邻居查询（ScanMaster 用）
    # =========================
    def get_neighbors(self, cell, radius=1):

        cx, cy = self._grid_key(cell.position)

        neighbors = []

        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):

                key = (cx + dx, cy + dy)

                for nid in self.grid.get(key, []):
                    if nid == cell.cell_id:
                        continue

                    nb = self.cells.get(nid)
                    if nb and nb.state_flags.get("alive", True):
                        neighbors.append(nb)

        return neighbors
