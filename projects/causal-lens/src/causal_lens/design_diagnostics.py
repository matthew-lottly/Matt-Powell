"""Cross-design diagnostic comparison.

Provides a helper that collects validity diagnostics from multiple
identification strategies and presents them in a single summary, making
it easy to compare the assumptions and evidence behind each design.
"""
from __future__ import annotations

from causal_lens.results import DesignDiagnostic


def diagnose_observational(
    *,
    overlap_ok: bool,
    max_smd: float,
    e_value: float | None = None,
    ess_ratio: float | None = None,
) -> list[DesignDiagnostic]:
    """Collect diagnostics for an observational (selection-on-observables) design."""
    diags: list[DesignDiagnostic] = []
    diags.append(DesignDiagnostic(
        design="Observational",
        estimand="ATE/ATT",
        key_assumption="Conditional exchangeability",
        diagnostic_name="Overlap (positivity)",
        diagnostic_value=1.0 if overlap_ok else 0.0,
        passes=overlap_ok,
        detail="Propensity-score ranges of treated and control groups overlap"
        if overlap_ok else "Positivity violation: no common support",
    ))
    diags.append(DesignDiagnostic(
        design="Observational",
        estimand="ATE/ATT",
        key_assumption="Covariate balance after adjustment",
        diagnostic_name="Max |SMD|",
        diagnostic_value=max_smd,
        passes=max_smd < 0.1,
        detail=f"Maximum absolute standardized mean difference = {max_smd:.4f}"
        + (" (< 0.1 threshold)" if max_smd < 0.1 else " (>= 0.1 threshold)"),
    ))
    if e_value is not None:
        diags.append(DesignDiagnostic(
            design="Observational",
            estimand="ATE/ATT",
            key_assumption="No unmeasured confounding",
            diagnostic_name="E-value",
            diagnostic_value=e_value,
            passes=e_value > 2.0,
            detail=f"E-value = {e_value:.2f}: confounder must have RR > {e_value:.2f} "
            "with both treatment and outcome to explain away the effect",
        ))
    if ess_ratio is not None:
        diags.append(DesignDiagnostic(
            design="Observational",
            estimand="ATE/ATT",
            key_assumption="Stable weights",
            diagnostic_name="ESS ratio",
            diagnostic_value=ess_ratio,
            passes=ess_ratio > 0.5,
            detail=f"Effective/actual sample ratio = {ess_ratio:.2f}"
            + (" (adequate)" if ess_ratio > 0.5 else " (severe weight instability)"),
        ))
    return diags


def diagnose_did(
    *,
    parallel_trends_p: float,
    n_pre_periods: int,
) -> list[DesignDiagnostic]:
    """Collect diagnostics for a difference-in-differences design."""
    return [DesignDiagnostic(
        design="Difference-in-Differences",
        estimand="ATT",
        key_assumption="Parallel trends",
        diagnostic_name="Pre-trends F-test p-value",
        diagnostic_value=parallel_trends_p,
        passes=parallel_trends_p > 0.05,
        detail=f"Joint pre-trend interaction test p = {parallel_trends_p:.4f} "
        f"across {n_pre_periods} pre-treatment periods"
        + (" (no evidence against parallel trends)" if parallel_trends_p > 0.05
           else " (parallel trends may be violated)"),
    )]


def diagnose_iv(
    *,
    first_stage_f: float,
    n_instruments: int = 1,
) -> list[DesignDiagnostic]:
    """Collect diagnostics for an instrumental variables design."""
    threshold = 10.0
    return [DesignDiagnostic(
        design="Instrumental Variables",
        estimand="LATE",
        key_assumption="Relevance (strong instrument)",
        diagnostic_name="First-stage F-statistic",
        diagnostic_value=first_stage_f,
        passes=first_stage_f >= threshold,
        detail=f"First-stage F = {first_stage_f:.1f} with {n_instruments} instrument(s)"
        + (f" (>= {threshold} threshold)" if first_stage_f >= threshold
           else f" (< {threshold}: weak instrument concern)"),
    )]


