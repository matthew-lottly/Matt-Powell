#!/usr/bin/env python
"""Replicate Hernán & Robins (2020) NHEFS smoking-cessation benchmark with CausalLens.

Expected weight-gain ATT: ~3.0 -- 3.5 kg (textbook reference values).
This script prints a table of estimator results and exports a CSV.

Usage:
    python replications/replicate_nhefs.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from causal_lens import (
    NHEFS_COMPLETE_CONFOUNDERS,
    DoublyRobustEstimator,
    IPWEstimator,
    RegressionAdjustmentEstimator,
    load_nhefs_complete_benchmark,
)

OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    data = load_nhefs_complete_benchmark()
    print(f"NHEFS benchmark: {len(data)} observations, "
          f"{data['treatment'].sum()} treated (quit smoking)\n")

    estimators = [
        ("Regression", RegressionAdjustmentEstimator(
            "treatment", "outcome", NHEFS_COMPLETE_CONFOUNDERS, bootstrap_repeats=200)),
        ("IPW", IPWEstimator(
            "treatment", "outcome", NHEFS_COMPLETE_CONFOUNDERS, bootstrap_repeats=200)),
        ("DR", DoublyRobustEstimator(
            "treatment", "outcome", NHEFS_COMPLETE_CONFOUNDERS, bootstrap_repeats=200)),
    ]

    rows = []
    for name, est in estimators:
        result = est.fit(data)
        rows.append({
            "Estimator": name,
            "ATT (kg)": round(result.effect, 2),
            "SE": round(result.se, 2) if result.se else None,
            "CI_low": round(result.ci_low, 2) if result.ci_low else None,
            "CI_high": round(result.ci_high, 2) if result.ci_high else None,
            "p_value": round(result.p_value, 4) if result.p_value else None,
        })
        print(f"  {name:12s}  ATT = {result.effect:.2f} kg  "
              f"SE = {result.se:.2f}" if result.se else "")

    df = pd.DataFrame(rows)
    df.to_csv(OUTPUT_DIR / "nhefs_replication.csv", index=False)
    print("\n" + df.to_string(index=False))

    # Sensitivity analysis on DR estimate
    print("\n--- OVB / E-value sensitivity (DR estimate) ---")
    dr_est = DoublyRobustEstimator(
        "treatment", "outcome", NHEFS_COMPLETE_CONFOUNDERS, bootstrap_repeats=50)
    sens = dr_est.sensitivity_analysis(data)
    print(f"  E-value:       {sens.e_value:.2f}")
    print(f"  E-value (CI):  {sens.e_value_ci:.2f}")
    print(f"  Bias to null:  {sens.bias_to_null:.2f}")

    print(f"\nOutputs written to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
