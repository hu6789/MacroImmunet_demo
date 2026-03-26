# IntentBuilder/fate_filter.py

ALLOWED_BY_FATE = {
    "dying": ["apoptosis_commit", "necrosis"],
    "normal": "all",
    "stressed": "all"
}


def apply_fate_filter(specs, fate):
    """
    根据 fate 过滤 intent specs
    """

    if fate not in ALLOWED_BY_FATE:
        return specs

    allowed = ALLOWED_BY_FATE[fate]

    if allowed == "all":
        return specs

    return [
        s for s in specs
        if s["behavior_id"] in allowed
    ]
