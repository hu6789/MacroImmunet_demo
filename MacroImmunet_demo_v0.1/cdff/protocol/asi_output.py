class ASIOutput:
    """
    Output of AdaptiveSpecificityInterpreter.
    """

    def __init__(self, matches=None, activation_prob=0.0, signal_bias=None):

        self.matches = matches or []
        self.activation_prob = activation_prob
        self.signal_bias = signal_bias or {}

    def to_dict(self):
        return {
            "matches": self.matches,
            "activation_prob": self.activation_prob,
            "signal_bias": self.signal_bias
        }
