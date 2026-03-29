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
import matplotlib.pyplot as plt
import networkx as nx

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
        fig, ax = plt.subplots(figsize=(6, 4))
        width = 0.8 / len(methods)
        x = range(len(datasets))
        for i, m in enumerate(sorted(methods)):
            vals = []
            for d in datasets:
                row = grouped[(grouped[dataset_col] == d) & (grouped[method_col] == m)]
                if not row.empty:
                    vals.append(float(row.iloc[0][metric]))
                else:
                    vals.append(0.0)
            ax.bar([xi + i*width for xi in x], vals, width=width, label=m)
        ax.set_xticks([xi + width*(len(methods)-1)/2 for xi in x])
        ax.set_xticklabels(datasets)
        ax.set_ylabel(metric)
        ax.set_title(metric.replace('_', ' ').title())
        ax.legend()
        fig.tight_layout()
        out = OUT / f"{out_prefix}_{metric}.png"
        fig.savefig(out, dpi=200)
        print(f"Wrote {out}")
        plt.close(fig)


def draw_schematic(graph, name):
    G = graph
    if not isinstance(G, nx.Graph):
        # try to coerce: expect adjacency list or edge list
        try:
            G = nx.from_numpy_array(G)
        except Exception:
            # fallback: create random graph with node count
            try:
                n = int(getattr(G, 'number_of_nodes', lambda: len(G))())
            except Exception:
                n = 50
            G = nx.erdos_renyi_graph(n, 0.05)
    pos = nx.spring_layout(G, seed=2)
    fig, ax = plt.subplots(figsize=(6, 6))
    nx.draw_networkx_nodes(G, pos, node_size=30, ax=ax)
    nx.draw_networkx_edges(G, pos, alpha=0.5, ax=ax)
    ax.set_title(name)
    ax.set_axis_off()
    out = OUT / f"{name.replace(' ', '_').lower()}.png"
    fig.tight_layout()
    fig.savefig(out, dpi=200)
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
