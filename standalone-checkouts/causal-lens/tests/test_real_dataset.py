from __future__ import annotations

import numpy as np

from causal_lens.data import DataSpec, load_monitoring_intervention_sample, validate_observational_frame
from causal_lens.estimators import (
    DoublyRobustEstimator,
    IPWEstimator,
    PropensityMatcher,
    RegressionAdjustmentEstimator,
)


def _real_dataset() -> tuple[list[str], object]:
    dataset = load_monitoring_intervention_sample()
    confounders = [
        "sensor_age_years",
        "maintenance_backlog_days",
        "baseline_alert_rate",
        "staffing_ratio",
    ]
    return confounders, dataset


def test_real_dataset_loads_with_expected_columns() -> None:
    confounders, dataset = _real_dataset()
    validated = validate_observational_frame(
        dataset,
        DataSpec(
            treatment_col="treatment",
            outcome_col="outcome_alert_rate",
            confounders=confounders,
        ),
    )
    assert len(validated) == 48
    assert set(confounders).issubset(validated.columns)


def test_real_dataset_estimators_agree_on_effect_direction() -> None:
    confounders, dataset = _real_dataset()
    estimators = [
        RegressionAdjustmentEstimator("treatment", "outcome_alert_rate", confounders, bootstrap_repeats=20),
        PropensityMatcher(
            "treatment",
            "outcome_alert_rate",
            confounders,
            caliper=None,
            bootstrap_repeats=20,
        ),
        IPWEstimator("treatment", "outcome_alert_rate", confounders, bootstrap_repeats=20),
        DoublyRobustEstimator("treatment", "outcome_alert_rate", confounders, bootstrap_repeats=20),
    ]
    effects = [estimator.fit(dataset).effect for estimator in estimators]
    assert all(effect < 0.0 for effect in effects)
    assert max(effects) - min(effects) < 0.08


def test_real_dataset_overlap_is_no_longer_degenerate() -> None:
    confounders, dataset = _real_dataset()
    result = DoublyRobustEstimator("treatment", "outcome_alert_rate", confounders, bootstrap_repeats=20).fit(dataset)
    assert result.diagnostics.overlap_ok is True


def test_matching_improves_average_absolute_balance_on_real_dataset() -> None:
    confounders, dataset = _real_dataset()
    result = PropensityMatcher(
        "treatment",
        "outcome_alert_rate",
        confounders,
        caliper=None,
        bootstrap_repeats=20,
    ).fit(dataset)
    before = np.mean(np.abs(list(result.diagnostics.balance_before.values())))
    after = np.mean(np.abs(list(result.diagnostics.balance_after.values())))
    assert after < 0.2
    assert result.diagnostics.balance_after != result.diagnostics.balance_before


def test_ipw_improves_average_absolute_balance_on_real_dataset() -> None:
    confounders, dataset = _real_dataset()
    result = IPWEstimator("treatment", "outcome_alert_rate", confounders, bootstrap_repeats=20).fit(dataset)
    before = np.mean(np.abs(list(result.diagnostics.balance_before.values())))
    after = np.mean(np.abs(list(result.diagnostics.balance_after.values())))
    assert after < before


def test_real_dataset_sensitivity_reports_bias_threshold() -> None:
    confounders, dataset = _real_dataset()
    estimator = DoublyRobustEstimator("treatment", "outcome_alert_rate", confounders, bootstrap_repeats=20)
    summary = estimator.sensitivity_analysis(dataset, steps=4)
    assert summary.bias_to_zero_effect > 0.02
    assert len(summary.scenarios) == 4
