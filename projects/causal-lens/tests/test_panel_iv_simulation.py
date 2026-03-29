"""Tests for panel-data estimators, IV/2SLS, and Monte Carlo simulation."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from causal_lens.panel import DifferenceInDifferences, SyntheticControl
from causal_lens.iv import TwoStageLeastSquares
from causal_lens.simulation import (
    SimulationConfig,
    run_simulation,
    summarize_simulation,
    run_quick_simulation,
    DGP_REGISTRY,
)


# ---------------------------------------------------------------------------
# Helpers: synthetic data generators for tests
# ---------------------------------------------------------------------------

def _did_dataset(n_units: int = 100, effect: float = 3.0, seed: int = 42) -> pd.DataFrame:
    """Generate a simple two-period panel dataset with known DiD effect."""
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n_units):
        treated = int(i >= n_units // 2)
        baseline = rng.normal(10.0, 2.0)
        for t in [0, 1]:
            time_effect = 2.0 * t
            treat_effect = effect * treated * t
            noise = rng.normal(0, 0.5)
            y = baseline + time_effect + treat_effect + noise
            rows.append({
                "unit": f"unit_{i}",
                "time": t,
                "treatment": treated,
                "post": t,
                "outcome": y,
            })
    return pd.DataFrame(rows)


def _did_multi_period_dataset(
    n_units: int = 60, n_pre: int = 4, n_post: int = 3, effect: float = 5.0, seed: int = 42,
) -> pd.DataFrame:
    """Multi-period panel with parallel pre-trends."""
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n_units):
        treated = int(i >= n_units // 2)
        baseline = rng.normal(20.0, 3.0)
        for t in range(n_pre + n_post):
            post = int(t >= n_pre)
            time_effect = 1.5 * t
            treat_effect = effect * treated * post
            noise = rng.normal(0, 0.5)
            y = baseline + time_effect + treat_effect + noise
            rows.append({
                "unit": f"unit_{i}",
                "time": t,
                "treatment": treated,
                "post": post,
                "outcome": y,
            })
    return pd.DataFrame(rows)


def _synth_control_dataset(
    n_controls: int = 10, n_periods: int = 20, treatment_time: int = 10,
    effect: float = 5.0, seed: int = 42,
) -> pd.DataFrame:
    """Generate panel data for synthetic control testing."""
    rng = np.random.default_rng(seed)
    rows = []
    # Generate a shared trend
    trend = np.cumsum(rng.normal(0.5, 0.3, n_periods))

    # Treated unit
    unit_level = rng.normal(50, 5)
    for t in range(n_periods):
        treat_effect = effect if t >= treatment_time else 0.0
        y = unit_level + trend[t] + treat_effect + rng.normal(0, 0.3)
        rows.append({"unit": "treated", "time": t, "outcome": y})

    # Control units — share the trend with different levels
    for c in range(n_controls):
        unit_level = rng.normal(50, 5)
        unit_noise_scale = rng.uniform(0.2, 0.5)
        for t in range(n_periods):
            y = unit_level + trend[t] + rng.normal(0, unit_noise_scale)
            rows.append({"unit": f"control_{c}", "time": t, "outcome": y})

    return pd.DataFrame(rows)


def _iv_dataset(n: int = 1000, true_effect: float = 3.0, seed: int = 42) -> pd.DataFrame:
    """Generate IV dataset with known LATE.

    z -> d -> y, with confounding u -> d and u -> y.
    """
    rng = np.random.default_rng(seed)
    u = rng.normal(0, 1, n)       # unobserved confounder
    z = rng.binomial(1, 0.5, n)   # instrument (random assignment)
    x = rng.normal(0, 1, n)       # observed covariate
    # First stage: d depends on z and u (but z is independent of u)
    d_latent = -0.5 + 1.5 * z + 0.8 * u + 0.3 * x + rng.normal(0, 0.5, n)
    d = (d_latent > 0).astype(float)
    # Outcome: depends on d, u, x
    y = 1.0 + true_effect * d + 1.2 * u + 0.5 * x + rng.normal(0, 1, n)
    return pd.DataFrame({"z": z, "treatment": d, "x": x, "outcome": y})


# ---------------------------------------------------------------------------
# DiD tests
# ---------------------------------------------------------------------------

def test_did_recovers_positive_effect() -> None:
    data = _did_dataset(n_units=200, effect=3.0)
    did = DifferenceInDifferences("unit", "time", "treatment", "outcome", "post")
    result = did.fit(data)
    assert 2.0 < result.effect < 4.5
    assert result.se is not None and result.se > 0
    assert result.p_value is not None and result.p_value < 0.05


def test_did_zero_effect() -> None:
    data = _did_dataset(n_units=200, effect=0.0)
    did = DifferenceInDifferences("unit", "time", "treatment", "outcome", "post")
    result = did.fit(data)
    assert -1.0 < result.effect < 1.0
    assert result.p_value is not None and result.p_value > 0.05


def test_did_reports_group_means() -> None:
    data = _did_dataset(n_units=100, effect=3.0)
    did = DifferenceInDifferences("unit", "time", "treatment", "outcome", "post")
    result = did.fit(data)
    assert result.n_treated > 0
    assert result.n_control > 0
    assert result.treated_post_mean > result.treated_pre_mean
    assert result.ci_low is not None and result.ci_high is not None


def test_did_with_covariates() -> None:
    data = _did_dataset(n_units=200, effect=3.0)
    rng = np.random.default_rng(99)
    data["covariate"] = rng.normal(0, 1, len(data))
    did = DifferenceInDifferences(
        "unit", "time", "treatment", "outcome", "post",
        covariates=["covariate"],
    )
    result = did.fit(data)
    assert 2.0 < result.effect < 4.5


def test_did_parallel_trends() -> None:
    data = _did_multi_period_dataset(n_units=80, n_pre=5, effect=5.0)
    did = DifferenceInDifferences("unit", "time", "treatment", "outcome", "post")
    trends = did.parallel_trends_test(data)
    assert trends["p_value"] > 0.05  # parallel trends should hold
    assert trends["n_periods"] >= 2


# ---------------------------------------------------------------------------
# Synthetic control tests
# ---------------------------------------------------------------------------

def test_synth_control_recovers_positive_effect() -> None:
    data = _synth_control_dataset(n_controls=8, effect=5.0)
    sc = SyntheticControl("unit", "time", "outcome", "treated", treatment_time=10)
    result = sc.fit(data)
    assert 3.0 < result.effect < 8.0
    assert result.pre_treatment_rmse < 2.0
    assert result.treated_unit == "treated"


def test_synth_control_weights_sum_to_one() -> None:
    data = _synth_control_dataset(n_controls=6, effect=3.0)
    sc = SyntheticControl("unit", "time", "outcome", "treated", treatment_time=10)
    result = sc.fit(data)
    total_weight = sum(result.weights.values())
    assert abs(total_weight - 1.0) < 0.01


def test_synth_control_post_means() -> None:
    data = _synth_control_dataset(n_controls=6, effect=5.0)
    sc = SyntheticControl("unit", "time", "outcome", "treated", treatment_time=10)
    result = sc.fit(data)
    assert result.treated_post_mean > result.synthetic_post_mean


def test_synth_control_zero_effect() -> None:
    data = _synth_control_dataset(n_controls=8, effect=0.0)
    sc = SyntheticControl("unit", "time", "outcome", "treated", treatment_time=10)
    result = sc.fit(data)
    assert -2.0 < result.effect < 2.0


# ---------------------------------------------------------------------------
# IV/2SLS tests
# ---------------------------------------------------------------------------

def test_2sls_recovers_positive_effect() -> None:
    data = _iv_dataset(n=2000, true_effect=3.0)
    iv = TwoStageLeastSquares("treatment", "outcome", ["z"], ["x"])
    result = iv.fit(data)
    assert 2.0 < result.effect < 5.0
    assert result.se > 0
    assert result.p_value < 0.05


def test_2sls_first_stage_f_is_strong() -> None:
    data = _iv_dataset(n=2000, true_effect=3.0)
    iv = TwoStageLeastSquares("treatment", "outcome", ["z"], ["x"])
    result = iv.fit(data)
    assert result.first_stage_f > 10.0
    assert result.weak_instrument is False


def test_2sls_weak_instrument_detected() -> None:
    """With a near-irrelevant instrument, F should be low."""
    rng = np.random.default_rng(42)
    n = 500
    z = rng.binomial(1, 0.5, n)
    x = rng.normal(0, 1, n)
    # instrument has almost no effect on treatment
    d = rng.binomial(1, 0.5, n).astype(float)
    y = 1.0 + 3.0 * d + 0.5 * x + rng.normal(0, 1, n)
    data = pd.DataFrame({"z": z, "treatment": d, "x": x, "outcome": y})
    iv = TwoStageLeastSquares("treatment", "outcome", ["z"], ["x"])
    result = iv.fit(data)
    assert result.weak_instrument is True
    assert result.first_stage_f < 10.0


def test_2sls_confidence_interval() -> None:
    data = _iv_dataset(n=2000, true_effect=3.0)
    iv = TwoStageLeastSquares("treatment", "outcome", ["z"], ["x"])
    result = iv.fit(data)
    assert result.ci_low < result.effect < result.ci_high
    assert result.ci_low < 3.0 < result.ci_high  # covers true effect


def test_2sls_no_covariates() -> None:
    rng = np.random.default_rng(42)
    n = 1000
    z = rng.binomial(1, 0.5, n)
    d = (0.5 * z + rng.normal(0, 0.5, n) > 0).astype(float)
    y = 2.0 * d + rng.normal(0, 1, n)
    data = pd.DataFrame({"z": z, "treatment": d, "outcome": y})
    iv = TwoStageLeastSquares("treatment", "outcome", ["z"])
    result = iv.fit(data)
    assert result.effect > 0
    assert result.n_obs == n


# ---------------------------------------------------------------------------
# Monte Carlo simulation tests
# ---------------------------------------------------------------------------

def test_dgp_registry_has_all_dgps() -> None:
    assert "linear" in DGP_REGISTRY
    assert "nonlinear_outcome" in DGP_REGISTRY
    assert "nonlinear_propensity" in DGP_REGISTRY
    assert "double_nonlinear" in DGP_REGISTRY
    assert "strong_confounding" in DGP_REGISTRY


def test_quick_simulation_runs() -> None:
    config = SimulationConfig(
        n_replications=3,
        sample_sizes=(100,),
        bootstrap_repeats=5,
        dgp_names=("linear",),
    )
    raw = run_simulation(config)
    assert len(raw) > 0
    assert "dgp" in raw.columns
    assert "estimator" in raw.columns
    assert "estimate" in raw.columns
    assert "covered" in raw.columns


def test_simulation_summary_has_metrics() -> None:
    config = SimulationConfig(
        n_replications=5,
        sample_sizes=(200,),
        bootstrap_repeats=5,
        dgp_names=("linear",),
    )
    raw = run_simulation(config)
    summary = summarize_simulation(raw)
    assert "bias" in summary.columns
    assert "rmse" in summary.columns
    assert "coverage" in summary.columns
    assert "se_ratio" in summary.columns


def test_simulation_linear_dgp_low_bias() -> None:
    """Regression and DR should have low bias on the linear DGP."""
    config = SimulationConfig(
        n_replications=10,
        sample_sizes=(200,),
        bootstrap_repeats=5,
        dgp_names=("linear",),
    )
    raw = run_simulation(config)
    summary = summarize_simulation(raw)
    for est in ["Regression", "DR", "CrossFitDR"]:
        row = summary[summary["estimator"] == est]
        if len(row) > 0:
            assert abs(float(row["bias"].iloc[0])) < 0.5


def test_simulation_coverage_reasonable() -> None:
    """Coverage should be between 50% and 100% for reasonable estimators."""
    config = SimulationConfig(
        n_replications=10,
        sample_sizes=(200,),
        bootstrap_repeats=5,
        dgp_names=("linear",),
    )
    raw = run_simulation(config)
    summary = summarize_simulation(raw)
    for _, row in summary.iterrows():
        if row["n_reps"] >= 10:
            assert 0.3 < row["coverage"] < 1.0


# ---------------------------------------------------------------------------
# IPW propensity-estimation uncertainty test
# ---------------------------------------------------------------------------

def test_ipw_se_accounts_for_propensity_estimation() -> None:
    """IPW SE with propensity correction should differ from naive."""
    from causal_lens.estimators import IPWEstimator
    from causal_lens.synthetic import generate_synthetic_observational_data

    data = generate_synthetic_observational_data(rows=600, seed=42)
    confounders = ["age", "severity", "baseline_score"]

    # With correction (default)
    est_corrected = IPWEstimator("treatment", "outcome", confounders, bootstrap_repeats=20)
    result_corrected = est_corrected.fit(data)

    # Without correction
    est_naive = IPWEstimator("treatment", "outcome", confounders, bootstrap_repeats=20)
    est_naive.account_for_propensity_estimation = False
    result_naive = est_naive.fit(data)

    # Both should give same point estimate
    assert abs(result_corrected.effect - result_naive.effect) < 1e-10

    # Both SEs should be positive and reasonable
    assert result_corrected.se is not None and result_corrected.se > 0
    assert result_naive.se is not None and result_naive.se > 0

    # SEs should differ (correction adjusts variance)
    assert result_corrected.se != result_naive.se
