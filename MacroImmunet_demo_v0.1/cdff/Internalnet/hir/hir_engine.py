class HIREngine:

    def __init__(self):
        pass


    def compute_factors(self, state):

        energy = state.get("energy", 1.0)
        stress = state.get("stress", 0.0)
        damage = state.get("damage", 0.0)

        energy_factor = max(0.1, energy)
        stress_factor = max(0.1, 1.0 - stress)
        damage_factor = max(0.1, 1.0 - damage)

        return {
            "energy_factor": energy_factor,
            "stress_factor": stress_factor,
            "damage_factor": damage_factor
        }


    def decide_fate(self, state):

        damage = state.get("damage", 0)

        if damage > 0.9:
            return "dying"

        return None


    def evaluate(self, state):

        factors = self.compute_factors(state)
        fate = self.decide_fate(state)

        return {
            "fate": fate,
            "factors": factors
        }
    def filter_behaviors(self, cell_state, behaviors):
        return self.evaluate(behaviors)
