# test/test_cell_instance.py

from cdff.cell_instance.cell_instance import CellInstance


def test_basic():

    cell = CellInstance(
        cell_id="cell_1",
        cell_type="epithelial",
        base_values={"IFN_secretion_rate": 1.2},
        node_state={"NFkB": 0.5}
    )

    print("\n=== BASIC INFO ===")
    print(cell)

    print("\n=== NODE ACCESS ===")
    print("NFkB:", cell.get_node("NFkB"))
    print("IRF3 (missing):", cell.get_node("IRF3"))

    print("\n=== BASE ACCESS ===")
    print("IFN rate:", cell.get_base("IFN_secretion_rate"))
    print("missing base:", cell.get_base("unknown"))

    print("\n=== STEP ===")
    cell.step()
    print("age:", cell.age)

    print("\n=== SUMMARY ===")
    print(cell.summary())


if __name__ == "__main__":
    test_basic()
