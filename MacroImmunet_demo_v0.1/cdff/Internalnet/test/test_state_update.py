from Internalnet.state_update.state_update_engine import StateUpdateEngine


def test_state_update():

    engine = StateUpdateEngine()

    state = {
        "energy": 1.0,
        "stress": 0.0
    }

    new_state = engine.update(state)

    assert new_state["energy"] < 1.0
    assert new_state["stress"] > 0.0
