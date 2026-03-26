"""Full benchmark: 20-seed comparison, CSV output, tables, plots, and maps.

Usage:
    cd projects/conformal-heterogeneous-gnn
    python scripts/run_benchmark.py
"""

from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

import numpy as np

# Ensure src is importable even without editable install
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from hetero_conformal.experiment import ExperimentConfig, run_experiment
from hetero_conformal.graph import generate_synthetic_infrastructure

OUT_DIR = Path(__file__).resolve().parent.parent / "outputs"
OUT_DIR.mkdir(exist_ok=True)

SEED_COUNT = int(os.environ.get("SEED_COUNT", "20"))
SEEDS = list(range(SEED_COUNT))
ALPHAS = [0.05, 0.10, 0.15, 0.20]
LAMBDAS = [0.0, 0.1, 0.3, 0.5, 1.0]
NODE_TYPES = ["power", "water", "telecom"]


# ── helpers ──────────────────────────────────────────────────────────────────

def _cfg(seed: int, alpha: float = 0.1, lam: float = 0.3, prop: bool = True) -> ExperimentConfig:
    return ExperimentConfig(
        seed=seed, alpha=alpha,
        neighborhood_weight=lam,
        use_propagation_aware=prop,
        epochs=200, patience=20,
    )


# ── 1. Baseline comparison (10 seeds) ───────────────────────────────────────

def run_baseline_sweep() -> list[dict]:
    rows: list[dict] = []
    for seed in SEEDS:
        # compare mondrian CP, CHMP (mean), CHMP (median), CHMP (median+floor)
        variants = [
            ("mondrian_cp", False, 0.0, None, 0.0),
            ("chmp_mean", True, 0.3, "mean", 0.0),
            ("chmp_median", True, 0.3, "median", 0.0),
            ("chmp_median_floor", True, 0.3, "median", 0.1),
        ]

        for method, prop, lam, agg, floor in variants:
            cfg = _cfg(seed, alpha=0.1, lam=lam, prop=prop)
            if agg is not None:
                cfg.neighbor_agg = agg
                cfg.trimmed_frac = 0.0
                cfg.floor_sigma = floor

            r = run_experiment(cfg, verbose=False)
            row = {
                "seed": seed,
                "method": method,
                "marginal_cov": r.marginal_cov,
                "mean_width": r.mean_width,
                "ece": r.ece,
            }
            for nt in NODE_TYPES:
                row[f"cov_{nt}"] = r.type_cov.get(nt, float("nan"))
                row[f"width_{nt}"] = r.interval_widths.get(nt, float("nan"))
                row[f"rmse_{nt}"] = r.rmse.get(nt, float("nan"))
            rows.append(row)
            print(f"  seed={seed} {method}: cov={r.marginal_cov:.4f} width={r.mean_width:.4f}")
    return rows


# ── 2. Lambda sensitivity (10 seeds × 5 lambdas) ───────────────────────────

def run_lambda_sweep() -> list[dict]:
    rows: list[dict] = []
    for seed in SEEDS:
        for lam in LAMBDAS:
            prop = lam > 0
            cfg = _cfg(seed, alpha=0.1, lam=lam, prop=prop)
            r = run_experiment(cfg, verbose=False)
            row = {
                "seed": seed, "lambda": lam,
                "marginal_cov": r.marginal_cov,
                "mean_width": r.mean_width,
                "ece": r.ece,
            }
            for nt in NODE_TYPES:
                row[f"cov_{nt}"] = r.type_cov.get(nt, float("nan"))
                row[f"width_{nt}"] = r.interval_widths.get(nt, float("nan"))
            rows.append(row)
    return rows


# ── 3. Alpha sweep (10 seeds × 4 alphas, CHMP only) ────────────────────────

