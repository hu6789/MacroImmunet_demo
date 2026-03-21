# cdff/cell_instance/cell_instance.py

class CellInstance:
    """
    CellInstance = 单个细胞的状态容器（Data Holder）

    不包含任何决策逻辑，仅存储：
    - node_state（动态）
    - base_values（个体差异）
    - metadata（状态标签）

    所有行为计算交由 InternalNet 完成
    """

    def __init__(
        self,
        cell_id: str,
        cell_type: str,
        base_values: dict = None,
        node_state: dict = None,
        region: str = "default"
    ):
        # =========================
        # 基础身份
        # =========================
        self.cell_id = cell_id
        self.id = cell_id
        self.type = cell_type
        self.region = region

        # =========================
        # 个体差异（核心）
        # =========================
        self.base_values = base_values if base_values else {}
        self.node_state = node_state if node_state else {}

        # =========================
        # 状态信息（未来用）
        # =========================
        self.state = "healthy"
        self.age = 0

        # =========================
        # 调试 / 标签
        # =========================
        self.tags = {}

    # =========================
    # 安全访问（防 missing node）
    # =========================

    def get_node(self, name: str, default: float = 0.0) -> float:
        """
        安全获取 node 值
        """
        return self.node_state.get(name, default)

    def set_node(self, name: str, value: float):
        """
        设置 node 值
        """
        self.node_state[name] = value

    def get_base(self, name: str, default: float = 1.0) -> float:
        """
        安全获取 base value
        """
        return self.base_values.get(name, default)

    # =========================
    # 生命周期（可选）
    # =========================

    def step(self):
        """
        每 tick 调用（未来扩展用）
        """
        self.age += 1

    # =========================
    # Debug / 打印
    # =========================

    def summary(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "region": self.region,
            "state": self.state,
            "age": self.age,
        }

    def __repr__(self):
        return f"<Cell {self.id} | type={self.type} | region={self.region}>"
