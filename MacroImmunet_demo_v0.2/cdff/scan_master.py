# cdff/scan_master.py

from collections import defaultdict


class ScanMaster:
    """
    ScanMaster = 环境感知层

    输入：
        World

    输出：
        region_signal_summary

    v0.2 特点：
        - 基于 region 聚合
        - 不涉及空间坐标
        - 为 ASI 预留接口
    """

    def __init__(self):
        pass

    # =========================
    # 主入口
    # =========================
    def scan(self, world, label_center):

        region_env = {}

        # 1️⃣ 先聚合 cell signals
        region_signals = defaultdict(self._init_region_signal)

        for cell in world.get_cells():

            region = cell.region
            signals = self._extract_signals(cell)

            for k, v in signals.items():
                region_signals[region][k] += v

        # 2️⃣ 合并 field（关键🔥）
        for region, signals in region_signals.items():

            region_fields = label_center.get_region_fields(region)
            field_to_node = {
                "IFN": "IFN_signal"
            }

            translated_fields = {}

            for k, v in region_fields.items():
                node_name = field_to_node.get(k, k)
                translated_fields[node_name] = v
            env = {}
            env.update(signals)        # cell-derived
            env.update(region_fields)  # field-derived（IFN等）

            region_env[region] = env

        return region_env

    # =========================
    # 信号提取（未来可扩展）
    # =========================

    def _extract_signals(self, cell):
        """
        从 cell 提取“可被环境感知”的信号

        v0.2：简化版本
        """

        signals = {}

        # 示例：用 node 模拟“分泌”
        if cell.get_node("NFkB") > 0.2:
            signals["NFkB_signal"] = cell.get_node("NFkB")

        if cell.get_node("IRF3") > 0.2:
            signals["IRF3_signal"] = cell.get_node("IRF3")

        # future:
        # IFN / cytokine / virus

        return signals

    # =========================
    # 初始化 region 容器
    # =========================

    def _init_region_signal(self):
        return {
            "NFkB_signal": 0.0,
            "IRF3_signal": 0.0
        }
