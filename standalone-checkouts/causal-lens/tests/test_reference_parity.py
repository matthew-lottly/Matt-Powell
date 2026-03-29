from __future__ import annotations

import numpy as np
import statsmodels.api as sm
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from causal_lens.data import load_monitoring_intervention_sample
from causal_lens.estimators import (
    DoublyRobustEstimator,
    IPWEstimator,
    PropensityMatcher,
    RegressionAdjustmentEstimator,
)


def _reference_dataset() -> tuple[list[str], object]:
    frame = load_monitoring_intervention_sample()
    confounders = [
        "sensor_age_years",
        "maintenance_backlog_days",
        "baseline_alert_rate",
        "staffing_ratio",
    ]
    return confounders, frame


def _reference_propensity(frame, confounders: list[str]) -> np.ndarray:
    scaler = StandardScaler()
    x_matrix = scaler.fit_transform(frame[confounders])
    treatment = frame["treatment"]
    model = LogisticRegression(max_iter=5_000)
    model.fit(x_matrix, treatment)
    propensity = model.predict_proba(x_matrix)[:, 1]
    return np.clip(propensity, 1e-2, 1.0 - 1e-2)


def test_regression_adjustment_matches_direct_statsmodels_ols() -> None:
    confounders, frame = _reference_dataset()
    estimate = RegressionAdjustmentEstimator(
        "treatment",
        "outcome_alert_rate",
        confounders,
        bootstrap_repeats=10,
    ).fit(frame)

    design = sm.add_constant(frame[["treatment", *confounders]])
    outcome = frame["outcome_alert_rate"]
    reference_model = sm.OLS(outcome, design).fit()
    reference_effect = float(reference_model.params["treatment"])

    assert abs(estimate.effect - reference_effect) < 1e-12


def test_matching_matches_manual_nearest_propensity_pairing() -> None:
    confounders, frame = _reference_dataset()
    estimate = PropensityMatcher(
        "treatment",
        "outcome_alert_rate",
        confounders,
        caliper=None,
        bootstrap_repeats=10,
    ).fit(frame)

    propensity = _reference_propensity(frame, confounders)
    treatment = frame["treatment"].to_numpy(dtype=int)
    outcome = frame["outcome_alert_rate"].to_numpy(dtype=float)
    treated_idx = np.where(treatment == 1)[0]
    remaining_controls = list(np.where(treatment == 0)[0])

    deltas: list[float] = []
    for treated_position in sorted(treated_idx, key=lambda index: float(propensity[index])):
        control_distances = np.abs(propensity[remaining_controls] - propensity[treated_position])
        best_position = int(np.argmin(control_distances))
        best_control = remaining_controls.pop(best_position)
        deltas.append(float(outcome[treated_position] - outcome[best_control]))
    reference_effect = float(np.mean(deltas))

    assert abs(estimate.effect - reference_effect) < 1e-12


def test_ipw_matches_manual_weighted_mean_formula() -> None:
    confounders, frame = _reference_dataset()
    estimate = IPWEstimator(
        "treatment",
        "outcome_alert_rate",
        confounders,
        bootstrap_repeats=10,
    ).fit(frame)

    propensity = _reference_propensity(frame, confounders)
    treatment = frame["treatment"].to_numpy(dtype=int)
    outcome = frame["outcome_alert_rate"].to_numpy(dtype=float)
    p_treat = treatment.mean()
    weights = np.where(
        treatment == 1,
        p_treat / propensity,
        (1.0 - p_treat) / (1.0 - propensity),
    )
    weights = np.clip(weights, 0.0, 20.0)
    treated_mean = np.average(outcome[treatment == 1], weights=weights[treatment == 1])
    control_mean = np.average(outcome[treatment == 0], weights=weights[treatment == 0])
    reference_effect = float(treated_mean - control_mean)

    assert abs(estimate.effect - reference_effect) < 1e-12


def test_doubly_robust_matches_manual_augmented_ipw_formula() -> None:
    confounders, frame = _reference_dataset()
    estimate = DoublyRobustEstimator(
        "treatment",
        "outcome_alert_rate",
        confounders,
        bootstrap_repeats=10,
    ).fit(frame)

    propensity = _reference_propensity(frame, confounders)
    treatment = frame["treatment"].to_numpy(dtype=int)
    outcome = frame["outcome_alert_rate"].to_numpy(dtype=float)
    design = sm.add_constant(frame[confounders])

    treated_model = sm.OLS(outcome[treatment == 1], design[treatment == 1]).fit()
    control_model = sm.OLS(outcome[treatment == 0], design[treatment == 0]).fit()
    mu1 = treated_model.predict(design)
    mu0 = control_model.predict(design)
    w1 = np.clip(1.0 / propensity, 0.0, 20.0)
    w0 = np.clip(1.0 / (1.0 - propensity), 0.0, 20.0)
    pseudo = mu1 - mu0 + treatment * (outcome - mu1) * w1 - (1 - treatment) * (outcome - mu0) * w0
    reference_effect = float(np.mean(pseudo))

    assert abs(estimate.effect - reference_effect) < 1e-12
