# cdff/cell_instance/cell_factory.py

import random
from cdff.cell_instance import CellInstance


class CellFactory:

    def __init__(self, sigma=0.1):
        self.sigma = sigma

    def create_epithelial_cell(self, cell_id: str, region="default"):

        # === baseline（可扩展） ===
        base_template = {
            "IFN_secretion_rate": 1.0,
            "NFkB_sensitivity": 1.0,
            "stress_resistance": 1.0
        }

        # === 加随机扰动 ===
        base_values = {
            k: v * random.normalvariate(1.0, self.sigma)
            for k, v in base_template.items()
        }

        # === 初始 node 状态 ===
        node_state = {
            "NFkB": random.uniform(0.0, 0.2),
            "IRF3": random.uniform(0.0, 0.2),
            "stress": random.uniform(0.0, 0.2),
        }

        return CellInstance(
            cell_id=cell_id,
            cell_type="epithelial",
            base_values=base_values,
            node_state=node_state,
            region=region
        )

    def create_population(self, n: int, cell_type="epithelial"):

        cells = []

        for i in range(n):

            if cell_type == "epithelial":
                cell = self.create_epithelial_cell(f"cell_{i}")

            else:
                raise ValueError(f"Unsupported cell type: {cell_type}")

            cells.append(cell)

        return cells
