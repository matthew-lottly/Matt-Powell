from __future__ import annotations

import numpy as np

from causal_lens.diagnostics import (
    compute_e_value,
    compute_e_value_ci,
    effective_sample_size,
    rosenbaum_bounds,
    standardized_mean_difference,
    summarize_overlap,
    variance_ratio,
)
from causal_lens.synthetic import generate_synthetic_observational_data


def test_standardized_mean_difference_returns_covariate_keys() -> None:
    dataset = generate_synthetic_observational_data(rows=200, seed=5)
    summary = standardized_mean_difference(
        dataset,
        treatment_col="treatment",
        covariates=["age", "severity", "baseline_score"],
    )
    assert set(summary) == {"age", "severity", "baseline_score"}


def test_overlap_summary_flags_overlap() -> None:
    propensity = np.array([0.2, 0.4, 0.6, 0.8], dtype=float)
    treatment = np.array([0, 1, 0, 1], dtype=int)
    summary = summarize_overlap(propensity, treatment)
    assert summary["overlap_ok"] is True
    assert summary["propensity_min"] == 0.2


def test_variance_ratio_returns_positive_values() -> None:
    dataset = generate_synthetic_observational_data(rows=300, seed=5)
    ratios = variance_ratio(dataset, "treatment", ["age", "severity", "baseline_score"])
    assert set(ratios) == {"age", "severity", "baseline_score"}
    assert all(v > 0.0 for v in ratios.values())


def test_variance_ratio_near_one_for_balanced_covariates() -> None:
    dataset = generate_synthetic_observational_data(rows=600, seed=42)
    ratios = variance_ratio(dataset, "treatment", ["baseline_score"])
    assert 0.5 < ratios["baseline_score"] < 2.0


def test_effective_sample_size_smaller_than_actual() -> None:
    weights = np.array([1.0, 1.0, 5.0, 0.2, 1.0, 1.0, 3.0, 0.5])
    treatment = np.array([1, 1, 1, 1, 0, 0, 0, 0])
    ess_t, ess_c = effective_sample_size(weights, treatment)
    assert ess_t > 0.0
    assert ess_t < 4.0
    assert ess_c > 0.0
    assert ess_c < 4.0


def test_effective_sample_size_equal_weights_equals_count() -> None:
    weights = np.ones(8)
    treatment = np.array([1, 1, 1, 1, 0, 0, 0, 0])
    ess_t, ess_c = effective_sample_size(weights, treatment)
    assert abs(ess_t - 4.0) < 1e-10
    assert abs(ess_c - 4.0) < 1e-10


def test_e_value_increases_with_effect_size() -> None:
    e1 = compute_e_value(1.0, 5.0)
    e2 = compute_e_value(3.0, 5.0)
    assert e1 > 1.0
    assert e2 > e1


def test_e_value_returns_one_for_zero_effect() -> None:
    assert compute_e_value(0.0, 5.0) == 1.0


def test_e_value_ci_returns_none_for_none_bound() -> None:
    assert compute_e_value_ci(None, 5.0) is None


def test_e_value_ci_returns_one_for_zero_bound() -> None:
    assert compute_e_value_ci(0.0, 5.0) == 1.0


def test_rosenbaum_bounds_significant_for_large_effect() -> None:
    rng = np.random.default_rng(42)
    diffs = rng.normal(5.0, 1.0, size=50)
    bounds = rosenbaum_bounds(diffs)
    assert bounds[0][0] == 1.0
    assert bounds[0][2] is True  # significant at Gamma=1


def test_rosenbaum_bounds_loses_significance_at_high_gamma() -> None:
    rng = np.random.default_rng(42)
    diffs = rng.normal(0.5, 1.0, size=30)
    bounds = rosenbaum_bounds(diffs, gamma_values=[1.0, 2.0, 5.0, 10.0])
    p_values = [b[1] for b in bounds]
    assert p_values[0] <= p_values[-1]  # p-value increases with Gamma


def test_rosenbaum_bounds_empty_returns_nonsignificant() -> None:
    bounds = rosenbaum_bounds(np.array([]))
    assert all(not b[2] for b in bounds)
