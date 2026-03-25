from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy.stats import norm, rankdata, t as t_dist

from causal_lens.results import OVBBound, OVBSummary


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


# ---------------------------------------------------------------------------
# Omitted-variable bias: Cinelli & Hazlett (2020)
# ---------------------------------------------------------------------------

def ovb_bounds(
    frame: pd.DataFrame,
    outcome_col: str,
    treatment_col: str,
    covariates: list[str],
    benchmark_covariates: list[str] | None = None,
    kd: float = 1.0,
    ky: float = 1.0,
    alpha: float = 0.05,
) -> OVBSummary:
    """Omitted-variable bias analysis following Cinelli & Hazlett (2020).

    Computes the robustness value (RV) and, optionally, contraction bounds
    calibrated against observed covariates. This tells the user how strong
    an omitted confounder would need to be (in partial-R² terms) to explain
    away the treatment effect.

    Parameters
    ----------
    frame : pd.DataFrame
        Data with outcome, treatment, and covariates.
    outcome_col : str
        Name of the outcome column.
    treatment_col : str
        Name of the treatment column.
    covariates : list[str]
        Covariates included in the regression.
    benchmark_covariates : list[str] | None
        Covariates to use as benchmarks for bounding. If None, each
        covariate in *covariates* is used as its own benchmark.
    kd : float
        Multiplier on the treatment-confounder partial R² benchmark.
    ky : float
        Multiplier on the outcome-confounder partial R² benchmark.
    alpha : float
        Significance level for RV_alpha.

    Returns
    -------
    OVBSummary
    """
    import statsmodels.api as sm

    y = frame[outcome_col].to_numpy(dtype=float)
    d = frame[treatment_col].to_numpy(dtype=float)
    x = frame[covariates].to_numpy(dtype=float)

    # Full regression: Y ~ D + X
    full_x = np.column_stack([d, x])
    full_x_with_const = sm.add_constant(full_x)
    full_model = sm.OLS(y, full_x_with_const).fit()
    # Treatment coefficient is the second column (after constant)
    treatment_effect = float(full_model.params[1])
    treatment_se = float(full_model.bse[1])
    n = len(y)
    dof = int(full_model.df_resid)

    # R² from full model
    r2_full = float(full_model.rsquared)

    # Restricted model: Y ~ X (no treatment)
    x_with_const = sm.add_constant(x)
    restricted_model = sm.OLS(y, x_with_const).fit()
    r2_restricted = float(restricted_model.rsquared)

    # Partial R² of treatment given covariates
    r2_y_treatment = _partial_r2(r2_full, r2_restricted)

    # Robustness value: how large must partial R²(confounder) be to
    # reduce the effect to zero?
    rv = _robustness_value(treatment_effect, treatment_se, dof)

    # Robustness value at significance level alpha
    t_crit = float(t_dist.ppf(1.0 - alpha / 2.0, dof))
    t_stat = abs(treatment_effect / treatment_se) if treatment_se > 1e-12 else float("inf")
    if t_stat > t_crit:
        rv_alpha = _robustness_value_alpha(treatment_effect, treatment_se, dof, alpha)
    else:
        rv_alpha = 0.0

    # Benchmark bounds
    if benchmark_covariates is None:
        benchmark_covariates = list(covariates)

    bounds: list[OVBBound] = []
    for bench_cov in benchmark_covariates:
        if bench_cov not in covariates:
            continue
        # Partial R² of benchmark covariate with outcome, given treatment + other covariates
        r2yz_dx = _benchmark_partial_r2_outcome(
            y, d, x, covariates, bench_cov, sm,
        )
        # Partial R² of benchmark covariate with treatment, given other covariates
        r2dz_x = _benchmark_partial_r2_treatment(
            d, x, covariates, bench_cov, sm,
        )

        # Scale by kd, ky
        r2dz_x_scaled = min(kd * r2dz_x, 1.0 - 1e-12)
        r2yz_dx_scaled = min(ky * r2yz_dx, 1.0 - 1e-12)

        # Adjusted effect under bias
        adj_effect = _adjusted_effect(
            treatment_effect, treatment_se, dof,
            r2dz_x_scaled, r2yz_dx_scaled,
        )
        adj_se = _adjusted_se(treatment_se, dof, r2dz_x_scaled, r2yz_dx_scaled)
        if adj_se is not None and adj_se > 0:
            t_val = float(t_dist.ppf(1.0 - alpha / 2.0, max(dof - 1, 1)))
            adj_ci_low = adj_effect - t_val * adj_se
            adj_ci_high = adj_effect + t_val * adj_se
        else:
            adj_ci_low = None
            adj_ci_high = None

        bounds.append(OVBBound(
            r2yz_dx=float(r2yz_dx_scaled),
            r2dz_x=float(r2dz_x_scaled),
            adjusted_effect=float(adj_effect),
            adjusted_se=float(adj_se) if adj_se is not None else None,
            adjusted_ci_low=float(adj_ci_low) if adj_ci_low is not None else None,
            adjusted_ci_high=float(adj_ci_high) if adj_ci_high is not None else None,
        ))

    return OVBSummary(
        treatment_effect=treatment_effect,
        treatment_se=treatment_se,
        r2_y_treatment=r2_y_treatment,
        r2_y_full=r2_full,
        robustness_value=rv,
        robustness_value_alpha=rv_alpha,
        bounds=bounds,
    )


