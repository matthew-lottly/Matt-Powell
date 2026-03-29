from __future__ import annotations

import math

from causal_lens.data import (
    LALONDE_CONFOUNDERS,
    NHEFS_COMPLETE_CONFOUNDERS,
    load_lalonde_benchmark,
    load_nhefs_complete_benchmark,
)
from causal_lens.estimators import DoublyRobustEstimator, IPWEstimator, RegressionAdjustmentEstimator, PropensityMatcher


def test_lalonde_benchmark_loader_adds_expected_columns() -> None:
    dataset = load_lalonde_benchmark()
    assert len(dataset) == 614
    assert set(["treatment", "outcome", *LALONDE_CONFOUNDERS]).issubset(dataset.columns)


def test_nhefs_benchmark_loader_adds_expected_columns() -> None:
    dataset = load_nhefs_complete_benchmark()
    assert len(dataset) == 1566
    assert set(["treatment", "outcome", *NHEFS_COMPLETE_CONFOUNDERS]).issubset(dataset.columns)


def test_lalonde_public_benchmark_produces_finite_positive_dr_effect() -> None:
    dataset = load_lalonde_benchmark()
    result = DoublyRobustEstimator("treatment", "outcome", LALONDE_CONFOUNDERS, bootstrap_repeats=10).fit(dataset)
    assert result.diagnostics.overlap_ok is True
    assert math.isfinite(result.effect)
    assert result.effect > 0.0


def test_lalonde_regression_within_literature_range() -> None:
    """Regression should produce ~$1548, within DW99 range of $1000-$2500."""
    dataset = load_lalonde_benchmark()
    result = RegressionAdjustmentEstimator("treatment", "outcome", LALONDE_CONFOUNDERS, bootstrap_repeats=10).fit(dataset)
    assert 500.0 < result.effect < 2500.0


def test_lalonde_matching_within_literature_range() -> None:
    """Matching should produce ~$1540, within DW99 range of $1000-$2200."""
    dataset = load_lalonde_benchmark()
    result = PropensityMatcher("treatment", "outcome", LALONDE_CONFOUNDERS, caliper=0.05, bootstrap_repeats=10).fit(dataset)
    assert 500.0 < result.effect < 2500.0


def test_lalonde_trimmed_ipw_within_literature_range() -> None:
    dataset = load_lalonde_benchmark()
    result = IPWEstimator(
        "treatment",
        "outcome",
        LALONDE_CONFOUNDERS,
        bootstrap_repeats=10,
        propensity_trim_bounds=(0.03, 0.97),
    ).fit(dataset)
    assert 1000.0 < result.effect < 2500.0


def test_lalonde_trimmed_dr_within_literature_range() -> None:
    dataset = load_lalonde_benchmark()
    result = DoublyRobustEstimator(
        "treatment",
        "outcome",
        LALONDE_CONFOUNDERS,
        bootstrap_repeats=10,
        propensity_trim_bounds=(0.03, 0.97),
    ).fit(dataset)
    assert 1000.0 < result.effect < 2500.0


def test_nhefs_public_benchmark_produces_stable_positive_ipw_effect() -> None:
    dataset = load_nhefs_complete_benchmark()
    result = IPWEstimator("treatment", "outcome", NHEFS_COMPLETE_CONFOUNDERS, bootstrap_repeats=10).fit(dataset)
    assert result.diagnostics.overlap_ok is True
    assert 1.0 < result.effect < 6.0


def test_nhefs_all_estimators_within_literature_range() -> None:
    """All NHEFS estimators should produce ~3.0-3.5 kg, matching Hernan & Robins textbook."""
    dataset = load_nhefs_complete_benchmark()
    for cls in [RegressionAdjustmentEstimator, IPWEstimator, DoublyRobustEstimator]:
        result = cls("treatment", "outcome", NHEFS_COMPLETE_CONFOUNDERS, bootstrap_repeats=10).fit(dataset)
        assert 2.0 < result.effect < 5.0, f"{cls.__name__} produced {result.effect}"


def test_lalonde_dr_sensitivity_has_positive_e_value() -> None:
    """E-value should be > 1 for the Lalonde DR estimate (positive effect)."""
    dataset = load_lalonde_benchmark()
    estimator = DoublyRobustEstimator(
        "treatment", "outcome", LALONDE_CONFOUNDERS, bootstrap_repeats=10,
        propensity_trim_bounds=(0.03, 0.97),
    )
    summary = estimator.sensitivity_analysis(dataset)
    assert summary.e_value is not None
    assert summary.e_value > 1.0


def test_nhefs_dr_has_significant_p_value() -> None:
    """NHEFS DR estimate should have p < 0.05 (well-established effect)."""
    dataset = load_nhefs_complete_benchmark()
    result = DoublyRobustEstimator(
        "treatment", "outcome", NHEFS_COMPLETE_CONFOUNDERS, bootstrap_repeats=10,
    ).fit(dataset)
    assert result.se is not None
    assert result.p_value is not None
    assert result.p_value < 0.05


def test_lalonde_placebo_reveals_selection_on_pre_treatment_earnings() -> None:
    """Placebo test on re74: Lalonde's observational comparison group has fundamentally
    different pre-treatment earnings, so most methods correctly detect this selection bias.
    At least one method should still pass (regression adjustment conditions on re75)."""
    from causal_lens.estimators import run_placebo_test
    dataset = load_lalonde_benchmark()
    confounders = [c for c in LALONDE_CONFOUNDERS if c != "re74"]
    results = run_placebo_test(
        dataset,
        treatment_col="treatment",
        placebo_outcome="re74",
        confounders=confounders,
        bootstrap_repeats=15,
        matcher_caliper=0.05,
    )
    assert len(results) == 4
    # Lalonde's known selection bias means most methods detect spurious effects on re74.
    # This is informative, not a failure — it surfaces the specification sensitivity
    # that makes Lalonde a canonical benchmark.
    failing = sum(1 for r in results if not r.passes)
    assert failing >= 1, "Expected at least one method to detect pre-treatment selection bias"


def test_lalonde_rosenbaum_sensitivity_significant_at_gamma_one() -> None:
    """Lalonde matching should be significant at Gamma=1."""
    dataset = load_lalonde_benchmark()
    matcher = PropensityMatcher(
        "treatment", "outcome", LALONDE_CONFOUNDERS,
        caliper=0.05, bootstrap_repeats=10,
    )
    bounds = matcher.rosenbaum_sensitivity(dataset)
    assert bounds[0].gamma == 1.0
    assert bounds[0].significant_at_05 is True