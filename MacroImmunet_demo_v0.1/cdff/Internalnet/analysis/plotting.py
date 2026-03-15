import matplotlib.pyplot as plt


def plot_curve(x, y, xlabel, ylabel, title=None):

    plt.figure()

    plt.plot(x, y, marker="o")

    plt.xlabel(xlabel)
    plt.ylabel(ylabel)

    if title:
        plt.title(title)

    plt.grid(True)

    plt.show()


def plot_multi_curve(x, curves, xlabel, ylabel, title=None):

    plt.figure()

    for name, y in curves.items():
        plt.plot(x, y, marker="o", label=name)

    plt.xlabel(xlabel)
    plt.ylabel(ylabel)

    if title:
        plt.title(title)

    plt.legend()
    plt.grid(True)

    plt.show()