def _partial_r2(r2_full: float, r2_restricted: float) -> float:
    """Partial R² of the added variable."""
    denom = 1.0 - r2_restricted
    if denom < 1e-12:
        return 0.0
    return (r2_full - r2_restricted) / denom


def _robustness_value(effect: float, se: float, dof: int) -> float:
    """Robustness value: minimum partial R² to reduce effect to zero.

    RV = 0.5 * (sqrt(f^4 + 4*f^2) - f^2)  where f = t_stat^2 / dof.
    """
    if se < 1e-12:
        return 1.0
    f2 = (effect / se) ** 2 / max(dof, 1)
    return float(0.5 * (math.sqrt(f2**2 + 4.0 * f2) - f2))


def _robustness_value_alpha(
    effect: float, se: float, dof: int, alpha: float,
) -> float:
    """Robustness value at significance level alpha."""
    if se < 1e-12:
        return 1.0
    t_crit = float(t_dist.ppf(1.0 - alpha / 2.0, max(dof, 1)))
    t_stat = abs(effect / se)
    if t_stat <= t_crit:
        return 0.0
    # f_alpha = (t_stat^2 - t_crit^2) / dof
    f_alpha = (t_stat**2 - t_crit**2) / max(dof, 1)
    return float(0.5 * (math.sqrt(f_alpha**2 + 4.0 * f_alpha) - f_alpha))


def _benchmark_partial_r2_outcome(
    y: np.ndarray,
    d: np.ndarray,
    x: np.ndarray,
    covariates: list[str],
    bench_cov: str,
    sm: Any,
) -> float:
    """Partial R² of benchmark covariate with outcome, controlling for treatment + other covariates."""
    bench_idx = covariates.index(bench_cov)
    # Full model includes treatment + all covariates
    full_x = np.column_stack([d, x])
    full_model = sm.OLS(y, sm.add_constant(full_x)).fit()
    # Restricted model drops the benchmark covariate
    other_cols = [i for i in range(x.shape[1]) if i != bench_idx]
    if other_cols:
        restricted_x = np.column_stack([d, x[:, other_cols]])
    else:
        restricted_x = d.reshape(-1, 1)
    restricted_model = sm.OLS(y, sm.add_constant(restricted_x)).fit()
    return _partial_r2(float(full_model.rsquared), float(restricted_model.rsquared))


def _benchmark_partial_r2_treatment(
    d: np.ndarray,
    x: np.ndarray,
    covariates: list[str],
    bench_cov: str,
    sm: Any,
) -> float:
    """Partial R² of benchmark covariate with treatment, controlling for other covariates."""
    bench_idx = covariates.index(bench_cov)
    # Full model: D ~ all covariates
    full_model = sm.OLS(d, sm.add_constant(x)).fit()
    # Restricted model: D ~ other covariates
    other_cols = [i for i in range(x.shape[1]) if i != bench_idx]
    if other_cols:
        restricted_model = sm.OLS(d, sm.add_constant(x[:, other_cols])).fit()
    else:
        restricted_model = sm.OLS(d, np.ones((len(d), 1))).fit()
    return _partial_r2(float(full_model.rsquared), float(restricted_model.rsquared))


def _adjusted_effect(
    effect: float,
    se: float,
    dof: int,
    r2dz_x: float,
    r2yz_dx: float,
) -> float:
    """Bias-adjusted treatment effect under hypothetical confounding."""
    # bias = sign(effect) * se * sqrt(dof) * sqrt(r2yz_dx * r2dz_x / (1 - r2dz_x))
    sign = 1.0 if effect >= 0 else -1.0
    denom = max(1.0 - r2dz_x, 1e-12)
    bias = sign * se * math.sqrt(max(dof, 1)) * math.sqrt(r2yz_dx * r2dz_x / denom)
    return effect - bias


def _adjusted_se(
    se: float,
    dof: int,
    r2dz_x: float,
    r2yz_dx: float,
) -> float | None:
    """Adjusted standard error under hypothetical confounding."""
    denom = max(1.0 - r2dz_x, 1e-12)
    factor = (1.0 - r2yz_dx) / denom
    if factor < 0:
        return None
    return se * math.sqrt(factor)