def diagnose_rd(
    *,
    mccrary_p: float | None = None,
    bandwidth: float | None = None,
    n_effective: int | None = None,
    first_stage_f: float | None = None,
    is_fuzzy: bool = False,
) -> list[DesignDiagnostic]:
    """Collect diagnostics for a regression discontinuity design."""
    diags: list[DesignDiagnostic] = []
    if mccrary_p is not None:
        diags.append(DesignDiagnostic(
            design="Regression Discontinuity",
            estimand="LATE" if is_fuzzy else "ATE at cutoff",
            key_assumption="No manipulation of running variable",
            diagnostic_name="McCrary test p-value",
            diagnostic_value=mccrary_p,
            passes=mccrary_p > 0.05,
            detail=f"McCrary density test p = {mccrary_p:.4f}"
            + (" (no evidence of manipulation)" if mccrary_p > 0.05
               else " (possible manipulation of running variable)"),
        ))
    if bandwidth is not None and n_effective is not None:
        diags.append(DesignDiagnostic(
            design="Regression Discontinuity",
            estimand="LATE" if is_fuzzy else "ATE at cutoff",
            key_assumption="Local continuity",
            diagnostic_name="Effective sample within bandwidth",
            diagnostic_value=float(n_effective),
            passes=n_effective >= 20,
            detail=f"{n_effective} observations within bandwidth h = {bandwidth:.3f}"
            + (" (adequate)" if n_effective >= 20 else " (thin support near cutoff)"),
        ))
    if is_fuzzy and first_stage_f is not None:
        diags.append(DesignDiagnostic(
            design="Regression Discontinuity (fuzzy)",
            estimand="LATE",
            key_assumption="Relevance (compliance jump at cutoff)",
            diagnostic_name="First-stage F-statistic",
            diagnostic_value=first_stage_f,
            passes=first_stage_f >= 10.0,
            detail=f"First-stage F = {first_stage_f:.1f}"
            + (" (>= 10)" if first_stage_f >= 10.0 else " (< 10: weak compliance)"),
        ))
    return diags


def diagnose_bunching(
    *,
    excess_mass: float,
    excluded_range: tuple[float, float],
    counterfactual_r2: float | None = None,
) -> list[DesignDiagnostic]:
    """Collect diagnostics for a bunching design."""
    diags: list[DesignDiagnostic] = []
    diags.append(DesignDiagnostic(
        design="Bunching",
        estimand="Structural elasticity",
        key_assumption="Excess mass relative to smooth counterfactual",
        diagnostic_name="Excess mass ratio",
        diagnostic_value=excess_mass,
        passes=excess_mass > 0.0,
        detail=f"Excess mass = {excess_mass:.3f} in [{excluded_range[0]:.2f}, {excluded_range[1]:.2f}]"
        + (" (positive bunching detected)" if excess_mass > 0 else " (no bunching detected)"),
    ))
    if counterfactual_r2 is not None:
        diags.append(DesignDiagnostic(
            design="Bunching",
            estimand="Structural elasticity",
            key_assumption="Smooth counterfactual fit quality",
            diagnostic_name="Counterfactual R²",
            diagnostic_value=counterfactual_r2,
            passes=counterfactual_r2 > 0.9,
            detail=f"Polynomial counterfactual R² = {counterfactual_r2:.3f}"
            + (" (good fit)" if counterfactual_r2 > 0.9 else " (poor fit)"),
        ))
    return diags


def compare_designs(*diagnostic_lists: list[DesignDiagnostic]) -> list[DesignDiagnostic]:
    """Merge diagnostics from multiple designs into one sorted list.

    Returns diagnostics sorted by design name, useful for side-by-side
    comparison of assumption evidence across identification strategies.
    """
    merged: list[DesignDiagnostic] = []
    for dl in diagnostic_lists:
        merged.extend(dl)
    return sorted(merged, key=lambda d: (d.design, d.diagnostic_name))
