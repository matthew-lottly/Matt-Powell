"""Stability analysis: run estimators across seeds and bootstrap settings.

Produces a CSV summarizing how estimates and balance behave across
different random seeds, bootstrap repeat counts, and caliper settings.
"""
from __future__ import annotations

import itertools
from pathlib import Path

import numpy as np
import pandas as pd

from causal_lens.data import (
    LALONDE_CONFOUNDERS,
    NHEFS_COMPLETE_CONFOUNDERS,
    load_lalonde_benchmark,
    load_nhefs_complete_benchmark,
)
from causal_lens.estimators import (
    DoublyRobustEstimator,
    IPWEstimator,
    PropensityMatcher,
    RegressionAdjustmentEstimator,
)
from causal_lens.synthetic import generate_synthetic_observational_data


def _ci_width(ci_low: float | None, ci_high: float | None) -> float | None:
    if ci_low is None or ci_high is None:
        return None
    return ci_high - ci_low


def _run_estimators(
    dataset: pd.DataFrame,
    outcome_col: str,
    confounders: list[str],
    bootstrap_repeats: int,
    bootstrap_seed: int,
    caliper: float | None,
) -> list[dict]:
    rows: list[dict] = []
    for cls in [
        RegressionAdjustmentEstimator,
        IPWEstimator,
        DoublyRobustEstimator,
    ]:
        est = cls(
            "treatment",
            outcome_col,
            confounders,
            bootstrap_repeats=bootstrap_repeats,
            bootstrap_seed=bootstrap_seed,
        )
        result = est.fit(dataset)
        diag = result.diagnostics
        rows.append({
            "method": result.method,
            "effect": result.effect,
            "ci_low": result.ci_low,
            "ci_high": result.ci_high,
            "ci_width": _ci_width(result.ci_low, result.ci_high),
            "balance_after": sum(abs(v) for v in diag.balance_after.values()) / len(diag.balance_after),
        })
    matcher = PropensityMatcher(
        "treatment",
        outcome_col,
        confounders,
        caliper=caliper,
        bootstrap_repeats=bootstrap_repeats,
        bootstrap_seed=bootstrap_seed,
    )
    result = matcher.fit(dataset)
    diag = result.diagnostics
    rows.append({
        "method": result.method,
        "effect": result.effect,
        "ci_low": result.ci_low,
        "ci_high": result.ci_high,
        "ci_width": _ci_width(result.ci_low, result.ci_high),
        "balance_after": sum(abs(v) for v in diag.balance_after.values()) / len(diag.balance_after),
    })
    return rows


def run_stability_analysis() -> pd.DataFrame:
    return run_stability_analysis_with_settings(
        seeds=[42, 123, 7, 2024, 999, 314, 55, 808, 1776, 2025, 31415, 65536],
        bootstrap_counts=[50, 200, 500],
        calipers={"lalonde": [0.03, 0.05, 0.10], "nhefs": [0.01, 0.02, 0.05]},
    )


def run_stability_analysis_with_settings(
    *,
    seeds: list[int],
    bootstrap_counts: list[int],
    calipers: dict[str, list[float]],
) -> pd.DataFrame:

    lalonde = load_lalonde_benchmark()
    nhefs = load_nhefs_complete_benchmark()
    synthetic = generate_synthetic_observational_data()

    all_rows: list[dict] = []

    for seed, n_boot in itertools.product(seeds, bootstrap_counts):
        for cal in calipers["lalonde"]:
            for row in _run_estimators(lalonde, "outcome", LALONDE_CONFOUNDERS, n_boot, seed, cal):
                all_rows.append({
                    "dataset": "lalonde",
                    "seed": seed,
                    "bootstrap_repeats": n_boot,
                    "caliper": cal,
                    **row,
                })
        for cal in calipers["nhefs"]:
            for row in _run_estimators(nhefs, "outcome", NHEFS_COMPLETE_CONFOUNDERS, n_boot, seed, cal):
                all_rows.append({
                    "dataset": "nhefs",
                    "seed": seed,
                    "bootstrap_repeats": n_boot,
                    "caliper": cal,
                    **row,
                })
        for row in _run_estimators(synthetic, "outcome", ["age", "severity", "baseline_score"], n_boot, seed, 0.02):
            all_rows.append({
                "dataset": "synthetic",
                "seed": seed,
                "bootstrap_repeats": n_boot,
                "caliper": 0.02,
                **row,
            })

    return pd.DataFrame(all_rows)


def export_stability_artifacts(output_dir: Path, *, quick: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    tables_dir = output_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)
    if quick:
        raw = run_stability_analysis_with_settings(
            seeds=[42, 123, 7, 2024, 999],
            bootstrap_counts=[50],
            calipers={"lalonde": [0.05], "nhefs": [0.02]},
        )
    else:
        raw = run_stability_analysis()
    raw.to_csv(tables_dir / "stability_raw.csv", index=False)

    summary = summarize_stability(raw)
    summary.to_csv(tables_dir / "stability_summary.csv", index=False)
    return raw, summary


def summarize_stability(frame: pd.DataFrame) -> pd.DataFrame:
    grouped = frame.groupby(["dataset", "method"])
    summary = grouped.agg(
        mean_effect=("effect", "mean"),
        std_effect=("effect", "std"),
        min_effect=("effect", "min"),
        max_effect=("effect", "max"),
        mean_ci_width=("ci_width", "mean"),
        std_ci_width=("ci_width", "std"),
        mean_balance_after=("balance_after", "mean"),
        n_runs=("effect", "count"),
    ).reset_index()
    summary["cv_effect"] = (summary["std_effect"] / summary["mean_effect"].abs()).round(4)
    return summary


def main() -> None:
    output_dir = Path(__file__).resolve().parents[2] / "outputs"

    print("Running stability analysis across seeds and settings...")
    raw, summary = export_stability_artifacts(output_dir)

    print("\n=== Stability Summary ===")
    for _, row in summary.iterrows():
        cv_label = f"CV={row['cv_effect']:.3f}" if pd.notna(row["cv_effect"]) else "CV=N/A"
        print(
            f"  {row['dataset']:12s} {row['method']:35s} "
            f"effect={row['mean_effect']:>10.2f} ± {row['std_effect']:>8.2f}  "
            f"{cv_label}  (n={int(row['n_runs'])})"
        )
    print(f"\nRaw data: {output_dir / 'tables' / 'stability_raw.csv'}")
    print(f"Summary:  {output_dir / 'tables' / 'stability_summary.csv'}")


if __name__ == "__main__":
    main()
