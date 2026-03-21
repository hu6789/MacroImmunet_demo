# cdff/cell_master.py

from Internalnet.Internalnet_engine import run_internalnet
from intent.intent_builder import build_intents


class CellMaster:
    """
    CellMaster = 决策调度层

    作用：
        - 组织 cell 输入
        - 接入 ScanMaster 输出
        - 调用 InternalNet
        - 收集 intents
    """

    def __init__(self):
        pass

    # =========================
    # 主入口
    # =========================

    def process(self, world, scan_result):

        all_intents = []

        for cell in world.get_cells():

            print(f"\n[CellMaster] Running InternalNet for {cell.id}")

            region = cell.region
            env = scan_result.get(region, {})

            behaviors = run_internalnet(cell, external_input=env)

            intents = build_intents(behaviors, cell.id)

            print(f"  behaviors: {behaviors}")
            print(f"  intents: {intents}")

            all_intents.extend(intents)

        return all_intents

    # =========================
    # node_input 构造
    # =========================

    def _build_node_input(self, cell, region_signal):

        node_input = {}

        # 1️⃣ cell 内部状态
        for k, v in cell.node_state.items():
            node_input[k] = v

        # 2️⃣ 外部信号（简单加进去）
        for k, v in region_signal.items():
            node_input[k] = v

        return node_input

