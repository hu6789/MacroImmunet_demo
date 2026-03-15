HYDROPHOBIC = set(["A","V","I","L","M","F","Y","W"])

def hydrophobic_score(seq):

    if len(seq) == 0:
        return 0

    score = 0

    for aa in seq:
        if aa in HYDROPHOBIC:
            score += 1

    return score / len(seq)


def asi_check(peptide, tcr_motif, costimulation,
              match_threshold=0.6,
              costim_threshold=0.5):

    p_score = hydrophobic_score(peptide)
    t_score = hydrophobic_score(tcr_motif)

    match_score = 1 - abs(p_score - t_score)

    signal1 = match_score >= match_threshold
    signal2 = costimulation >= costim_threshold

    permission = signal1 and signal2

    return {
        "peptide": peptide,
        "tcr_motif": tcr_motif,
        "match_score": round(match_score, 3),
        "costimulation": costimulation,
        "signal1": signal1,
        "signal2": signal2,
        "permission": permission
    }

