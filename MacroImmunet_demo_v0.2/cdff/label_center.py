# cdff/label_center.py

from collections import defaultdict


class LabelCenter:
    """
    LabelCenter = 世界状态唯一写入源（SSOT）

    v0.2 功能：
    - 接收 intents
    - 聚合并写入 field（按 region）
    - 支持 secretion（当前唯一实现）

    架构保证：
    - 所有写 world 的操作必须经过这里
    - 支持未来 tick 末统一 apply
    """

    # =========================
    # 初始化
    # =========================

    def __init__(self):

        # world fields
        # 结构：
        # {
        #   "IL6": {"default": 1.2},
        #   "IFN": {"default": 0.8}
        # }
        self.fields = defaultdict(lambda: defaultdict(float))

        # intent 队列（tick buffer）
        self.intent_queue = []

    # =========================
    # 对外接口
    # =========================

    def submit(self, intents):
        """
        接收 intents（来自 CellMaster）
        """
        if not intents:
            return

        self.intent_queue.extend(intents)

    def apply(self, world):
        """
        应用所有 intents 到 world
        """

        if not self.intent_queue:
            return

        for intent in self.intent_queue:
            self._dispatch_intent(intent, world)

        # 清空队列（tick 结束）
        self.intent_queue = []

    # =========================
    # intent 分发
    # =========================

    def _dispatch_intent(self, intent, world):
    
        print("[LabelCenter] Applying:", intent)

        intent_type = intent.get("type")

        if intent_type == "secretion":
            self._apply_secretion(intent, world)

        elif intent_type == "state_update":
            self._apply_state_update(intent, world)

        elif intent_type == "fate": 
            self._apply_fate(intent, world)
        # 🔜 future:
        # elif intent_type == "damage":
        # elif intent_type == "movement":
        # elif intent_type == "division":

    # =========================
    # 具体行为实现
    # =========================

    def _apply_secretion(self, intent, world):
        """
        secretion → field 累加
        """

        cell_id = intent.get("cell_id")
        molecule = intent.get("target")
        strength = intent.get("strength", 0.0)

        # 找 cell
        cell = world.get_cell(cell_id)
        if cell is None:
            print(f"[LabelCenter] WARNING: cell {cell_id} not found")
            return

        region = cell.region

        # 写入 field
        self.fields[molecule][region] += strength
    def _apply_state_update(self, intent, world):

        cell = world.get_cell(intent["cell_id"])
        if not cell:
            return

        key = intent.get("target")
        value = intent.get("strength", 0.0)

        if not hasattr(cell, "meta"):
            cell.meta = {}

        # 累加 or 覆盖（推荐累加更真实）
        cell.meta[key] = cell.meta.get(key, 0.0) + value
    def _apply_fate(self, intent, world):

        cell = world.get_cell(intent["cell_id"])
        if not cell:
            return

        fate = intent.get("target")
 
        if not hasattr(cell, "meta"):
            cell.meta = {}

        cell.meta["fate"] = fate

        if fate == "apoptosis_commit":
            cell.alive = False

        # demo阶段可以先这样
            if fate == "apoptosis_commit":
                cell.alive = False
    # =========================
    # 读取接口（给 ScanMaster / debug 用）
    # =========================

    def get_field(self, molecule, region):
        return self.fields.get(molecule, {}).get(region, 0.0)

    def get_region_fields(self, region):
        """
        返回该 region 所有 molecule
        """
        result = {}
        for mol, regions in self.fields.items():
            result[mol] = regions.get(region, 0.0)
        return result

    def summary(self):
        """
        简单输出
        """
        return {
            mol: dict(regions)
            for mol, regions in self.fields.items()
        }
