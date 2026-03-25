#!/usr/bin/env python
"""Replicate Dehejia & Wahba (1999) Lalonde benchmark results with CausalLens.

Expected range for the job-training ATT: $1,000 -- $2,500.
This script prints a table of estimator results and exports a CSV.

Usage:
    python replications/replicate_lalonde.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from causal_lens import (
    LALONDE_CONFOUNDERS,
    DoublyRobustEstimator,
    IPWEstimator,
    PropensityMatcher,
    RegressionAdjustmentEstimator,
    load_lalonde_benchmark,
    run_placebo_test,
)

OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    data = load_lalonde_benchmark()
    print(f"Lalonde benchmark: {len(data)} observations, "
          f"{data['treatment'].sum()} treated\n")

    estimators = [
        ("Regression", RegressionAdjustmentEstimator(
            "treatment", "outcome", LALONDE_CONFOUNDERS, bootstrap_repeats=200)),
        ("Matching", PropensityMatcher(
            "treatment", "outcome", LALONDE_CONFOUNDERS, caliper=0.05, bootstrap_repeats=200)),
        ("IPW", IPWEstimator(
            "treatment", "outcome", LALONDE_CONFOUNDERS, bootstrap_repeats=200,
            propensity_trim_bounds=(0.03, 0.97))),
        ("DR", DoublyRobustEstimator(
            "treatment", "outcome", LALONDE_CONFOUNDERS, bootstrap_repeats=200,
            propensity_trim_bounds=(0.03, 0.97))),
    ]

    rows = []
    for name, est in estimators:
        result = est.fit(data)
        rows.append({
            "Estimator": name,
            "ATT": round(result.effect, 1),
            "SE": round(result.se, 1) if result.se else None,
            "CI_low": round(result.ci_low, 1) if result.ci_low else None,
            "CI_high": round(result.ci_high, 1) if result.ci_high else None,
            "p_value": round(result.p_value, 4) if result.p_value else None,
            "Overlap_OK": result.diagnostics.overlap_ok,
        })
        print(f"  {name:12s}  ATT = ${result.effect:,.0f}  "
              f"SE = {result.se:,.0f}" if result.se else "")

    df = pd.DataFrame(rows)
    df.to_csv(OUTPUT_DIR / "lalonde_replication.csv", index=False)
    print("\n" + df.to_string(index=False))

    # Placebo / falsification test on pre-treatment earnings (re74)
    print("\n--- Placebo test on re74 ---")
    confounders_excl = [c for c in LALONDE_CONFOUNDERS if c != "re74"]
    placebo = run_placebo_test(
        data, treatment_col="treatment", placebo_outcome="re74",
        confounders=confounders_excl, bootstrap_repeats=50, matcher_caliper=0.05,
    )
    for r in placebo:
        status = "PASS" if r.passes else "FAIL"
        print(f"  {r.method:12s}  effect = {r.effect:,.0f}  [{status}]")

    print(f"\nOutputs written to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
