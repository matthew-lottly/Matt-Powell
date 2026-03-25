from __future__ import annotations

import numpy as np
import pandas as pd

from causal_lens import (
    BunchingElasticity,
    BunchingEstimate,
    BunchingEstimator,
    McCraryResult,
    RDEstimate,
    RegressionDiscontinuity,
)


# ---------------------------------------------------------------------------
# Synthetic Data Generators
# ---------------------------------------------------------------------------

def _sharp_rdd_dataset(seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n = 2_000
    running = rng.uniform(-1.0, 1.0, n)
    outcome = 1.5 + 2.75 * (running >= 0.0) + 1.5 * running + rng.normal(0.0, 0.45, n)
    covariate = 0.3 * running + rng.normal(0.0, 0.2, n)
    return pd.DataFrame({
        "running": running,
        "outcome": outcome,
        "covariate": covariate,
    })


def _fuzzy_rdd_dataset(seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n = 3_000
    running = rng.uniform(-1.0, 1.0, n)
    treat_prob = np.clip(0.2 + 0.5 * (running >= 0.0) + 0.1 * running, 0.05, 0.95)
    treatment = rng.binomial(1, treat_prob, n).astype(float)
    outcome = 1.0 + 3.0 * treatment + 1.2 * running + rng.normal(0.0, 0.6, n)
    return pd.DataFrame({
        "running": running,
        "outcome": outcome,
        "treatment": treatment,
    })


def _bunched_dataset(seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n = 5_000
    score = rng.normal(0.0, 1.0, n)
    moved = (score > -0.05) & (score < 0.15) & (rng.random(n) < 0.6)
    score[moved] = rng.uniform(-0.10, -0.01, moved.sum())
    return pd.DataFrame({"score": score})


def _smooth_dataset(seed: int = 8) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame({"score": rng.normal(0.0, 1.0, 5_000)})


def _kink_bunching_dataset(seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n = 50_000
    zstar = 50_000.0
    elasticity = 0.25
    t1, t2 = 0.15, 0.25
    ntr = (t2 - t1) / (1.0 - t1)
    dz = elasticity * zstar * ntr

    z0 = rng.uniform(30_000, 70_000, n)
    z_obs = z0.copy()
    in_region = (z0 > zstar) & (z0 <= zstar + dz)
    z_obs[in_region] = zstar + rng.uniform(-25, 25, int(in_region.sum()))
    z_obs += rng.normal(0, 200, n)
    return pd.DataFrame({"income": z_obs})


# ---------------------------------------------------------------------------
# Sharp RD Tests
# ---------------------------------------------------------------------------

def test_rdd_recovers_positive_cutoff_effect() -> None:
    data = _sharp_rdd_dataset()
    result = RegressionDiscontinuity(
        "running",
        "outcome",
        cutoff=0.0,
        bandwidth=0.40,
        kernel="triangular",
    ).fit(data)
    assert isinstance(result, RDEstimate)
    assert 2.3 < result.effect < 3.2
    assert result.se is not None and result.se > 0.0
    assert result.p_value is not None and result.p_value < 0.01


def test_rdd_supports_covariates_and_quadratic_fit() -> None:
    data = _sharp_rdd_dataset()
    result = RegressionDiscontinuity(
        "running",
        "outcome",
        cutoff=0.0,
        bandwidth=0.45,
        degree=2,
        covariates=["covariate"],
    ).fit(data)
    assert 2.2 < result.effect < 3.3
    assert result.n_left > 50
    assert result.n_right > 50
    assert result.density_ratio is not None


def test_rdd_automatic_bandwidth_is_positive() -> None:
    data = _sharp_rdd_dataset()
    result = RegressionDiscontinuity("running", "outcome").fit(data)
    assert result.bandwidth > 0.0
    assert result.ci_low is not None
    assert result.ci_high is not None


# ---------------------------------------------------------------------------
# Robust Bias-Corrected RD Tests
# ---------------------------------------------------------------------------

def test_rdd_bias_corrected_effect_is_populated() -> None:
    data = _sharp_rdd_dataset()
    result = RegressionDiscontinuity(
        "running", "outcome", cutoff=0.0, bandwidth=0.40,
    ).fit(data)
    assert result.bias_corrected_effect is not None
    assert result.robust_se is not None and result.robust_se > 0.0
    assert result.robust_p_value is not None
    assert result.robust_ci_low is not None
    assert result.robust_ci_high is not None
    assert result.pilot_bandwidth is not None and result.pilot_bandwidth > result.bandwidth
    # Bias-corrected estimate should be in a reasonable range
    assert 1.5 < result.bias_corrected_effect < 4.0


def test_rdd_robust_se_is_at_least_conventional_se() -> None:
    data = _sharp_rdd_dataset()
    result = RegressionDiscontinuity(
        "running", "outcome", cutoff=0.0, bandwidth=0.40,
    ).fit(data)
    # Robust SE accounts for bias estimation variance, so should be >= conventional
    assert result.robust_se is not None and result.se is not None
    assert result.robust_se >= result.se * 0.95  # allow small numerical tolerance


def test_rdd_robust_ci_covers_true_effect() -> None:
    data = _sharp_rdd_dataset()
    result = RegressionDiscontinuity(
        "running", "outcome", cutoff=0.0, bandwidth=0.40,
    ).fit(data)
    # True effect is 2.75; robust CI should cover it
    assert result.robust_ci_low is not None and result.robust_ci_high is not None
    assert result.robust_ci_low < 2.75 < result.robust_ci_high


# ---------------------------------------------------------------------------
# Fuzzy RD Tests
# ---------------------------------------------------------------------------

def test_fuzzy_rdd_recovers_late() -> None:
    data = _fuzzy_rdd_dataset()
    result = RegressionDiscontinuity(
        "running", "outcome",
        cutoff=0.0, bandwidth=0.40,
        treatment_col="treatment",
    ).fit(data)
    assert result.design == "fuzzy"
    # True LATE is 3.0
    assert 1.5 < result.effect < 5.0
    assert result.first_stage_effect is not None and result.first_stage_effect > 0.2
    assert result.first_stage_f is not None and result.first_stage_f > 4.0
    assert result.reduced_form_effect is not None


def test_fuzzy_rdd_first_stage_is_strong() -> None:
    data = _fuzzy_rdd_dataset()
    result = RegressionDiscontinuity(
        "running", "outcome",
        cutoff=0.0, bandwidth=0.40,
        treatment_col="treatment",
    ).fit(data)
    assert result.first_stage_se is not None and result.first_stage_se > 0.0
    # First stage F should indicate instrument relevance
    assert result.first_stage_f is not None and result.first_stage_f > 10.0


# ---------------------------------------------------------------------------
# McCrary Density Test
# ---------------------------------------------------------------------------

def test_mccrary_no_manipulation_for_uniform_running() -> None:
    data = _sharp_rdd_dataset()
    rd = RegressionDiscontinuity("running", "outcome", cutoff=0.0)
    mc = rd.mccrary_test(data)
    assert isinstance(mc, McCraryResult)
    # Uniform running variable should not show manipulation
    assert mc.p_value > 0.01
    assert mc.manipulation_detected is False
    assert mc.n_left > 0 and mc.n_right > 0


def test_mccrary_detects_manipulation_when_present() -> None:
    rng = np.random.default_rng(99)
    n = 5_000
    # Create data with clear manipulation: pile-up just right of cutoff
    running = rng.normal(0.0, 1.0, n)
    manipulated = (running > -0.2) & (running < 0.0) & (rng.random(n) < 0.7)
    running[manipulated] = rng.uniform(0.0, 0.1, manipulated.sum())
    outcome = 1.0 + running + rng.normal(0.0, 0.5, n)
    data = pd.DataFrame({"running": running, "outcome": outcome})

    rd = RegressionDiscontinuity("running", "outcome", cutoff=0.0)
    mc = rd.mccrary_test(data, test_bandwidth=0.5)
    # Should detect the manipulation
    assert mc.density_ratio > 1.0
    assert mc.z_statistic > 0.0


# ---------------------------------------------------------------------------
# Descriptive Bunching Tests
# ---------------------------------------------------------------------------

def test_bunching_detects_excess_mass_near_threshold() -> None:
    data = _bunched_dataset()
    result = BunchingEstimator(
        "score",
        threshold=0.0,
        side="left",
        bin_width=0.05,
        analysis_window=1.0,
        excluded_window=0.10,
        polynomial_degree=4,
        bootstrap_repeats=20,
    ).fit(data)
    assert isinstance(result, BunchingEstimate)
    assert result.excess_mass > 50.0
    assert result.excess_mass_ratio > 0.3
    assert result.counterfactual_mass > 0.0


def test_bunching_is_small_for_smooth_distribution() -> None:
    data = _smooth_dataset()
    result = BunchingEstimator(
        "score",
        threshold=0.0,
        side="left",
        bin_width=0.05,
        analysis_window=1.0,
        excluded_window=0.10,
        polynomial_degree=4,
        bootstrap_repeats=10,
    ).fit(data)
    assert abs(result.excess_mass_ratio) < 0.5


# ---------------------------------------------------------------------------
# Structural Bunching Elasticity Tests
# ---------------------------------------------------------------------------

def test_bunching_elasticity_recovers_positive_value() -> None:
    data = _kink_bunching_dataset()
    est = BunchingEstimator(
        "income",
        threshold=50_000.0,
        side="left",
        bin_width=500,
        analysis_window=15_000,
        excluded_window=2_000,
        polynomial_degree=5,
        bootstrap_repeats=20,
    )
    result = est.elasticity(data, tax_rate_below=0.15, tax_rate_above=0.25)
    assert isinstance(result, BunchingElasticity)
    assert result.elasticity > 0.05
    assert result.excess_mass > 0.0
    assert result.normalized_bunching > 0.0
    assert result.counterfactual_at_kink > 0.0
    assert result.implied_dz_star > 0.0
    assert result.kink_point == 50_000.0
    assert result.net_of_tax_change > 0.0


def test_bunching_elasticity_bootstrap_ci() -> None:
    data = _kink_bunching_dataset()
    est = BunchingEstimator(
        "income",
        threshold=50_000.0,
        side="left",
        bin_width=500,
        analysis_window=15_000,
        excluded_window=2_000,
        polynomial_degree=5,
        bootstrap_repeats=50,
    )
    result = est.elasticity(data, tax_rate_below=0.15, tax_rate_above=0.25)
    assert result.ci_low is not None and result.ci_high is not None
    assert result.ci_low < result.elasticity < result.ci_high


# ---------------------------------------------------------------------------
# Cross-Design RDD Simulation Tests
# ---------------------------------------------------------------------------

def test_rdd_simulation_runs_and_summarizes() -> None:
    from causal_lens.simulation import run_rdd_simulation, summarize_simulation
    raw = run_rdd_simulation(n_replications=5, sample_sizes=(500,), true_effect=2.75, seed=42)
    assert len(raw) > 0
    assert "RD_conventional" in raw["estimator"].values
    assert "RD_bias_corrected" in raw["estimator"].values
    summary = summarize_simulation(raw)
    assert "bias" in summary.columns
    assert "rmse" in summary.columns