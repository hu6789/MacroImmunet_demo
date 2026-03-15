from Internalnet.behavior.behavior_rules import BEHAVIOR_RULES


class BehaviorEngine:

    def generate(self, node_values, hir_result):

        behaviors = []

        # 如果细胞正在死亡，不产生行为
        if hir_result.get("fate") == "dying":
            return behaviors

        factors = hir_result.get("factors", {})

        energy_factor = factors.get("energy_factor", 1.0)
        stress_factor = factors.get("stress_factor", 1.0)
        damage_factor = factors.get("damage_factor", 1.0)

        for behavior, rule in BEHAVIOR_RULES.items():

            node = rule["node"]
            threshold = rule["threshold"]

            value = node_values.get(node, 0)

            # 根据行为类型应用不同调节
            if behavior == "proliferate":
                value *= energy_factor

            if behavior == "produce_IL2":
                value *= stress_factor

            value *= damage_factor

            if value > threshold:
                behaviors.append(behavior)

        return behaviors