def run_alpha_sweep() -> list[dict]:
    rows: list[dict] = []
    for seed in SEEDS:
        for alpha in ALPHAS:
            cfg = _cfg(seed, alpha=alpha, lam=0.3, prop=True)
            r = run_experiment(cfg, verbose=False)
            row = {
                "seed": seed, "alpha": alpha,
                "marginal_cov": r.marginal_cov,
                "mean_width": r.mean_width,
                "ece": r.ece,
            }
            for nt in NODE_TYPES:
                row[f"cov_{nt}"] = r.type_cov.get(nt, float("nan"))
                row[f"width_{nt}"] = r.interval_widths.get(nt, float("nan"))
            rows.append(row)
    return rows


# ── CSV helpers ──────────────────────────────────────────────────────────────

def _write_csv(path: Path, rows: list[dict]):
    if not rows:
        return
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote {path}")


# ── Tables (Markdown) ───────────────────────────────────────────────────────

def build_summary_table(rows: list[dict], group_col: str, path: Path):
    """Aggregate rows by `group_col` and write a Markdown table."""
    groups: dict[str, list[dict]] = {}
    for r in rows:
        k = str(r[group_col])
        groups.setdefault(k, []).append(r)

    lines = [
        f"| {group_col} | Marginal Cov | Mean Width | ECE |"
        + "".join(f" Cov {nt} |" for nt in NODE_TYPES),
        "| --- | ---: | ---: | ---: |" + " ---: |" * len(NODE_TYPES),
    ]
    for k in sorted(groups, key=lambda x: (x if not x.replace(".", "").replace("-","").isdigit() else float(x))):
        g = groups[k]
        mc = np.mean([r["marginal_cov"] for r in g])
        mw = np.mean([r["mean_width"] for r in g])
        me = np.mean([r["ece"] for r in g])
        type_covs = "".join(
            f" {np.mean([r[f'cov_{nt}'] for r in g]):.4f} |"
            for nt in NODE_TYPES
        )
        lines.append(f"| {k} | {mc:.4f} | {mw:.4f} | {me:.4f} |{type_covs}")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  wrote {path}")


# ── Plots ────────────────────────────────────────────────────────────────────

def plot_baseline_boxplots(rows: list[dict]):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
    metrics = [("marginal_cov", "Marginal Coverage"), ("mean_width", "Mean Width"), ("ece", "ECE")]
    methods = sorted({r["method"] for r in rows})

    for ax, (col, title) in zip(axes, metrics):
        data = [[r[col] for r in rows if r["method"] == m] for m in methods]
        bp = ax.boxplot(data, tick_labels=methods, patch_artist=True)
        colors = ["#4C72B0", "#DD8452"]
        for patch, color in zip(bp["boxes"], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)
        if col == "marginal_cov":
            ax.axhline(0.9, color="red", ls="--", lw=1, label="target 0.90")
            ax.legend(fontsize=8)
        ax.set_title(title)
        ax.grid(axis="y", alpha=0.3)

    fig.suptitle(f"Baseline Comparison ({SEED_COUNT} seeds, α=0.10)", fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "baseline_boxplots.png", dpi=150)
    plt.close(fig)
    print("  wrote baseline_boxplots.png")


def plot_coverage_by_type(rows: list[dict]):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    methods = sorted({r["method"] for r in rows})
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))

    for ax, nt in zip(axes, NODE_TYPES):
        col = f"cov_{nt}"
        data = [[r[col] for r in rows if r["method"] == m] for m in methods]
        bp = ax.boxplot(data, tick_labels=methods, patch_artist=True)
        colors = ["#4C72B0", "#DD8452"]
        for patch, color in zip(bp["boxes"], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)
        ax.axhline(0.9, color="red", ls="--", lw=1)
        ax.set_title(f"{nt.capitalize()} Coverage")
        ax.set_ylim(0.6, 1.05)
        ax.grid(axis="y", alpha=0.3)

    fig.suptitle(f"Per-Type Coverage ({SEED_COUNT} seeds, α=0.10)", fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "coverage_by_type.png", dpi=150)
    plt.close(fig)
    print("  wrote coverage_by_type.png")


