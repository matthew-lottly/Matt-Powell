"""External comparison script.

Compares CausalLens API results against manual sklearn/statsmodels
implementations on the same public benchmarks. This script produces
a comparison table showing that the CausalLens abstractions give the
same results a researcher would get implementing each method by hand.

Optional: if DoWhy is available, also compares against DoWhy estimates.
"""
from __future__ import annotations

import importlib
from importlib.util import find_spec
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from causal_lens.data import (
    LALONDE_CONFOUNDERS,
    NHEFS_COMPLETE_CONFOUNDERS,
    load_lalonde_benchmark,
    load_nhefs_complete_benchmark,
)
from causal_lens.estimators import (
    DoublyRobustEstimator,
    IPWEstimator,
    RegressionAdjustmentEstimator,
)

WEIGHT_CAP = 20.0


def _manual_propensity(frame: pd.DataFrame, confounders: list[str]) -> np.ndarray:
    scaler = StandardScaler()
    x = scaler.fit_transform(frame[confounders])
    model = LogisticRegression(max_iter=5_000)
    model.fit(x, frame["treatment"])
    p = model.predict_proba(x)[:, 1]
    return np.clip(p, 1e-2, 1.0 - 1e-2)


def _manual_regression(frame: pd.DataFrame, confounders: list[str], outcome_col: str) -> float:
    design = sm.add_constant(frame[["treatment", *confounders]])
    model = sm.OLS(frame[outcome_col], design).fit()
    return float(model.params["treatment"])


def _manual_ipw_stabilized(frame: pd.DataFrame, confounders: list[str], outcome_col: str) -> float:
    p = _manual_propensity(frame, confounders)
    t = frame["treatment"].to_numpy(dtype=int)
    y = frame[outcome_col].to_numpy(dtype=float)
    p_treat = t.mean()
    w = np.where(t == 1, p_treat / p, (1.0 - p_treat) / (1.0 - p))
    w = np.clip(w, 0.0, WEIGHT_CAP)
    return float(np.average(y[t == 1], weights=w[t == 1]) - np.average(y[t == 0], weights=w[t == 0]))


def _manual_dr(frame: pd.DataFrame, confounders: list[str], outcome_col: str) -> float:
    p = _manual_propensity(frame, confounders)
    t = frame["treatment"].to_numpy(dtype=int)
    y = frame[outcome_col].to_numpy(dtype=float)
    x = sm.add_constant(frame[confounders])
    m1 = sm.OLS(y[t == 1], x[t == 1]).fit()
    m0 = sm.OLS(y[t == 0], x[t == 0]).fit()
    mu1, mu0 = m1.predict(x), m0.predict(x)
    w1 = np.clip(1.0 / p, 0.0, WEIGHT_CAP)
    w0 = np.clip(1.0 / (1.0 - p), 0.0, WEIGHT_CAP)
    pseudo = mu1 - mu0 + t * (y - mu1) * w1 - (1 - t) * (y - mu0) * w0
    return float(np.mean(pseudo))


def compare_on_dataset(
    name: str,
    frame: pd.DataFrame,
    confounders: list[str],
    outcome_col: str,
    propensity_trim_bounds: tuple[float, float] | None = None,
) -> list[dict]:
    rows: list[dict] = []
    for method_name, cls, manual_fn in [
        ("Regression", RegressionAdjustmentEstimator, _manual_regression),
        ("IPW", IPWEstimator, _manual_ipw_stabilized),
        ("DoublyRobust", DoublyRobustEstimator, _manual_dr),
    ]:
        cl_result = cls(
            "treatment", outcome_col, confounders,
            bootstrap_repeats=10,
            propensity_trim_bounds=propensity_trim_bounds,
        ).fit(frame)
        # Apply same trim to manual comparison
        eval_frame = frame
        if propensity_trim_bounds is not None:
            p = _manual_propensity(frame, confounders)
            lo, hi = propensity_trim_bounds
            mask = (p >= lo) & (p <= hi)
            eval_frame = frame.loc[mask].reset_index(drop=True)
        manual_result = manual_fn(eval_frame, confounders, outcome_col)
        rows.append({
            "dataset": name,
            "method": method_name,
            "causal_lens_effect": cl_result.effect,
            "manual_effect": manual_result,
            "abs_diff": abs(cl_result.effect - manual_result),
            "match": abs(cl_result.effect - manual_result) < 1e-10,
        })
    return rows


