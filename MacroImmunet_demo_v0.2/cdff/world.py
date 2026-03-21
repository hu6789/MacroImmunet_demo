# cdff/world.py

class World:
    """
    World = 仿真容器（v0.2 极简版）

    只负责：
    - 存储 cell
    - 提供基础访问接口

    不负责：
    - 空间计算
    - 物理过程
    """

    def __init__(self):
        self.cells = []

    # =========================
    # Cell 管理
    # =========================

    def add_cell(self, cell):
        self.cells.append(cell)

    def get_cells(self):
        return self.cells

    # =========================
    # Debug
    # =========================

    def summary(self):
        return {
            "cell_count": len(self.cells)
        }

    def __repr__(self):
        return f"<World cells={len(self.cells)}>"
    def get_cell(self, cell_id):
        for c in self.cells:
            if c.id == cell_id:
                return c
        return None
