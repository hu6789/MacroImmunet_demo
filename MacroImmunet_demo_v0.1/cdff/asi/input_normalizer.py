# asi/input_normalizer.py
# NormalizedSpecificityInput = {
#     "antigen_id": str,
#     "epitopes": [
#         {
#             "epitope_id": str,
#             "type": "T" | "B" | "Ab",
#             "confidence": float,
#             "signal_strength": float,
#             "affinity_hint": float | None,
#         }
#     ],
#     "presentation_context": {
#         "mhc_class": "I" | "II" | None,
#         "cell_type": str | None,
#     }
# }
def normalize_specificity_input(raw_input, source=None):

    if raw_input is None:
        return {"epitopes": []}

    # test_asi_pipeline 用的结构
    if "epitopes" in raw_input:
        return {
            "epitopes": raw_input.get("epitopes", [])
        }

    # scanmaster pipeline 的结构
    if "events" in raw_input:

        epitopes = []

        for e in raw_input.get("events", []):

            if e.get("signal") == "pMHC_candidate":
                epitopes.append({
                    "epitope_id": e.get("epitope_id", "unknown")
                })

        return {
            "epitopes": epitopes
        }

    return {"epitopes": []}
