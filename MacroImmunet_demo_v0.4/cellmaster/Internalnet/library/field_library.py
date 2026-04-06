# Internalnet/library/field_library.py

FIELD_DEFS = {
    "IFN_external": {
        "decay_tau": 5,
        "diffusion": 0.2
    },
    "TNF_external": {
        "decay_tau": 4,
        "diffusion": 0.15
    },
    "chemokine": {
        "decay_tau": 6,
        "diffusion": 0.25
    }
}


class FieldLibrary:

    def __init__(self):
        self.fields = FIELD_DEFS

    def get(self, name):
        return self.fields.get(name, {})

    def all(self):
        return self.fields
