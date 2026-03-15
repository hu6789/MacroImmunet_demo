# master_base.py
from math import floor
from typing import List, Dict, Tuple

class BaseMaster:
    """
    基类：每个 tick 被调用一次；子类实现 scan_space(), score_cell/coord(), decide_from_scores()
    输出: list of intents (dict)
    """
    def __init__(self, space, env, params=None):
        self.space = space
        self.env = env
        self.params = params or {}
        self.mode = "healthy"   # or "emergency"

    def tick(self):
        # top-level entry: scan -> score -> decide -> emit
        scan_items = self.scan_space()
        scored = self.score_items(scan_items)
        intents = self.decide_from_scores(scored)
        # post-process intents (emit events)
        for it in intents:
            try:
                if hasattr(self.env, "emit_event"):
                    self.env.emit_event("master_intent", {"master": self.__class__.__name__, "intent": it})
            except Exception:
                pass
        return intents

    def scan_space(self):
        """返回要评估的 items（coord 或 cell counts）; 子类 override"""
        raise NotImplementedError

    def score_items(self, items):
        """给每个 item 返回一个 score (item, score)"""
        scored = []
        for it in items:
            s = self.score_item(it)
            scored.append((it, s))
        return scored

    def score_item(self, item):
        """默认评分：基于 Field_Antigen_Density 密度；子类可重写"""
        coord = item
        fd = self.space.fields.get("Field_Antigen_Density")
        if not fd:
            return 0.0
        x,y = coord
        try:
            val = float(fd[y][x])
            # 简单 normalize
            return val
        except Exception:
            return 0.0

    def decide_from_scores(self, scored_items):
        """从 scored_items 选 top-K 并输出 intents。子类可 override"""
        if not scored_items:
            return []
        scored_items.sort(key=lambda t: t[1], reverse=True)
        maxk = int(self.params.get("max_hotspots", 3))
        out = []
        for (item, score) in scored_items[:maxk]:
            # default: if score>0 -> attempt infect
            if score <= 0:
                continue
            intent = {
                "space": self.space.id,
                "coord": item,
                "action": "attempt_infect",
                "strength": float(score) * float(self.params.get("infection_intent_strength", 0.1))
            }
            out.append(intent)
        return out

