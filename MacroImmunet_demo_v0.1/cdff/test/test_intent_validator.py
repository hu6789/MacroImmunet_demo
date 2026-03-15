from cdff.intent.intent_validator import validate_intent


def test_valid_intent():

    intent = {

        "type": "die",

        "source": 1

    }

    assert validate_intent(intent)


def test_invalid_intent_type():

    intent = {

        "type": "explode",

        "source": 1

    }

    try:

        validate_intent(intent)

        assert False

    except ValueError:

        assert True
