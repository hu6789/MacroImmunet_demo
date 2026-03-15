from cdff.Internalnet.engine.internalnet_engine import InternalNetEngine


class InternalNetAdapter:

    def __init__(self):

        # 先加载 CD8 网络
        self.engine = InternalNetEngine(
            graph_path="cdff/Internalnet/CD8_TCELL_INTERNALNET_GRAPH_v1.json"
        )

    def run(self, cell, processed_input):

        signals = processed_input.get("signals", {})

        # ===== DEBUG 打印 =====
        print("\n[InternalNetAdapter] INPUT SIGNALS")
        print(signals)

        # 转换为 node_state
        node_state = {}

        for k, v in signals.items():
            node_state[k] = v

        # ===== DEBUG =====
        print("[InternalNetAdapter] NODE STATE")
        print(node_state)

        # 跑 internalnet
        output = self.engine.run(node_state)

        # ===== DEBUG =====
        print("[InternalNetAdapter] INTERNALNET OUTPUT")
        print(output)

        behaviors = output.get("behaviors", [])

        return {
            "behaviors": behaviors,
            "state_summary": output
        }

    # 兼容旧接口
    def forward(self, cell_state):

        return self.run(cell_state, {"signals": {}})
