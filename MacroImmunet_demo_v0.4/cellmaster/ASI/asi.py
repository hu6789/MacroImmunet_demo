class ASI:

    def __init__(self):
        pass

    def run(self, cell, scan_output):

        best_target = None
        best_score = 0.0
 
        for c in scan_output.get("cell_contacts", []):

            target_id = c["cell_id"]
            pmhc = c.get("pMHC", 0.0)

            specificity = cell.feature_params.get("TCR_match", 1.0)

            match_score = pmhc * specificity

            if match_score > best_score:
                best_score = match_score
                best_target = target_id

        return {
            "selected_target": best_target,
            "signals": {
                "TCR_external": best_score
            }
        }
