from __future__ import annotations

import math

import pandas as pd

from causal_lens.estimators import (
    CrossFittedDREstimator,
    DoublyRobustEstimator,
    FlexibleDoublyRobustEstimator,
    IPWEstimator,
    PropensityMatcher,
    RegressionAdjustmentEstimator,
    SLearner,
    TLearner,
    run_placebo_test,
)
from causal_lens.synthetic import generate_synthetic_observational_data


def _dataset() -> tuple[list[str], object]:
    dataset = generate_synthetic_observational_data(rows=900, seed=7, treatment_effect=2.25)
    confounders = ["age", "severity", "baseline_score"]
    return confounders, dataset


def test_regression_adjustment_recovers_positive_effect() -> None:
    confounders, dataset = _dataset()
    result = RegressionAdjustmentEstimator("treatment", "outcome", confounders).fit(dataset)
    assert result.effect > 1.5
    assert result.effect < 3.0
    assert result.diagnostics.overlap_ok is True


def test_matching_recovers_positive_effect() -> None:
    confounders, dataset = _dataset()
    result = PropensityMatcher("treatment", "outcome", confounders).fit(dataset)
    assert result.effect > 1.3
    assert result.effect < 3.2


def test_matching_improves_balance_on_confounded_synthetic_data() -> None:
    confounders, dataset = _dataset()
    result = PropensityMatcher("treatment", "outcome", confounders, bootstrap_repeats=20).fit(dataset)
    before = sum(abs(value) for value in result.diagnostics.balance_before.values()) / len(result.diagnostics.balance_before)
    after = sum(abs(value) for value in result.diagnostics.balance_after.values()) / len(result.diagnostics.balance_after)
    assert after < before


def test_ipw_recovers_positive_effect() -> None:
    confounders, dataset = _dataset()
    result = IPWEstimator("treatment", "outcome", confounders).fit(dataset)
    assert result.effect > 1.3
    assert result.effect < 3.2
    assert "age" in result.diagnostics.balance_after


def test_doubly_robust_recovers_positive_effect() -> None:
    confounders, dataset = _dataset()
    result = DoublyRobustEstimator("treatment", "outcome", confounders).fit(dataset)
    assert result.effect > 1.5
    assert result.effect < 3.0
    assert result.ci_low is not None
    assert result.ci_high is not None


def test_sensitivity_analysis_reports_positive_bias_threshold() -> None:
    confounders, dataset = _dataset()
    estimator = DoublyRobustEstimator("treatment", "outcome", confounders)
    summary = estimator.sensitivity_analysis(dataset, steps=5)
    assert summary.bias_to_zero_effect > 1.0
    assert summary.standardized_bias_to_zero_effect > 0.0
    assert len(summary.scenarios) == 5


def test_subgroup_effects_return_multiple_severity_groups() -> None:
    confounders, dataset = _dataset()
    dataset = dataset.copy()
    dataset["severity_group"] = pd.qcut(
        dataset["severity"],
        q=3,
        labels=["low", "mid", "high"],
        duplicates="drop",
    )
    estimator = DoublyRobustEstimator("treatment", "outcome", confounders, bootstrap_repeats=20)
    subgroup_results = estimator.subgroup_effects(
        dataset,
        "severity_group",
        min_rows=80,
        min_group_size=20,
    )
    assert len(subgroup_results) >= 3
    assert all(result.effect > 0.5 for result in subgroup_results)


def test_regression_adjustment_reports_analytic_se() -> None:
    confounders, dataset = _dataset()
    result = RegressionAdjustmentEstimator("treatment", "outcome", confounders).fit(dataset)
    assert result.se is not None
    assert result.se > 0.0
    assert result.p_value is not None
    assert 0.0 <= result.p_value <= 1.0


def test_ipw_reports_influence_function_se() -> None:
    confounders, dataset = _dataset()
    result = IPWEstimator("treatment", "outcome", confounders).fit(dataset)
    assert result.se is not None
    assert result.se > 0.0
    assert result.p_value is not None


def test_doubly_robust_reports_influence_function_se() -> None:
    confounders, dataset = _dataset()
    result = DoublyRobustEstimator("treatment", "outcome", confounders).fit(dataset)
    assert result.se is not None
    assert result.se > 0.0
    assert result.p_value is not None
    assert result.p_value < 0.05  # true effect = 2.25


def test_diagnostics_include_variance_ratios() -> None:
    confounders, dataset = _dataset()
    result = IPWEstimator("treatment", "outcome", confounders).fit(dataset)
    assert result.diagnostics.variance_ratios is not None
    assert set(result.diagnostics.variance_ratios) == set(confounders)
    assert all(v > 0.0 for v in result.diagnostics.variance_ratios.values())


def test_diagnostics_include_effective_sample_size() -> None:
    confounders, dataset = _dataset()
    result = IPWEstimator("treatment", "outcome", confounders).fit(dataset)
    assert result.diagnostics.ess_treated is not None
    assert result.diagnostics.ess_treated > 0.0
    assert result.diagnostics.ess_control is not None
    assert result.diagnostics.ess_control > 0.0


def test_sensitivity_includes_e_value() -> None:
    confounders, dataset = _dataset()
    estimator = DoublyRobustEstimator("treatment", "outcome", confounders)
    summary = estimator.sensitivity_analysis(dataset, steps=5)
    assert summary.e_value is not None
    assert summary.e_value > 1.0
    assert summary.e_value_ci is not None


def test_rosenbaum_sensitivity_returns_gamma_table() -> None:
    confounders, dataset = _dataset()
    matcher = PropensityMatcher("treatment", "outcome", confounders, caliper=None, bootstrap_repeats=10)
    bounds = matcher.rosenbaum_sensitivity(dataset)
    assert len(bounds) == 7  # default gamma values
    assert bounds[0].gamma == 1.0
    assert all(0.0 <= b.p_upper <= 1.0 for b in bounds)


