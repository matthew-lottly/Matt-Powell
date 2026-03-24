from __future__ import annotations

import math

import numpy as np
import pandas as pd


def standardized_mean_difference(
    frame: pd.DataFrame,
    treatment_col: str,
    covariates: list[str],
    weights: np.ndarray | None = None,
) -> dict[str, float]:
    treatment_mask = frame[treatment_col].to_numpy(dtype=int) == 1
    control_mask = ~treatment_mask
    result: dict[str, float] = {}

    treated_weights = None if weights is None else weights[treatment_mask]
    control_weights = None if weights is None else weights[control_mask]

    for covariate in covariates:
        values = frame[covariate].to_numpy(dtype=float)
        treated = values[treatment_mask]
        control = values[control_mask]
        treated_mean = _weighted_mean(treated, treated_weights)
        control_mean = _weighted_mean(control, control_weights)
        treated_var = _weighted_variance(treated, treated_weights)
        control_var = _weighted_variance(control, control_weights)
        pooled = math.sqrt(max((treated_var + control_var) / 2.0, 1e-12))
        result[covariate] = float((treated_mean - control_mean) / pooled)
    return result


def summarize_overlap(propensity_scores: np.ndarray, treatment: np.ndarray) -> dict[str, float | bool]:
    treated_scores = propensity_scores[treatment == 1]
    control_scores = propensity_scores[treatment == 0]
    overlap_ok = bool(treated_scores.min() <= control_scores.max() and control_scores.min() <= treated_scores.max())
    return {
        "propensity_min": float(propensity_scores.min()),
        "propensity_max": float(propensity_scores.max()),
        "treated_mean_propensity": float(treated_scores.mean()),
        "control_mean_propensity": float(control_scores.mean()),
        "overlap_ok": overlap_ok,
    }


def _weighted_mean(values: np.ndarray, weights: np.ndarray | None) -> float:
    if weights is None:
        return float(values.mean())
    return float(np.average(values, weights=weights))


def _weighted_variance(values: np.ndarray, weights: np.ndarray | None) -> float:
    if weights is None:
        return float(values.var(ddof=1)) if len(values) > 1 else 0.0
    mean = _weighted_mean(values, weights)
    variance = np.average((values - mean) ** 2, weights=weights)
    return float(variance)