def build_external_comparison() -> pd.DataFrame:
    lalonde = load_lalonde_benchmark()
    nhefs = load_nhefs_complete_benchmark()

    all_rows: list[dict] = []
    # Use the same trim bounds as the CLI for Lalonde weighting estimators
    all_rows.extend(compare_on_dataset(
        "lalonde", lalonde, LALONDE_CONFOUNDERS, "outcome",
        propensity_trim_bounds=(0.03, 0.97),
    ))
    all_rows.extend(compare_on_dataset("nhefs", nhefs, NHEFS_COMPLETE_CONFOUNDERS, "outcome"))
    return pd.DataFrame(all_rows)


def export_external_comparison_artifacts(output_dir: Path) -> pd.DataFrame:
    tables_dir = output_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)
    comparison = build_external_comparison()
    comparison.to_csv(tables_dir / "external_comparison.csv", index=False)
    return comparison


def main() -> None:
    output_dir = Path(__file__).resolve().parents[2] / "outputs"
    comparison = export_external_comparison_artifacts(output_dir)

    print("=== CausalLens vs Manual Implementation ===")
    for _, row in comparison.iterrows():
        status = "MATCH" if row["match"] else "DIFF"
        print(
            f"  [{status}] {row['dataset']:10s} {row['method']:15s} "
            f"CausalLens={row['causal_lens_effect']:>12.4f}  "
            f"Manual={row['manual_effect']:>12.4f}  "
            f"diff={row['abs_diff']:.2e}"
        )

    all_match = comparison["match"].all()
    print(f"\nAll match: {all_match}")

    # Optionally compare against DoWhy if available
    try:
        if find_spec("dowhy") is None:
            raise ImportError
        print("\nDoWhy detected — running DoWhy comparison...")
        _compare_dowhy(load_lalonde_benchmark(), load_nhefs_complete_benchmark(), output_dir / "tables")
    except ImportError:
        print("\nDoWhy not installed — skipping DoWhy comparison.")
        print("Install with: pip install dowhy")


def _compare_dowhy(
    lalonde: pd.DataFrame,
    nhefs: pd.DataFrame,
    output_dir: Path,
) -> None:
    dowhy_module = importlib.import_module("dowhy")
    CausalModel: Any = dowhy_module.CausalModel

    rows: list[dict] = []
    for name, frame, confounders, outcome in [
        ("lalonde", lalonde, LALONDE_CONFOUNDERS, "outcome"),
        ("nhefs", nhefs, NHEFS_COMPLETE_CONFOUNDERS, "outcome"),
    ]:
        model = CausalModel(
            data=frame,
            treatment="treatment",
            outcome=outcome,
            common_causes=confounders,
        )
        identified = model.identify_effect(proceed_when_unidentifiable=True)
        for method_name, dowhy_method in [
            ("Regression", "backdoor.linear_regression"),
            ("IPW", "backdoor.propensity_score_weighting"),
        ]:
            estimate = model.estimate_effect(identified, method_name=dowhy_method)
            rows.append({
                "dataset": name,
                "method": method_name,
                "dowhy_effect": float(estimate.value),
            })

    dowhy_df = pd.DataFrame(rows)
    dowhy_df.to_csv(output_dir / "dowhy_comparison.csv", index=False)
    print(dowhy_df.to_string(index=False))


if __name__ == "__main__":
    main()
