from cdff.cell_instance.cell_factory import CellFactory


def test_factory():

    factory = CellFactory(sigma=0.2)

    cells = factory.create_population(5)

    for c in cells:
        print(c)
        print("  base:", c.base_values)
        print("  node:", c.node_state)


if __name__ == "__main__":
    test_factory()
