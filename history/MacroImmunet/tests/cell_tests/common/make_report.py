# tests/cell_tests/common/make_report.py
import json

def summarize_trace(trace):
    """
    Minimal one-page summary:
      - total_ticks
      - total_actions
      - first_exception (if any)
    """
    total_ticks = len(trace)
    total_actions = sum(len(t["actions"]) for t in trace)
    first_exc = None
    for t in trace:
        for cell_actions in t["actions"]:
            for a in cell_actions["actions"]:
                if a.get("name") in ("exception", "behavior_exception"):
                    first_exc = {"tick": t["tick"], "cell": cell_actions.get("cell"), "error": a.get("error")}
                    break
            if first_exc:
                break
        if first_exc:
            break
    summary = {
        "total_ticks": total_ticks,
        "total_actions": total_actions,
        "first_exception": first_exc
    }
    return summary

def write_report(path, trace):
    report = {"trace": trace, "summary": summarize_trace(trace)}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    return report