def plot_lambda_sensitivity(rows: list[dict]):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    lambdas_sorted = sorted(set(r["lambda"] for r in rows))
    mean_cov = [np.mean([r["marginal_cov"] for r in rows if r["lambda"] == l]) for l in lambdas_sorted]
    std_cov = [np.std([r["marginal_cov"] for r in rows if r["lambda"] == l]) for l in lambdas_sorted]
    mean_w = [np.mean([r["mean_width"] for r in rows if r["lambda"] == l]) for l in lambdas_sorted]
    std_w = [np.std([r["mean_width"] for r in rows if r["lambda"] == l]) for l in lambdas_sorted]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.5))
    ax1.errorbar(lambdas_sorted, mean_cov, yerr=std_cov, marker="o", capsize=3)
    ax1.axhline(0.9, color="red", ls="--", lw=1, label="target")
    ax1.set_xlabel("λ (neighborhood weight)")
    ax1.set_ylabel("Marginal Coverage")
    ax1.set_title("Coverage vs λ")
    ax1.legend()
    ax1.grid(alpha=0.3)

    ax2.errorbar(lambdas_sorted, mean_w, yerr=std_w, marker="s", capsize=3, color="#DD8452")
    ax2.set_xlabel("λ (neighborhood weight)")
    ax2.set_ylabel("Mean Interval Width")
    ax2.set_title("Efficiency vs λ")
    ax2.grid(alpha=0.3)

    fig.suptitle(f"Lambda Sensitivity ({SEED_COUNT} seeds, α=0.10)", fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "lambda_sensitivity.png", dpi=150)
    plt.close(fig)
    print("  wrote lambda_sensitivity.png")


def plot_alpha_calibration(rows: list[dict]):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    alphas_sorted = sorted(set(r["alpha"] for r in rows))
    mean_cov = [np.mean([r["marginal_cov"] for r in rows if r["alpha"] == a]) for a in alphas_sorted]
    targets = [1 - a for a in alphas_sorted]

    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot([0.75, 1.0], [0.75, 1.0], "k--", lw=1, label="ideal")
    ax.scatter(targets, mean_cov, s=80, zorder=5, label=f"CHMP (mean over {SEED_COUNT} seeds)")
    for t, mc in zip(targets, mean_cov):
        ax.annotate(f"α={1-t:.2f}", (float(t), float(mc)), textcoords="offset points", xytext=(8, -8), fontsize=8)
    ax.set_xlabel("Target Coverage (1−α)")
    ax.set_ylabel("Empirical Coverage")
    ax.set_title("Calibration Plot")
    ax.legend()
    ax.grid(alpha=0.3)
    ax.set_xlim(0.75, 1.0)
    ax.set_ylim(0.75, 1.0)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "alpha_calibration.png", dpi=150)
    plt.close(fig)
    print("  wrote alpha_calibration.png")


# ── Spatial map ──────────────────────────────────────────────────────────────

