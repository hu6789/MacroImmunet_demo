from cdff.intent.intent_schema import REQUIRED_FIELDS
from cdff.intent.intent_types import ALLOWED_INTENT_TYPES

def validate_intent(intent):
    """
    Validate intent structure
    """

    # 检查 required 字段
    for field in REQUIRED_FIELDS:
        if field not in intent:
            raise ValueError(f"Intent missing field: {field}")

    # 检查 type
    intent_type = intent["type"]

    if intent_type not in ALLOWED_INTENT_TYPES:
        raise ValueError(f"Unknown intent type: {intent_type}")

    return True
