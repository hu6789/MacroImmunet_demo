from Internalnet.hir.hir_engine import HIREngine
from Internalnet.hir.hir_rules import HIR_RULES


engine = HIREngine()


def run_case(name, state):

    print("\n====================")
    print("Scenario:", name)
    print("====================")

    print("State:", state)

    result = engine.evaluate(state)

    print("\nHIR Result:")
    print("Fate:", result["fate"])
    print("HIR factors:", result["factors"])

def main():

    run_case(
        "Healthy cell",
        {
            "energy": 0.8,
            "stress": 0.1,
            "damage": 0.0
        }
    )

    run_case(
        "Low energy",
        {
            "energy": 0.1,
            "stress": 0.2,
            "damage": 0.0
        }
    )

    run_case(
        "Severe damage",
        {
            "energy": 0.5,
            "stress": 0.7,
            "damage": 0.95
        }
    )


if __name__ == "__main__":
    main()