def test_rosenbaum_significant_at_gamma_one_for_strong_effect() -> None:
    confounders, dataset = _dataset()
    matcher = PropensityMatcher("treatment", "outcome", confounders, caliper=None, bootstrap_repeats=10)
    bounds = matcher.rosenbaum_sensitivity(dataset)
    assert bounds[0].significant_at_05 is True  # Gamma=1 with true effect=2.25


def test_placebo_test_passes_on_unrelated_outcome() -> None:
    dataset = generate_synthetic_observational_data(rows=600, seed=42, treatment_effect=2.0)
    import numpy as np
    rng = np.random.default_rng(99)
    dataset["noise_outcome"] = rng.normal(0.0, 1.0, size=len(dataset))
    confounders = ["age", "severity", "baseline_score"]
    results = run_placebo_test(
        dataset,
        treatment_col="treatment",
        placebo_outcome="noise_outcome",
        confounders=confounders,
        bootstrap_repeats=20,
    )
    assert len(results) == 4
    passing = sum(1 for r in results if r.passes)
    assert passing >= 3  # most methods should pass on pure noise


def test_se_consistent_with_bootstrap_ci() -> None:
    """Analytic SE should be broadly consistent with bootstrap CI width."""
    confounders, dataset = _dataset()
    result = DoublyRobustEstimator("treatment", "outcome", confounders, bootstrap_repeats=40).fit(dataset)
    assert result.se is not None
    assert result.ci_low is not None and result.ci_high is not None
    bootstrap_width = result.ci_high - result.ci_low
    analytic_width = 2 * 1.96 * result.se
    ratio = analytic_width / bootstrap_width
    assert 0.3 < ratio < 3.0  # within a factor of 3


def test_ipw_se_consistent_with_bootstrap_ci() -> None:
    """IPW sandwich SE should be broadly consistent with bootstrap CI width."""
    confounders, dataset = _dataset()
    result = IPWEstimator("treatment", "outcome", confounders, bootstrap_repeats=40).fit(dataset)
    assert result.se is not None
    assert result.ci_low is not None and result.ci_high is not None
    bootstrap_width = result.ci_high - result.ci_low
    analytic_width = 2 * 1.96 * result.se
    ratio = analytic_width / bootstrap_width
    assert 0.3 < ratio < 5.0  # IPW sandwich SE can be conservative


def test_matching_reports_abadie_imbens_se() -> None:
    confounders, dataset = _dataset()
    result = PropensityMatcher("treatment", "outcome", confounders, bootstrap_repeats=20).fit(dataset)
    assert result.se is not None
    assert result.se > 0.0
    assert result.p_value is not None
    assert 0.0 <= result.p_value <= 1.0


def test_cross_fitted_dr_recovers_positive_effect() -> None:
    confounders, dataset = _dataset()
    result = CrossFittedDREstimator("treatment", "outcome", confounders, bootstrap_repeats=20).fit(dataset)
    assert result.effect > 1.0
    assert result.effect < 4.0
    assert result.se is not None
    assert result.se > 0.0
    assert result.p_value is not None


def test_cross_fitted_dr_se_is_valid() -> None:
    confounders, dataset = _dataset()
    result = CrossFittedDREstimator("treatment", "outcome", confounders, bootstrap_repeats=20).fit(dataset)
    assert result.se is not None
    assert result.ci_low is not None and result.ci_high is not None
    bootstrap_width = result.ci_high - result.ci_low
    analytic_width = 2 * 1.96 * result.se
    ratio = analytic_width / bootstrap_width
    assert 0.2 < ratio < 5.0


def test_flexible_dr_recovers_positive_effect() -> None:
    confounders, dataset = _dataset()
    result = FlexibleDoublyRobustEstimator("treatment", "outcome", confounders, bootstrap_repeats=20).fit(dataset)
    assert result.effect > 1.0
    assert result.effect < 4.0
    assert result.se is not None
    assert result.p_value is not None


def test_t_learner_recovers_positive_ate() -> None:
    confounders, dataset = _dataset()
    learner = TLearner("treatment", "outcome", confounders)
    ate = learner.ate(dataset)
    assert ate > 1.0
    assert ate < 4.0


def test_t_learner_cate_column_present() -> None:
    confounders, dataset = _dataset()
    learner = TLearner("treatment", "outcome", confounders)
    result = learner.estimate(dataset)
    assert "cate" in result.columns
    assert len(result) == len(dataset)


def test_t_learner_gbm_recovers_positive_ate() -> None:
    confounders, dataset = _dataset()
    learner = TLearner("treatment", "outcome", confounders, use_gbm=True)
    ate = learner.ate(dataset)
    assert ate > 0.5
    assert ate < 5.0


def test_s_learner_recovers_positive_ate() -> None:
    confounders, dataset = _dataset()
    learner = SLearner("treatment", "outcome", confounders)
    ate = learner.ate(dataset)
    assert ate > 1.0
    assert ate < 4.0


def test_s_learner_cate_column_present() -> None:
    confounders, dataset = _dataset()
    learner = SLearner("treatment", "outcome", confounders)
    result = learner.estimate(dataset)
    assert "cate" in result.columns
    assert len(result) == len(dataset)


def test_s_learner_gbm_recovers_positive_ate() -> None:
    confounders, dataset = _dataset()
    learner = SLearner("treatment", "outcome", confounders, use_gbm=True)
    ate = learner.ate(dataset)
    assert ate > 0.5
    assert ate < 5.0
