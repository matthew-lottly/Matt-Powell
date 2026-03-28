"""Generate publication-ready figures from benchmark outputs.

Reads CSVs from outputs/ and produces vector-quality (SVG/PDF) figures
with consistent typography, colorblind-safe palettes, and proper sizing.

Usage:
    python scripts/plot_paper_figures.py
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

OUT_DIR = Path(__file__).resolve().parent.parent / "outputs"
FIG_DIR = OUT_DIR / "figures"
FIG_DIR.mkdir(exist_ok=True)


# ── Style setup ──────────────────────────────────────────────────────────────

def _setup_style():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.family": "serif",
        "font.size": 10,
        "axes.titlesize": 11,
        "axes.labelsize": 10,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 8,
        "figure.dpi": 300,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "axes.grid": True,
        "grid.alpha": 0.3,
    })
    return plt


# Colorblind-safe palette (Wong 2011)
COLORS = {
    "mondrian_cp":        "#0072B2",
    "chmp_mean":          "#E69F00",
    "chmp_median":        "#56B4E9",
    "chmp_median_floor":  "#009E73",
    "meta_learned":       "#D55E00",
    "chmp_learned_lambda":"#CC79A7",
    "chmp_attention":     "#F0E442",
    "ensemble_cp":        "#999999",
    "cqr_propagation":    "#000000",
}

METHOD_LABELS = {
    "mondrian_cp":        "Mondrian CP",
    "chmp_mean":          "CHMP (mean)",
    "chmp_median":        "CHMP (median)",
    "chmp_median_floor":  "CHMP (median+floor)",
    "meta_learned":       "Meta-Cal (ours)",
    "chmp_learned_lambda":"Learned-λ (ours)",
    "chmp_attention":     "Attention (ours)",
    "ensemble_cp":        "Ensemble CP",
    "cqr_propagation":    "CQR + Prop",
}

NODE_TYPES = ["power", "water", "telecom"]


def _read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path) as f:
        return list(csv.DictReader(f))


def _cast_rows(rows: list[dict]) -> list[dict]:
    """Cast numeric fields from strings."""
    for r in rows:
        for k, v in r.items():
            if k in ("method",):
                continue
            try:
                r[k] = float(v)
            except (ValueError, TypeError):
                pass
    return rows


# ── Figure 1: Full method comparison bar chart ──────────────────────────────

def fig_method_comparison():
    plt = _setup_style()

    rows = _cast_rows(_read_csv(OUT_DIR / "full_comparison.csv"))
    if not rows:
        rows = _cast_rows(_read_csv(OUT_DIR / "baseline_comparison.csv"))
    if not rows:
        print("  SKIP: no comparison data found")
        return

    methods = []
    seen = set()
    for r in rows:
        m = r["method"]
        if m not in seen:
            methods.append(m)
            seen.add(m)

    # Aggregate
    def agg(col, m):
        vals = [r[col] for r in rows if r["method"] == m]
        return np.mean(vals), np.std(vals)

    fig, axes = plt.subplots(1, 3, figsize=(12, 4))

    for ax, (col, label) in zip(axes, [
        ("marginal_cov", "Marginal Coverage"),
        ("mean_width", "Mean Interval Width"),
        ("ece", "ECE"),
    ]):
        means = [agg(col, m)[0] for m in methods]
        stds = [agg(col, m)[1] for m in methods]
        colors = [COLORS.get(m, "#888888") for m in methods]
        labels = [METHOD_LABELS.get(m, m) for m in methods]

        x = np.arange(len(methods))
        bars = ax.bar(x, means, yerr=stds, capsize=3, color=colors, alpha=0.85,
                      edgecolor="black", linewidth=0.5)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=7)
        ax.set_ylabel(label)
        if col == "marginal_cov":
            ax.axhline(0.9, color="red", ls="--", lw=0.8, label="target (0.90)")
            ax.legend(fontsize=7)

    fig.suptitle("Method Comparison (all seeds)", fontweight="bold", fontsize=12)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig1_method_comparison.pdf")
    fig.savefig(FIG_DIR / "fig1_method_comparison.svg")
    plt.close(fig)
    print("  wrote fig1_method_comparison.pdf/svg")


# ── Figure 2: Per-type conditional coverage ─────────────────────────────────

def fig_per_type_coverage():
    plt = _setup_style()

    rows = _cast_rows(_read_csv(OUT_DIR / "full_comparison.csv"))
    if not rows:
        rows = _cast_rows(_read_csv(OUT_DIR / "baseline_comparison.csv"))
    if not rows:
        print("  SKIP: no comparison data found")
        return

    methods = []
    seen = set()
    for r in rows:
        m = r["method"]
        if m not in seen:
            methods.append(m)
            seen.add(m)

    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    width = 0.8 / max(len(methods), 1)

    for ax, nt in zip(axes, NODE_TYPES):
        col = f"cov_{nt}"
        x = np.arange(len(methods))
        for i, m in enumerate(methods):
            vals = [r[col] for r in rows if r["method"] == m]
            mean_val = np.mean(vals)
            std_val = np.std(vals)
            ax.bar(i, mean_val, yerr=std_val, capsize=2,
                   color=COLORS.get(m, "#888"), alpha=0.85,
                   edgecolor="black", linewidth=0.5)
        ax.set_xticks(x)
        ax.set_xticklabels([METHOD_LABELS.get(m, m) for m in methods],
                           rotation=45, ha="right", fontsize=7)
        ax.axhline(0.9, color="red", ls="--", lw=0.8)
        ax.set_title(f"{nt.capitalize()}")
        ax.set_ylabel("Coverage")
        ax.set_ylim(0.7, 1.05)

    fig.suptitle("Per-Type Conditional Coverage", fontweight="bold", fontsize=12)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig2_per_type_coverage.pdf")
    fig.savefig(FIG_DIR / "fig2_per_type_coverage.svg")
    plt.close(fig)
    print("  wrote fig2_per_type_coverage.pdf/svg")


# ── Figure 3: Lambda sensitivity ────────────────────────────────────────────

def fig_lambda_sensitivity():
    plt = _setup_style()

    rows = _cast_rows(_read_csv(OUT_DIR / "lambda_sensitivity.csv"))
    if not rows:
        print("  SKIP: no lambda data found")
        return

    lambdas = sorted({r["lambda"] for r in rows})
    mean_cov = [np.mean([r["marginal_cov"] for r in rows if r["lambda"] == l]) for l in lambdas]
    std_cov = [np.std([r["marginal_cov"] for r in rows if r["lambda"] == l]) for l in lambdas]
    mean_w = [np.mean([r["mean_width"] for r in rows if r["lambda"] == l]) for l in lambdas]
    std_w = [np.std([r["mean_width"] for r in rows if r["lambda"] == l]) for l in lambdas]
    mean_ece = [np.mean([r["ece"] for r in rows if r["lambda"] == l]) for l in lambdas]
    std_ece = [np.std([r["ece"] for r in rows if r["lambda"] == l]) for l in lambdas]

    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(14, 4))

    ax1.errorbar(lambdas, mean_cov, yerr=std_cov, marker="o", capsize=3, color="#0072B2")
    ax1.axhline(0.9, color="red", ls="--", lw=0.8, label="target")
    ax1.set_xlabel("λ")
    ax1.set_ylabel("Marginal Coverage")
    ax1.legend()

    ax2.errorbar(lambdas, mean_w, yerr=std_w, marker="s", capsize=3, color="#E69F00")
    ax2.set_xlabel("λ")
    ax2.set_ylabel("Mean Width")

    ax3.errorbar(lambdas, mean_ece, yerr=std_ece, marker="^", capsize=3, color="#D55E00")
    ax3.set_xlabel("λ")
    ax3.set_ylabel("ECE")

    fig.suptitle("Propagation Weight (λ) Sensitivity", fontweight="bold")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig3_lambda_sensitivity.pdf")
    fig.savefig(FIG_DIR / "fig3_lambda_sensitivity.svg")
    plt.close(fig)
    print("  wrote fig3_lambda_sensitivity.pdf/svg")


# ── Figure 4: Alpha calibration plot ────────────────────────────────────────

def fig_alpha_calibration():
    plt = _setup_style()

    rows = _cast_rows(_read_csv(OUT_DIR / "alpha_sweep.csv"))
    if not rows:
        print("  SKIP: no alpha data found")
        return

    alphas = sorted({r["alpha"] for r in rows})
    targets = [1 - a for a in alphas]
    mean_cov = [np.mean([r["marginal_cov"] for r in rows if r["alpha"] == a]) for a in alphas]
    std_cov = [np.std([r["marginal_cov"] for r in rows if r["alpha"] == a]) for a in alphas]

    fig, ax = plt.subplots(figsize=(5, 5))
    ax.plot([0.7, 1.0], [0.7, 1.0], "k--", lw=0.8, label="ideal")
    ax.errorbar(targets, mean_cov, yerr=std_cov, fmt="o", capsize=3, color="#0072B2",
                label="CHMP", markersize=6)
    for t, mc in zip(targets, mean_cov):
        ax.annotate(f"α={1-t:.2f}", (float(t), float(mc)),
                    textcoords="offset points", xytext=(8, -8), fontsize=7)
    ax.set_xlabel("Target Coverage (1−α)")
    ax.set_ylabel("Empirical Coverage")
    ax.legend()
    ax.set_xlim(0.75, 1.0)
    ax.set_ylim(0.75, 1.0)
    ax.set_aspect("equal")

    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig4_alpha_calibration.pdf")
    fig.savefig(FIG_DIR / "fig4_alpha_calibration.svg")
    plt.close(fig)
    print("  wrote fig4_alpha_calibration.pdf/svg")


# ── Figure 5: Diagnostic plots from diagnostics.json ────────────────────────

def fig_diagnostics():
    plt = _setup_style()

    diag_path = OUT_DIR / "diagnostics.json"
    if not diag_path.exists():
        print("  SKIP: no diagnostics.json found")
        return
    with open(diag_path) as f:
        diag = json.load(f)

    # 5a: Width-decile conditional coverage
    wd = diag.get("width_decile", {})
    if wd:
        fig, ax = plt.subplots(figsize=(6, 4))
        centers = wd["decile_centers"]
        coverages = wd["coverage"]
        ax.bar(range(len(centers)), coverages, color="#0072B2", alpha=0.8, edgecolor="black", linewidth=0.5)
        ax.axhline(0.9, color="red", ls="--", lw=0.8, label="target (0.90)")
        ax.set_xticks(range(len(centers)))
        ax.set_xticklabels([f"{c:.2f}" for c in centers], rotation=45, fontsize=7)
        ax.set_xlabel("Width Decile Center")
        ax.set_ylabel("Coverage")
        ax.set_ylim(0.5, 1.1)
        ax.legend()
        ax.set_title("Conditional Coverage by Width Decile")
        fig.tight_layout()
        fig.savefig(FIG_DIR / "fig5a_width_decile_coverage.pdf")
        fig.savefig(FIG_DIR / "fig5a_width_decile_coverage.svg")
        plt.close(fig)
        print("  wrote fig5a_width_decile_coverage.pdf/svg")

    # 5b: Sigma vs hit-rate
    svh = diag.get("sigma_vs_hitrate", {})
    if svh:
        fig, axes = plt.subplots(1, min(len(svh), 3), figsize=(12, 4))
        if not hasattr(axes, "__iter__"):
            axes = [axes]
        for ax, nt in zip(axes, list(svh.keys())[:3]):
            data = svh[nt]
            if not data.get("sigma_bin_centers"):
                continue
            ax.bar(range(len(data["sigma_bin_centers"])), data["hitrate"],
                   color="#E69F00", alpha=0.8, edgecolor="black", linewidth=0.5)
            ax.axhline(0.9, color="red", ls="--", lw=0.8)
            ax.set_title(f"{nt.capitalize()}")
            ax.set_ylabel("Hit Rate")
            ax.set_xlabel("σ bin")
            ax.set_ylim(0.5, 1.1)
        fig.suptitle("σ vs Hit-Rate", fontweight="bold")
        fig.tight_layout()
        fig.savefig(FIG_DIR / "fig5b_sigma_hitrate.pdf")
        fig.savefig(FIG_DIR / "fig5b_sigma_hitrate.svg")
        plt.close(fig)
        print("  wrote fig5b_sigma_hitrate.pdf/svg")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("Generating publication figures…")
    fig_method_comparison()
    fig_per_type_coverage()
    fig_lambda_sensitivity()
    fig_alpha_calibration()
    fig_diagnostics()
    print(f"All figures saved to: {FIG_DIR}")


if __name__ == "__main__":
    main()
