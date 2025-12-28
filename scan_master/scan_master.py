from collections import defaultdict

class ScanMaster:
    """
    Step2.5 mini ScanMaster
    - read label snapshot
    - aggregate antigen release
    - emit hotspot events
    """

    def __init__(self, config=None):
        cfg = dict(config or {})
        self.antigen_threshold = float(cfg.get("antigen_threshold", 1.0))
    def rank_events(events, current_tick=None):
        """
        Step4.7.4
        Rank ScanEvents by priority.
        Priority = type_weight + recency + signal
        """
        if not events:
            return []

        if current_tick is None:
            current_tick = max(e.tick for e in events)

        type_weight = {
            "danger_signal": 3.0,
            "cytokine_peak": 2.0,
            "antigen_peak": 1.0,
        }

        def priority(e):
            recency = 1.0 / (1 + (current_tick - e.tick))
            base = type_weight.get(e.type, 0.5)
            return base * 10 + recency + e.value

        return sorted(events, key=priority, reverse=True)


