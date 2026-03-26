# HIR 参数集中管理（以后全局调这里）

HIR_PARAMS = {

    "cytokine_secretion": {
        "viral_weight": 1.2,
        "baseline": 0.2,
        "stress_weight": 0.3,
        "damage_weight": 0.2,
        "min_output": 0.1
    },

    "metabolism": {
        "energy_weight": 1.0,
        "stress_weight": 0.6,
        "viral_weight": 0.3,
        "min_output": 0.0
    },

    "stress_response": {
        "stress_weight": 1.0,
        "damage_weight": 0.5,
        "energy_penalty": 0.5,
        "min_output": 0.0
    },

    "fate_execution": {
        "baseline": 1.0
    }
}
