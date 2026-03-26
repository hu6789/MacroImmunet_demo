# Internalnet/cell/cell_factory.py

import json
import os
import random
import numpy as np

from .cell_instance import Cell


class CellFactory:

    def __init__(self):
        base_dir = os.path.dirname(__file__)
        self.type_dir = os.path.join(base_dir, "cell_types")

        # ✅ 关键：在这里做“个体差异采样”
    def create(self, cell_type="test_cell"):

        path = os.path.join(self.type_dir, f"{cell_type}.json")

        with open(path, "r") as f:
            config = json.load(f)

        cell = Cell(config)

        # 1️⃣ 基础分布
        self._apply_distribution(cell)

        # 2️⃣ subtype（🔥新增）
        if "subtypes" in config:
            subtype_name = random.choice(list(config["subtypes"].keys()))
            subtype_params = config["subtypes"][subtype_name]

            for k, spec in subtype_params.items():
                cell.feature_params[k] = self._sample_param(spec)

            cell.meta["subtype"] = subtype_name

        return cell

    # =========================
    # 🔹 参数采样
    # =========================
    def _sample_param(self, spec):

        if isinstance(spec, (int, float)):
            return spec

        mean = spec.get("mean", 1.0)
        std = spec.get("std", 0.0)
        dist = spec.get("dist", "normal")

        if dist == "normal":
            return max(0.0, random.gauss(mean, std))

        elif dist == "lognormal":
            return np.random.lognormal(mean=0, sigma=std) * mean

        else:
            return mean

    def _apply_distribution(self, cell):

        for k, spec in cell.feature_params.items():
            cell.feature_params[k] = self._sample_param(spec)
