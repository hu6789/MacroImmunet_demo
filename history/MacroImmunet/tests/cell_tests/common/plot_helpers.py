# tests/cell_tests/common/plot_helpers.py
import pandas as pd
import matplotlib.pyplot as plt

def plot_time_series(df, cols=None, out_png=None, title=None):
    """
    df: pandas.DataFrame with 'tick' column
    cols: list of columns to plot (defaults to all except tick)
    """
    if cols is None:
        cols = [c for c in df.columns if c != 'tick']
    plt.figure(figsize=(8,4))
    for c in cols:
        plt.plot(df['tick'], df[c], label=c)
    plt.xlabel('tick')
    if title:
        plt.title(title)
    plt.legend()
    plt.tight_layout()
    if out_png:
        plt.savefig(out_png)
    else:
        plt.show()

