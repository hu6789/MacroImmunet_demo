# world/labelcenter.py

from collections import defaultdict


class LabelCenter:

    def __init__(self, field_defs=None):
        self.intent_queue = []
        self.field_defs = field_defs or {}

    # =========================
    # 🧾 收集
    # =========================
    def collect(self, intents):
        if intents:
            self.intent_queue.extend(intents)

    # =========================
    # 🔥 主执行（tick末）
    # =========================
    def apply(self, world):

        # 👉 分桶（避免顺序影响）
        damage_events = []
        field_events = []
        death_events = []

        for intent in self.intent_queue:
            t = intent.get("type")

            if t == "damage_cell":
                damage_events.append(intent)
            elif t == "add_field":
                field_events.append(intent)
            elif t == "cell_die":
                death_events.append(intent)
                     
        self.field_defs = world.field_defs

        # =========================
        # 1️⃣ damage
        # =========================
        self._apply_damage(world, damage_events)

        # =========================
        # 2️⃣ field add
        # =========================
        self._apply_field(world, field_events)

        # =========================
        # 3️⃣ death（⚠️延后执行）
        # =========================
        self._apply_death(world, death_events)

        # =========================
        # 4️⃣ field diffusion
        # =========================
        self._apply_field_diffusion(world)

        # =========================
        # 5️⃣ field decay
        # =========================
        self._apply_field_decay(world)

        # =========================
        # 6️⃣ cleanup
        # =========================
        self._cleanup_dead_cells(world)

        # =========================
        # 🧹 clear
        # =========================
        self.intent_queue.clear()
       

    # =========================
    # 💥 damage
    # =========================
    def _apply_damage(self, world, events):

        acc = defaultdict(float)

        for intent in events:
            target = intent.get("target")
            strength = intent.get("strength", 0.0)

            if target is not None:
                acc[target] += strength

        for cid, dmg in acc.items():
            cell = world.cells.get(cid)

            if not cell or not cell.state_flags.get("alive", True):
                continue

            cell.node_state["damage"] = (
                cell.node_state.get("damage", 0.0) + dmg
            )

    # =========================
    # 🌍 field add
    # =========================
    def _apply_field(self, world, events):

        acc = defaultdict(lambda: defaultdict(float))

        for intent in events:
            field = intent.get("field")
            val = intent.get("value", 0.0)
            source = intent.get("source")

            cell = world.cells.get(source)
            if not cell or not cell.state_flags.get("alive", True):
                continue

            pos = tuple(cell.position)
            acc[field][pos] += val

        for fname, grid in acc.items():

            world.fields.setdefault(fname, {})

            # ✅ 读取 field 配置（如果没有就默认 max=1.0）
            cfg = self.field_defs.get(fname, {})
            max_val = cfg.get("max", 1.0)

            for pos, v in grid.items():

                old_val = world.fields[fname].get(pos, 0.0)
                new_val = old_val + v

                # 🔥 限制最大值（关键！）
                new_val = min(max_val, new_val)

                world.fields[fname][pos] = new_val

    # =========================
    # ☠️ death
    # =========================
    def _apply_death(self, world, events):

        for intent in events:
            cid = intent.get("target")
            cell = world.cells.get(cid)

            if cell:
                cell.state_flags["alive"] = False

    # =========================
    # 🌫 diffusion（4邻域 + 边界限制）
    # =========================
    def _apply_field_diffusion(self, world):

        for fname, grid in world.fields.items():

            cfg = self.field_defs.get(fname, {})
            rate = cfg.get("diffusion", 0.0)

            if rate <= 0:
                continue

            new_grid = defaultdict(float)

            for (x, y), val in grid.items():

                share = val * rate
                remain = val - share

                new_grid[(x, y)] += remain

                for dx, dy in [(1,0),(-1,0),(0,1),(0,-1)]:
                    nx, ny = x + dx, y + dy

                    # 👉 边界保护（🔥重要）
                    if 0 <= nx < world.width and 0 <= ny < world.height:
                        new_grid[(nx, ny)] += share / 4

            world.fields[fname] = dict(new_grid)

    # =========================
    # ⏳ decay
    # =========================
    def _apply_field_decay(self, world):

        for fname, grid in world.fields.items():

            cfg = self.field_defs.get(fname)
            tau = cfg.get("decay_tau", 10.0) if cfg else 10.0

            if not tau:
                continue

            new_grid = {}

            for pos, val in grid.items():

                new_val = val * (tau - 1) / tau

                if new_val > 1e-4:
                    new_grid[pos] = new_val

            world.fields[fname] = new_grid

    # =========================
    # 🧹 cleanup
    # =========================
    def _cleanup_dead_cells(self, world):

        dead_ids = [
            cid for cid, c in world.cells.items()
            if not c.state_flags.get("alive", True)
        ]

        for cid in dead_ids:
            world.remove_cell(cid)
