import math


# -----------------------------
# 基础函数
# -----------------------------

def sigmoid(x):
    return 1.0 / (1.0 + math.exp(-x))


# -----------------------------
# weighted_sum_sigmoid
# 常用于 TF 激活
# -----------------------------

def weighted_sum_sigmoid(node, input_values, params):

    total = 0.0

    for i, inp in enumerate(node.inputs):

        # 优先用 w0 w1
        w = params.get(f"w{i}")

        # 如果没有，用 w_inputname
        if w is None:
            w = params.get(f"w_{inp}")

        # 再没有就默认1
        if w is None:
            w = 1.0

        total += w * input_values.get(inp, 0.0)

    bias = params.get("bias", 0.0)

    return 1.0 / (1.0 + math.exp(-(total + bias)))
# -----------------------------
# linear
# 简单线性组合
# -----------------------------

def linear(node, graph):

    total = 0.0

    for inp in node.inputs:

        if inp not in graph:
            continue

        value = graph[inp].get()

        w_key = "w_" + inp
        weight = node.params.get(w_key, 1.0)

        total += value * weight

    return total


# -----------------------------
# logic_and
# 生物 gating 常用
# -----------------------------

def logic_and(node, graph):

    for inp in node.inputs:

        if inp not in graph:
            return 0.0

        if graph[inp].get() <= 0:
            return 0.0

    return 1.0


# -----------------------------
# stress_accumulate
# 用于 stress / damage
# -----------------------------

def stress_accumulate(node, graph):

    prev = node.get()

    total = 0.0

    for inp in node.inputs:

        if inp not in graph:
            continue

        total += graph[inp].get()

    decay = node.params.get("decay", 0.1)

    new_val = prev * (1 - decay) + total

    return new_val


# -----------------------------
# resource_decay
# energy / ATP
# -----------------------------

def resource_decay(node, graph):

    prev = node.get()

    decay = node.params.get("decay", 0.05)

    return prev * (1 - decay)


# -----------------------------
# rule dispatcher
# -----------------------------

def run_rule(node, graph):

    rule_name = node.update_rule

    if rule_name not in RULE_REGISTRY:

        raise ValueError(f"Unknown rule: {rule_name}")

    rule = RULE_REGISTRY[rule_name]

    return rule(node, graph)
def identity(node, input_values, params):

    # 外部输入节点直接使用 state 值
    if node.node_id in input_values:
        return input_values[node.node_id]

    # fallback
    if input_values:
        return list(input_values.values())[0]

    return 0.0

# -----------------------------
# rule registry
# -----------------------------

RULE_REGISTRY = {

    "weighted_sum_sigmoid": weighted_sum_sigmoid,

    "linear": linear,

    "logic_and": logic_and,

    "stress_accumulate": stress_accumulate,

    "resource_decay": resource_decay,
    
    "identity": identity

}

