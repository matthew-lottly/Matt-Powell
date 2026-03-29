#!/usr/bin/env python3
"""Generate paper figures from benchmark outputs.

Produces grouped bar charts for marginal coverage, mean width, and ECE from
`outputs/real_method_comparison.csv` and `outputs/real_data_benchmark.csv`.
Also attempts to draw schematic site and location maps using available real-data
loaders; if loaders are unavailable, falls back to simple network schematics.
"""
from pathlib import Path
import sys
import traceback

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx

# Publication defaults
plt.rcParams.update({
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.labelsize": 11,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "axes.grid": True,
    "grid.alpha": 0.3,
    "axes.spines.top": False,
    "axes.spines.right": False,
})

# Colorblind-friendly palette
COLORS = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#D55E00"]

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "figures"
OUT.mkdir(parents=True, exist_ok=True)


def read_csv_safe(path):
    p = Path(path)
    if not p.exists():
        print(f"Missing: {p}")
        return None
    return pd.read_csv(p)


def plot_grouped_metrics(df, dataset_col, method_col, metrics, out_prefix):
    grouped = df.groupby([dataset_col, method_col]).mean().reset_index()
    datasets = grouped[dataset_col].unique()
    methods = grouped[method_col].unique()

    for metric in metrics:
        fig, ax = plt.subplots(figsize=(7, 4.5))
        width = 0.75 / len(methods)
        x = range(len(datasets))
        for i, m in enumerate(sorted(methods)):
            vals = []
            for d in datasets:
                row = grouped[(grouped[dataset_col] == d) & (grouped[method_col] == m)]
                if not row.empty:
                    vals.append(float(row.iloc[0][metric]))
                else:
                    vals.append(0.0)
            color = COLORS[i % len(COLORS)]
            ax.bar([xi + i*width for xi in x], vals, width=width, label=m,
                   color=color, edgecolor="black", linewidth=0.5, alpha=0.85)
        ax.set_xticks([xi + width*(len(methods)-1)/2 for xi in x])
        ax.set_xticklabels(datasets, fontweight="bold")
        ax.set_ylabel(metric.replace("_", " ").title())
        ax.set_title(metric.replace("_", " ").title(), fontweight="bold")
        if metric == "marginal_cov":
            ax.axhline(0.9, color="#d62728", ls="--", lw=1.2, label="Target")
        ax.legend(framealpha=0.9)
        fig.tight_layout()
        out = OUT / f"{out_prefix}_{metric}.png"
        fig.savefig(out)
        print(f"Wrote {out}")
        plt.close(fig)


def draw_schematic(graph, name):
    G = graph
    if not isinstance(G, nx.Graph):
        try:
            G = nx.from_numpy_array(G)
        except Exception:
            try:
                n = int(getattr(G, 'number_of_nodes', lambda: len(G))())
            except Exception:
                n = 50
            G = nx.erdos_renyi_graph(n, 0.05)
    pos = nx.spring_layout(G, seed=2)
    fig, ax = plt.subplots(figsize=(7, 7))
    nx.draw_networkx_nodes(G, pos, node_size=35, node_color="#0072B2",
                           alpha=0.8, ax=ax, edgecolors="black", linewidths=0.3)
    nx.draw_networkx_edges(G, pos, alpha=0.3, edge_color="#999999",
                           width=0.6, ax=ax)
    ax.set_title(name.replace("_", " "), fontweight="bold", fontsize=13)
    ax.set_axis_off()
    out = OUT / f"{name.replace(' ', '_').lower()}.png"
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)
    print(f"Wrote {out}")


def try_draw_real_maps():
    # Try to import loaders from the package
    try:
        from src.hetero_conformal.real_data import load_activsg200, load_ieee118
        print("Found real-data loaders; attempting to load graphs...")
        try:
            G1 = load_activsg200()
            draw_schematic(G1, "ACTIVSg200_site_map")
        except Exception:
            print("Could not draw ACTIVSg200 from loader:")
            traceback.print_exc()
        try:
            G2 = load_ieee118()
            draw_schematic(G2, "IEEE118_site_map")
        except Exception:
            print("Could not draw IEEE118 from loader:")
            traceback.print_exc()
    except Exception:
        print("Real-data loaders not available; drawing placeholder schematics.")
        # Draw placeholders
        draw_schematic(nx.erdos_renyi_graph(200, 0.02, seed=1), "ACTIVSg200_site_map")
        draw_schematic(nx.erdos_renyi_graph(118, 0.03, seed=2), "IEEE118_site_map")


def main():
    df_cmp = read_csv_safe(ROOT / 'outputs' / 'real_method_comparison.csv')
    df_bench = read_csv_safe(ROOT / 'outputs' / 'real_data_benchmark.csv')
    metrics = ['marginal_cov', 'mean_width', 'ece']
    if df_cmp is not None:
        plot_grouped_metrics(df_cmp, 'dataset', 'method', metrics, 'method_comparison')
    if df_bench is not None:
        try:
            plot_grouped_metrics(df_bench, 'dataset', 'method', metrics, 'real_benchmark')
        except KeyError:
            print("Skipping real_benchmark plots: expected column 'method' not found.")

    try_draw_real_maps()


if __name__ == '__main__':
    main()
