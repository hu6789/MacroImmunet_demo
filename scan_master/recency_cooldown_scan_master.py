class RecencyCooldownScanMaster:
    def __init__(self, space=None, k=1, cooldown=1,
                 recency_bonus=1.0, cooldown_penalty=1.0):
        self.space = space
        self.k = k
        self.cooldown = cooldown
        self.recency_bonus = recency_bonus
        self.cooldown_penalty = cooldown_penalty

        # coord -> last_selected_tick
        self.last_selected = {}

    def scan(self, grid_summary, tick):
        candidates = []

        for coord, info in grid_summary.items():
            pmhc = info["labels"].get("PMHC", 0.0)
            if pmhc <= 0:
                continue

            # ---------- recency ----------
            last_tick = self.last_selected.get(coord)
            if last_tick is None:
                recency = self.recency_bonus
            else:
                dt = tick - last_tick
                recency = self.recency_bonus if dt > 0 else 0.0

            # ---------- cooldown ----------
            if last_tick is not None and (tick - last_tick) <= self.cooldown:
                cooldown_pen = self.cooldown_penalty
            else:
                cooldown_pen = 0.0

            score = pmhc + recency - cooldown_pen

            candidates.append({
                "coord": coord,
                "pmhc": pmhc,
                "score": score,
                "recency_bonus": recency,
                "cooldown_penalty": cooldown_pen,
            })

        # ---------- 稳定排序 ----------
        candidates.sort(
            key=lambda x: (
                -x["score"],
                -x["pmhc"],
                -x["recency_bonus"],
                x["coord"],          # 稳定 tie-break
            )
        )

        # ---------- Top-K ----------
        selected = candidates[: self.k]

        # ---------- 更新 last_selected ----------
        for item in selected:
            self.last_selected[item["coord"]] = tick

        # ---------- 输出 node ----------
        nodes = []
        for rank, item in enumerate(selected):
            nodes.append({
                "meta": {
                    "coord": item["coord"],
                    "rank": rank,
                    "score": item["score"],
                    "pmhc": item["pmhc"],
                    "recency_bonus": item["recency_bonus"],
                    "cooldown_penalty": item["cooldown_penalty"],
                }
            })

        return nodes

