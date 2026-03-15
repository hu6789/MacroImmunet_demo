# cdff/scanmaster/event_builder.py

def build_node_input(events):

    signals = {}

    for event in events:

        signal = event["signal"]
        strength = event["strength"]

        signals[signal] = signals.get(signal, 0) + strength

    node_input = {

        "signals": signals,
        "events": events
    }

    return node_input
