class HIRResult:
    """
    Physiological filtering result.
    """

    def __init__(self, allowed_behaviors=None, factors=None, fate=None):

        self.allowed_behaviors = allowed_behaviors or []
        self.factors = factors or {}
        self.fate = fate

    def to_dict(self):

        return {
            "allowed_behaviors": self.allowed_behaviors,
            "factors": self.factors,
            "fate": self.fate
        }
