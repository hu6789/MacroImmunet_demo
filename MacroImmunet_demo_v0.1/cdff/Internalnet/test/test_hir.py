from Internalnet.hir.hir_engine import HIREngine


engine = HIREngine()


def run_case(name, state, behaviors):

    print("\n====================")
    print("Scenario:", name)
    print("====================")

    print("State:", state)
    print("Base behaviors:", behaviors)

    result = engine.evaluate(state, behaviors)

    print("\nHIR Factors:")
    print(result["factors"])

    print("\nFinal behaviors:")
    print(result["behaviors"])

    print("\nFate:")
    print(result["fate"])



def main():

    base_behaviors = {
        "proliferation_rate": 1.0,
        "IL2_output": 1.0
    }

    run_case(
        "Healthy cell",
        {
            "energy": 0.9,
            "stress": 0.1,
            "damage": 0.0
        },
        base_behaviors
    )

    run_case(
        "Low energy",
        {
            "energy": 0.2,
            "stress": 0.2,
            "damage": 0.0
        },
        base_behaviors
    )

    run_case(
        "High stress",
        {
            "energy": 0.8,
            "stress": 0.7,
            "damage": 0.0
        },
        base_behaviors
    )

    run_case(
        "Severe damage",
        {
            "energy": 0.6,
            "stress": 0.6,
            "damage": 0.95
        },
        base_behaviors
    )


if __name__ == "__main__":
    main()
