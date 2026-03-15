# asi/specificity_matcher.py

from typing import Dict, List


def match_specificity(
    normalized_input: Dict,
    cell_profile: Dict,
) -> Dict:
    """
    Determine whether the cell recognizes any epitopes
    in the normalized specificity input.

    Parameters
    ----------
    normalized_input : dict
        Output from InputNormalizer.
        Expected to contain:
            - "epitopes": List[{"epitope_id": str, "type": str}]

    cell_profile : dict
        Read-only description of cell recognition capability.
        Expected to contain:
            - "recognition": {
                  receptor_name: List[epitope_id]
              }

    Returns
    -------
    dict
        {
            "matched": bool,
            "matches": [
                {
                    "epitope_id": str,
                    "via": str,
                }
            ]
        }
    """
    epitopes: List[Dict] = normalized_input.get("epitopes", [])
    recognition: Dict[str, List[str]] = cell_profile.get("recognition", {})

    matches: List[Dict] = []

    for ep in epitopes:
        ep_id = ep.get("epitope_id")
        if ep_id is None:
            continue

        for receptor, known_epitopes in recognition.items():
            if ep_id in known_epitopes:
                matches.append({
                    "epitope_id": ep_id,
                    "via": receptor,
                })

    return {
        "matched": len(matches) > 0,
        "matches": matches,
    }