def plot_spatial_map(seed: int = 0):
    """Plot a spatial map of the graph with node risk scores and intervals."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection

    cfg = _cfg(seed, alpha=0.1, lam=0.3, prop=True)
    graph = generate_synthetic_infrastructure(
        n_power=cfg.n_power, n_water=cfg.n_water, n_telecom=cfg.n_telecom,
        feature_dim=cfg.feature_dim, coupling_prob=cfg.coupling_prob,
        coupling_radius=cfg.coupling_radius, seed=cfg.seed,
    )
    r = run_experiment(cfg, verbose=False)

    fig, axes = plt.subplots(1, 3, figsize=(18, 5.5))
    cmap = plt.cm.RdYlGn_r  # type: ignore[attr-defined]
    markers = {"power": "^", "water": "s", "telecom": "o"}
    titles = [
        "Risk Scores (Ground Truth)",
        "Prediction Intervals (Width)",
        "Coverage Map (Hit/Miss)",
    ]

    for ax, title in zip(axes, titles):
        ax.set_title(title, fontsize=11)
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.set_aspect("equal")

    # Panel 1: ground truth risk
    ax = axes[0]
    sc = None
    for nt in NODE_TYPES:
        pos = graph.node_positions[nt]
        labels = graph.node_labels[nt]
        sc = ax.scatter(pos[:, 0], pos[:, 1], c=labels, cmap=cmap,
                        marker=markers[nt], s=30, alpha=0.8, edgecolors="k",
                        linewidths=0.3, vmin=0, vmax=1, label=nt)
    if sc is not None:
        fig.colorbar(sc, ax=ax, label="Risk Score", shrink=0.8)
    ax.legend(loc="lower left", fontsize=8)

    # Panel 2: interval widths on test nodes
    assert r.conformal_result is not None, "conformal_result is required for plotting"
    ax = axes[1]
    sc = None
    for nt in NODE_TYPES:
        test_mask = graph.node_masks[nt]["test"]
        pos = graph.node_positions[nt][test_mask]
        widths = r.conformal_result.upper[nt] - r.conformal_result.lower[nt]
        sc = ax.scatter(pos[:, 0], pos[:, 1], c=widths, cmap="YlOrRd",
                        marker=markers[nt], s=35, alpha=0.85, edgecolors="k",
                        linewidths=0.3, label=nt)
    if sc is not None:
        fig.colorbar(sc, ax=ax, label="Interval Width", shrink=0.8)
    ax.legend(loc="lower left", fontsize=8)

    # Panel 3: coverage hit/miss
    ax = axes[2]
    for nt in NODE_TYPES:
        test_mask = graph.node_masks[nt]["test"]
        pos = graph.node_positions[nt][test_mask]
        true = graph.node_labels[nt][test_mask]
        lo = r.conformal_result.lower[nt]
        hi = r.conformal_result.upper[nt]
        hit = (true >= lo) & (true <= hi)
        colors = ["#2ca02c" if h else "#d62728" for h in hit]
        ax.scatter(pos[:, 0], pos[:, 1], c=colors,
                   marker=markers[nt], s=35, alpha=0.85, edgecolors="k",
                   linewidths=0.3, label=nt)
    # manual legend for hit/miss
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#2ca02c", markersize=8, label="Covered"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#d62728", markersize=8, label="Missed"),
    ]
    ax.legend(handles=legend_elements, loc="lower left", fontsize=8)

    # Draw some cross-edges lightly in all panels
    for ax_i in axes:
        for (src_type, rel, dst_type), ei in graph.edge_index.items():
            if src_type == dst_type or ei.shape[1] == 0:
                continue
            src_pos = graph.node_positions[src_type]
            dst_pos = graph.node_positions[dst_type]
            # sample up to 200 edges for visual clarity
            n_draw = min(200, ei.shape[1])
            idx = np.random.default_rng(0).choice(ei.shape[1], n_draw, replace=False)
            segs = np.stack([src_pos[ei[0, idx]], dst_pos[ei[1, idx]]], axis=1)
            segs_list = segs.tolist()
            lc = LineCollection(segs_list, colors="gray", alpha=0.06, linewidths=0.3)
            ax_i.add_collection(lc)

    fig.suptitle(f"Spatial Infrastructure Map (seed={seed}, α=0.10)", fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "spatial_map.png", dpi=150)
    plt.close(fig)
    print("  wrote spatial_map.png")


def plot_per_type_width_map(seed: int = 0):
    """One map per infrastructure type showing interval width heatmap."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    cfg = _cfg(seed, alpha=0.1, lam=0.3, prop=True)
    graph = generate_synthetic_infrastructure(
        n_power=cfg.n_power, n_water=cfg.n_water, n_telecom=cfg.n_telecom,
        feature_dim=cfg.feature_dim, coupling_prob=cfg.coupling_prob,
        coupling_radius=cfg.coupling_radius, seed=cfg.seed,
    )
    r = run_experiment(cfg, verbose=False)

    assert r.conformal_result is not None, "conformal_result is required for plotting"

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    markers = {"power": "^", "water": "s", "telecom": "o"}

    for ax, nt in zip(axes, NODE_TYPES):
        test_mask = graph.node_masks[nt]["test"]
        pos = graph.node_positions[nt][test_mask]
        widths = r.conformal_result.upper[nt] - r.conformal_result.lower[nt]
        sc = ax.scatter(pos[:, 0], pos[:, 1], c=widths, cmap="YlOrRd",
                        marker=markers[nt], s=50, alpha=0.9,
                        edgecolors="k", linewidths=0.4)
        fig.colorbar(sc, ax=ax, shrink=0.8, label="Width")
        ax.set_title(f"{nt.capitalize()} — Interval Width", fontsize=11)
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.set_aspect("equal")
        ax.grid(alpha=0.2)

    fig.suptitle(f"Per-Type Interval Width Maps (seed={seed})", fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "per_type_width_map.png", dpi=150)
    plt.close(fig)
    print("  wrote per_type_width_map.png")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("CHMP Benchmark Suite")
    print("=" * 60)

    # 1. Baseline comparison
    print(f"\n[1/6] Baseline comparison ({SEED_COUNT} seeds)…")
    baseline_rows = run_baseline_sweep()
    _write_csv(OUT_DIR / "baseline_comparison.csv", baseline_rows)
    build_summary_table(baseline_rows, "method", OUT_DIR / "baseline_table.md")
    plot_baseline_boxplots(baseline_rows)
    plot_coverage_by_type(baseline_rows)

    # 2. Lambda sensitivity
    print(f"\n[2/6] Lambda sensitivity ({SEED_COUNT} seeds × {len(LAMBDAS)} lambdas)…")
    lambda_rows = run_lambda_sweep()
    _write_csv(OUT_DIR / "lambda_sensitivity.csv", lambda_rows)
    build_summary_table(lambda_rows, "lambda", OUT_DIR / "lambda_table.md")
    plot_lambda_sensitivity(lambda_rows)

    # 3. Alpha calibration
    print(f"\n[3/6] Alpha sweep ({SEED_COUNT} seeds × {len(ALPHAS)} alphas)…")
    alpha_rows = run_alpha_sweep()
    _write_csv(OUT_DIR / "alpha_sweep.csv", alpha_rows)
    build_summary_table(alpha_rows, "alpha", OUT_DIR / "alpha_table.md")
    plot_alpha_calibration(alpha_rows)

    # 4. Spatial maps
    print("\n[4/6] Spatial risk / coverage / width map (seed 0)…")
    plot_spatial_map(seed=0)

    print("\n[5/6] Per-type width maps (seed 0)…")
    plot_per_type_width_map(seed=0)

    # 6. Summary JSON
    print("\n[6/6] Writing final summary…")
    summary = {
        "baseline": _aggregate(baseline_rows, "method"),
        "lambda": _aggregate_num(lambda_rows, "lambda"),
        "alpha": _aggregate_num(alpha_rows, "alpha"),
    }
    with open(OUT_DIR / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    print(f"  wrote {OUT_DIR / 'summary.json'}")

    print("\n" + "=" * 60)
    print("Done. All outputs in:", OUT_DIR)
    print("=" * 60)


def _aggregate(rows: list[dict], key: str) -> dict:
    groups: dict[str, list[dict]] = {}
    for r in rows:
        groups.setdefault(str(r[key]), []).append(r)
    out = {}
    for k, g in groups.items():
        out[k] = {
            "mean_cov": float(np.mean([r["marginal_cov"] for r in g])),
            "std_cov": float(np.std([r["marginal_cov"] for r in g])),
            "mean_width": float(np.mean([r["mean_width"] for r in g])),
            "std_width": float(np.std([r["mean_width"] for r in g])),
            "mean_ece": float(np.mean([r["ece"] for r in g])),
        }
    return out


def _aggregate_num(rows: list[dict], key: str) -> dict:
    return _aggregate(rows, key)


if __name__ == "__main__":
    main()
