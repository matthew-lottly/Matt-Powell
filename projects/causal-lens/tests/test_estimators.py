from __future__ import annotations

import pandas as pd

from causal_lens.estimators import (
    DoublyRobustEstimator,
    IPWEstimator,
    PropensityMatcher,
    RegressionAdjustmentEstimator,
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
