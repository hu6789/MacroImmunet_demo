from Internalnet.asi.asi_engine import asi_check


def run_case(name, peptide, tcr, costim):

    print("\n==============================")
    print("Scenario:", name)
    print("==============================")

    result = asi_check(peptide, tcr, costim)

    print("\n=== ASI Check ===")
    print("Peptide:", result["peptide"])
    print("TCR motif:", result["tcr_motif"])
    print("Match score:", result["match_score"])
    print("Costimulation:", result["costimulation"])

    print("\nSignal1 (TCR recognition):", result["signal1"])
    print("Signal2 (Costimulation):", result["signal2"])

    if not result["permission"]:
        print("\nASI Decision: Activation blocked")
        return

    print("\nASI Decision: Activation permitted")

    # 模拟 InternalNet signaling
    print("\n=== InternalNet Signaling ===")

    NFAT = 0.88
    IL2 = 0.96

    print("NFAT activation:", NFAT)
    print("IL2 production:", IL2)

    print("\nBehaviors:")
    print(" - produce_IL2")
    print(" - proliferate")


def main():

    tcr = "VILVF"

    run_case(
        "Antigen mismatch",
        peptide="AAAAAAA",
        tcr=tcr,
        costim=0.8
    )

    run_case(
        "No costimulation",
        peptide="SIINFEKL",
        tcr=tcr,
        costim=0.2
    )

    run_case(
        "Full activation",
        peptide="SIINFEKL",
        tcr=tcr,
        costim=0.8
    )


if __name__ == "__main__":
    main()
