from cdff.intentbuilder.intent_builder import IntentBuilder


def test_intentbuilder_builds_intent():

    builder = IntentBuilder()

    cell = {"id": 1}

    behaviors = [
        {"type": "kill", "target": 2}
    ]

    intents = builder.build(cell, behaviors)

    assert isinstance(intents, list)

    intent = intents[0]

    assert intent["type"] == "kill"
    assert intent["source"] == 1
    assert intent["target"] == 2
def test_intentbuilder_string_behavior():

    builder = IntentBuilder()

    cell = {"id": 1}

    behaviors = ["die"]

    intents = builder.build(cell, behaviors)

    assert intents[0]["type"] == "die"

