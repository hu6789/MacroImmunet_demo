from Internalnet.behavior.behavior_engine import BehaviorEngine


def test_behavior_engine():

    engine = BehaviorEngine()

    node_values = {
        "NFAT": 0.7,
        "IL2": 0.7
    }

    hir_result = {
        "fate": None,
        "hir_flags": {}
    }

    behaviors = engine.generate(node_values, hir_result)

    assert "produce_IL2" in behaviors
