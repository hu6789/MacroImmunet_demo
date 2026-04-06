# scanmaster/scanmaster.py

from collections import defaultdict

class ScanMaster:

    def __init__(self, world):
        """
        world: 你的 World 实例
        """
        self.world = world

    # =========================
    # 主扫描接口
    # =========================
    def scan_cell(self, cell):
 
        pos = tuple(cell.position)

        # ✅ 1️⃣ 邻居细胞
        neighbors = self.world.get_neighbors(cell)

        # ✅ 2️⃣ contact-based signals
        contacts = []
        for nb in neighbors:
            contacts.append({
                "cell_id": nb.cell_id,
                "pMHC": nb.node_state.get("pMHC", 0.0),
                "costim": nb.node_state.get("costim", 0.0)
            })

        # ✅ 3️⃣ field signals
        neighborhood = self._get_neighborhood(pos, radius=1)
        ligand_summary = self._scan_ligands(neighborhood)
        context_tags = self._scan_context(cell, neighborhood)

        return {
            "cell_id": cell.cell_id,
            "position": pos,
            "ligand_summary": ligand_summary,
            "cell_contacts": contacts,   # ⭐ 核心！
            "context_tags": context_tags
        }


    # =========================
    # 获取邻域坐标
    # =========================
    def _get_neighborhood(self, pos, radius=1):

        x, y = pos
        width, height = self.world.width, self.world.height

        neighbors = []
        for dx in range(-radius, radius+1):
            for dy in range(-radius, radius+1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < width and 0 <= ny < height:
                    neighbors.append((nx, ny))

        return neighbors

    # =========================
    # 扫描 neighborhood 中的 ligand
    # =========================
    def _scan_ligands(self, neighborhood):
        """
        汇总 neighborhood 内的 field
        返回 dict: {ligand_name: total_value}
        """
        ligand_totals = defaultdict(float)

        for fname, grid in self.world.fields.items():
            for pos in neighborhood:
                val = grid.get(pos, 0.0)
                if val > 0:
                    ligand_totals[fname] += val

        return dict(ligand_totals)

    # =========================
    # 扫描 context tag
    # =========================
    def _scan_context(self, cell, neighborhood):
        """
        返回环境标记，例如 hotspot, stress_zone
        """
        tags = []

        # 检测热点: 如果邻域中某 field > 阈值
        for fname, grid in self.world.fields.items():
            cfg = self.world.field_defs.get(fname, {})

            threshold = cfg.get("hotspot_threshold")
            if threshold is None:
                continue
            for pos in neighborhood:
                if grid.get(pos, 0.0) >= threshold:
                    tags.append(f"hotspot_{fname}")
                    break

        # 其他 tag 可以扩展，例如氧化应激区、感染区等
        # ...

        return tags
