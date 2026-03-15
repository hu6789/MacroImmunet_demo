# cdff/scanmaster/interaction_library.py

INTERACTION_RULES = [

    {
        "name": "TCR_pMHC_contact",

        "source_cell": "CD8_T",
        "target_cell": "infected_cell",

        "signal": "pMHC_candidate",
        "strength": 1.0
    },

    {
        "name": "virus_contact",

        "source_cell": "epithelial_cell",
        "particle": "virus",

        "signal": "virus_binding",
        "strength": 1.0
    },

    {
        "name": "cytokine_sensing",

        "source_cell": "CD8_T",
        "field": "IL2",

        "signal": "IL2_signal",
        "strength": 1.0
    }
]
