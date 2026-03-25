#!/usr/bin/env python
"""Demonstrate cross-design diagnostics on synthetic data.

Shows how CausalLens collects assumption evidence from observational,
DiD, IV, RD, and bunching designs into a unified comparison table.

Usage:
    python replications/replicate_cross_design.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from causal_lens import (
    BunchingEstimator,
    DoublyRobustEstimator,
    DifferenceInDifferences,
    RegressionDiscontinuity,
    TwoStageLeastSquares,
    compare_designs,
    diagnose_bunching,
    diagnose_did,
    diagnose_iv,
    diagnose_observational,
    diagnose_rd,
)

OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"


def _make_obs_data(rng: np.random.Generator, n: int = 500) -> pd.DataFrame:
    x1 = rng.normal(0, 1, n)
    x2 = rng.normal(0, 1, n)
    prop = 1 / (1 + np.exp(-(0.5 * x1 + 0.3 * x2)))
    t = rng.binomial(1, prop, n)
    y = 1 + 0.8 * x1 + 0.6 * x2 + 2.0 * t + rng.normal(0, 1, n)
    return pd.DataFrame({"x1": x1, "x2": x2, "treatment": t, "outcome": y})


def _make_did_data(rng: np.random.Generator, n_units: int = 100) -> pd.DataFrame:
    rows = []
    for i in range(n_units):
        treat = int(i >= n_units // 2)
        base = rng.normal(5, 1)
        for t in range(4):
            post = int(t >= 2)
            y = base + 0.5 * t + 2.0 * treat * post + rng.normal(0, 0.3)
            rows.append({"unit": i, "time": t, "treatment": treat, "post": post, "outcome": y})
    return pd.DataFrame(rows)


def _make_iv_data(rng: np.random.Generator, n: int = 500) -> pd.DataFrame:
    z = rng.binomial(1, 0.5, n).astype(float)
    u = rng.normal(0, 1, n)
    d = (0.6 * z + 0.4 * u + rng.normal(0, 0.3, n) > 0.5).astype(float)
    y = 1 + 2.0 * d + u + rng.normal(0, 0.5, n)
    return pd.DataFrame({"instrument": z, "treatment": d, "outcome": y})


def _make_rd_data(rng: np.random.Generator, n: int = 500) -> pd.DataFrame:
    x = rng.uniform(-1, 1, n)
    t = (x >= 0).astype(float)
    y = 0.5 * x + 2.0 * t + rng.normal(0, 0.3, n)
    return pd.DataFrame({"running": x, "treatment": t, "outcome": y})


def _make_bunching_data(rng: np.random.Generator, n: int = 2000) -> np.ndarray:
    base = rng.normal(100, 15, n)
    bunched = base.copy()
    near_kink = np.abs(base - 100) < 5
    bunched[near_kink] = 100 + rng.normal(0, 0.5, near_kink.sum())
    return bunched


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(42)

    print("=== Cross-Design Diagnostic Comparison ===\n")

    # --- Generate synthetic data for each design ---
    obs = _make_obs_data(rng)
    did_df = _make_did_data(rng)
    iv_df = _make_iv_data(rng)
    rd_df = _make_rd_data(rng)
    bunch_vals = _make_bunching_data(rng)

    # --- Run estimators to extract diagnostic values ---

    # Observational: DR estimator for overlap, balance, E-value
    dr = DoublyRobustEstimator("treatment", "outcome", ["x1", "x2"], bootstrap_repeats=20)
    dr_result = dr.fit(obs)
    sens = dr.sensitivity_analysis(obs)
    d_obs = diagnose_observational(
        overlap_ok=dr_result.diagnostics.overlap_ok,
        max_smd=max(abs(s) for s in dr_result.diagnostics.balance_before.values()),
        e_value=sens.e_value,
    )

    # DiD: pre-trends test
    did_est = DifferenceInDifferences("unit", "time", "treatment", "outcome", "post", cluster_col="unit")
    did_est.fit(did_df)
    pre_trends = did_est.parallel_trends_test(did_df, pre_periods=[0, 1])
    d_did = diagnose_did(parallel_trends_p=pre_trends["p_value"], n_pre_periods=pre_trends["n_periods"])

    # IV: first-stage F
    iv_est = TwoStageLeastSquares("treatment", "outcome", ["instrument"])
    iv_result = iv_est.fit(iv_df)
    d_iv = diagnose_iv(first_stage_f=iv_result.first_stage_f)

    # RD: McCrary test + effective sample
    rd_est = RegressionDiscontinuity("running", "outcome", cutoff=0.0)
    rd_result = rd_est.fit(rd_df)
    mccrary = rd_est.mccrary_test(rd_df)
    n_eff = int(sum(abs(rd_df["running"]) <= rd_result.bandwidth))
    d_rd = diagnose_rd(
        mccrary_p=mccrary.p_value,
        bandwidth=rd_result.bandwidth,
        n_effective=n_eff,
    )

    # Bunching: excess mass from BunchingEstimator on DataFrame
    bunch_df = pd.DataFrame({"running": bunch_vals})
    bunch_est = BunchingEstimator("running", threshold=100.0)
    bunch_result = bunch_est.fit(bunch_df)
    d_bunch = diagnose_bunching(
        excess_mass=bunch_result.excess_mass,
        excluded_range=(100.0 - bunch_result.excluded_window, 100.0 + bunch_result.excluded_window),
    )

    # --- Compare all designs ---
    all_diags = compare_designs(d_obs, d_did, d_iv, d_rd, d_bunch)

    rows = [d.to_dict() for d in all_diags]
    df = pd.DataFrame(rows)
    df.to_csv(OUTPUT_DIR / "cross_design_diagnostics.csv", index=False)

    for d in all_diags:
        status = "PASS" if d.passes else "FAIL"
        print(f"  [{d.design:14s}] {d.diagnostic_name:30s} = "
              f"{d.diagnostic_value:8.3f}  [{status}]")

    print(f"\nOutputs written to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
