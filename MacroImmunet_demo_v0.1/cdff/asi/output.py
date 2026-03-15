# asi/output.py

def build_asi_output(*, gating_result, adapter_patch):
    """
    Build the unified output structure of ASI.

    This function defines what ASI officially produces,
    regardless of internal implementation details.
    """
    return {
        "gating": gating_result,
        "patch": adapter_patch,
    }

