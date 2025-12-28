class Label:
    def __init__(self, label_id, mass=1.0, half_life=None):
        self.label_id = label_id
        self.mass = mass
        self.half_life = half_life

        self.owned_by = None
        self.age = 0.0

    def decay(self, dt):
        if self.half_life is None:
            return

        # 简化指数衰减（够用）
        decay_factor = 0.5 ** (dt / self.half_life)
        self.mass *= decay_factor

