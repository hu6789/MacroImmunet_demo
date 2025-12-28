class DefaultGeneGate:
    """
    Step3 placeholder gene gate.
    Allows everything.
    """
    def allow(self, gene_state, node_meta):
        return True

    def batch_filter(self, targets, node_meta):
        return targets

    def sample_fraction(self, items, fraction, rng=None):
        if fraction >= 1.0:
            return items
        if fraction <= 0.0:
            return []
        n = int(len(items) * fraction)
        return items[:n]


class DefaultIntentExecutor:
    """
    Step3 placeholder executor.
    Does nothing but accept intents.
    """
    def apply_intents(self, region_id, intents, tick=0):
        return []

