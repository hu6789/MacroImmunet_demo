import json
import os

from cellmaster.cellmaster import CellMaster
from scanmaster.scanmaster import ScanMaster
from world.labelcenter import LabelCenter
from cellmaster.cell.cell_factory import CellFactory
from world.world import World

from cellmaster.Internalnet.Internalnet_engine import InternalNet
from cellmaster.ASI.asi import ASI
from cellmaster.inputbuilder.input_builder import InputBuilder
from cellmaster.intentbuilder.intent_builder import IntentBuilder


# =========================
# Load behaviors
# =========================
def load_behaviors(path):
    behaviors = []
    target_dir = os.path.join(path, "behavior_node")

    for root, _, files in os.walk(target_dir):
        for f in files:
            if f.endswith(".json"):
                with open(os.path.join(root, f)) as fp:
                    data = json.load(fp)
                    if "behavior_id" in data:
                        behaviors.append(data)

    return behaviors


# =========================
# 🔥 Scenario（最小测试）
# =========================
def build_scenario():

    field_defs = {
        "IFN_external": {
            "diffusion": 0.2,
            "decay_tau": 5,
            "max": 1.0
        }
    }

    cells = [
        {"type": "cd8_t_cell", "position": (1, 1)},
        {"type": "infected_cell", "position": (2, 2)}
    ]

    return field_defs, cells

def load_scenario(path):
    with open(path) as f:
        return json.load(f)
# =========================
# 🔁 Simulation Loop
# =========================
def run_simulation(scenario_path, steps=10):

    scenario = load_scenario(scenario_path)
    
    # 🔹 world
    field_defs = scenario.get("field_defs", {})
    
    world = World(
        width=scenario["world"]["width"],
        height=scenario["world"]["height"]
    )
    
    world.field_defs = field_defs

    label_center = LabelCenter(field_defs=field_defs)

    # 🔹 modules
    behaviors = load_behaviors("cellmaster/Internalnet/behavior")
    print("Loaded behaviors:", [b["behavior_id"] for b in behaviors])
    
    net = InternalNet(behaviors)
    asi = ASI()
    input_builder = InputBuilder()
    intent_builder = IntentBuilder()

    cell_master = CellMaster(net, asi, input_builder, intent_builder)
    scan_master = ScanMaster(world)
    factory = CellFactory()

    # 🔹 cells
    for c in scenario["cells"]:
        cell = factory.create(
            position=tuple(c["position"]),
            cell_type=c["type"]
        )
        world.add_cell(cell)
    print("Initial cells:", list(world.cells.keys()))

    # 🔹 initial fields
    for fname, points in scenario.get("fields", {}).items():
        world.fields[fname] = {}
        for x, y, val in points:
            world.fields[fname][(x, y)] = val
            
        steps = scenario.get("steps", 10)

    # =========================
    # 🔁 主循环
    # =========================
    for t in range(steps):
        print(f"\n===== TICK {t} =====")

        all_intents = []

        for cell in list(world.cells.values()):

            # 1️⃣ scan
            scan_output = scan_master.scan_cell(cell)

            # 2️⃣ decision
            intents, result, external_field = cell_master.step(
                cell, world, scan_output
            )

            all_intents.extend(intents)

            # 🔥 Debug（你想要的！）
            print(f"\nCell {cell.cell_id} ({cell.cell_type})")
            print("  input:", external_field)
            print("  activation:", round(cell.node_state.get("activation_signal", 0), 3))
            print("  subtype:", cell.meta.get("subtype"))
            print("  receptor_pMHC:", cell.receptor_params.get("pMHC"))
            print("  damage:", round(cell.node_state.get("damage", 0), 3))
            print("  fate:", result.get("fate"))
            print("  behaviors:", [b["behavior_id"] for b in result.get("behaviors", [])])
            print("  intents:", intents)
            
            if intents:
                print("  ⚡ events triggered!")

        # 3️⃣ apply
        label_center.collect(all_intents)
        label_center.apply(world)

        # 🌍 world debug（🔥很重要）
        total_ifn = sum(world.fields.get("IFN_external", {}).values())
        print("\nWorld IFN total:", round(total_ifn, 3))
        print("Alive cells:", list(world.cells.keys()))

# =========================
# 🚀 Main
# =========================
import sys

if __name__ == "__main__":
    scenario_path = sys.argv[1] if len(sys.argv) > 1 else "scenarios/test_minimal.json"
    run_simulation(scenario_path, steps=10)
