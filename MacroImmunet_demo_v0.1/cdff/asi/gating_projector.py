# asi/gating_projector.py

from typing import Dict, List


def project_gating(
    normalized_input: Dict,
    match_result: Dict,
) -> Dict:
    """
    Project specificity match result into a gating signal
    consumable by InternalNet signal processing.

    This function does NOT decide actions.
    """

    matches: List[Dict] = match_result.get("matches", [])

    present = bool(match_result.get("matched", False))
    num_matches = len(matches)

    vias = []
    for m in matches:
        via = m.get("via")
        if via and via not in vias:
            vias.append(via)

    return {
        "present": present,
        "activation_bias": num_matches,
        "details": {
            "num_matches": num_matches,
            "vias": vias,
        }
    }

