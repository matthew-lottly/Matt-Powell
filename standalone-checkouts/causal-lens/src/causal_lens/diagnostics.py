from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy.stats import norm, rankdata


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


def variance_ratio(
    frame: pd.DataFrame,
    treatment_col: str,
    covariates: list[str],
    weights: np.ndarray | None = None,
) -> dict[str, float]:
    """Variance ratio (treated / control) per covariate. Values near 1.0 indicate balance."""
    treatment_mask = frame[treatment_col].to_numpy(dtype=int) == 1
    control_mask = ~treatment_mask
    treated_weights = None if weights is None else weights[treatment_mask]
    control_weights = None if weights is None else weights[control_mask]
    result: dict[str, float] = {}
    for covariate in covariates:
        values = frame[covariate].to_numpy(dtype=float)
        treated_var = _weighted_variance(values[treatment_mask], treated_weights)
        control_var = _weighted_variance(values[control_mask], control_weights)
        denom = max(control_var, 1e-12)
        result[covariate] = float(treated_var / denom)
    return result


def effective_sample_size(weights: np.ndarray, treatment: np.ndarray) -> tuple[float, float]:
    """Kish effective sample size per treatment group. Returns (ess_treated, ess_control)."""
    ess: dict[str, float] = {}
    for label, mask in [("treated", treatment == 1), ("control", treatment == 0)]:
        w = weights[mask]
        total_w = float(w.sum())
        if total_w < 1e-12:
            ess[label] = 0.0
        else:
            ess[label] = float(total_w**2 / (w**2).sum())
    return ess["treated"], ess["control"]


def compute_e_value(effect: float, outcome_std: float) -> float:
    """E-value for unmeasured confounding (VanderWeele & Ding 2017).

    Minimum strength of association an unmeasured confounder would need with both
    the treatment and the outcome to fully explain away the observed effect.
    """
    if outcome_std < 1e-12 or abs(effect) < 1e-12:
        return 1.0
    d = abs(effect) / outcome_std
    rr = math.exp(0.91 * d)
    return float(rr + math.sqrt(rr * (rr - 1.0)))


def compute_e_value_ci(ci_bound_closest_to_null: float | None, outcome_std: float) -> float | None:
    """E-value for the CI bound closest to null. Returns 1.0 if CI includes null."""
    if ci_bound_closest_to_null is None:
        return None
    if abs(ci_bound_closest_to_null) < 1e-12:
        return 1.0
    return compute_e_value(ci_bound_closest_to_null, outcome_std)


def rosenbaum_bounds(
    paired_differences: np.ndarray,
    gamma_values: list[float] | None = None,
) -> list[tuple[float, float, bool]]:
    """Rosenbaum sensitivity analysis for matched pairs (Rosenbaum 2002).

    Tests how large hidden-bias Gamma must be to overturn significance.
    Returns list of (gamma, p_upper, significant_at_05) tuples.
    """
    if gamma_values is None:
        gamma_values = [1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0]

    n = len(paired_differences)
    if n == 0:
        return [(g, 1.0, False) for g in gamma_values]

    abs_diffs = np.abs(paired_differences)
    ranks = rankdata(abs_diffs, method="average")
    positive_mask = paired_differences > 0
    t_plus = float(ranks[positive_mask].sum())

    results: list[tuple[float, float, bool]] = []
    for gamma in gamma_values:
        p_plus = gamma / (1.0 + gamma)
        e_t = p_plus * ranks.sum()
        var_t = p_plus * (1.0 - p_plus) * (ranks**2).sum()
        if var_t < 1e-12:
            p_upper = 0.5
        else:
            z = (t_plus - e_t) / math.sqrt(var_t)
            p_upper = float(1.0 - norm.cdf(z))
        results.append((float(gamma), float(p_upper), p_upper < 0.05))
    return results
