HIR_RULES = {

    "energy_low": {
        "node": "energy",
        "threshold": 0.2,
        "effect": "suppress_proliferation"
    },

    "stress_high": {
        "node": "stress",
        "threshold": 0.8,
        "effect": "exhausted"
    },

    "damage_critical": {
        "node": "damage",
        "threshold": 0.9,
        "effect": "dying"
    }

}
