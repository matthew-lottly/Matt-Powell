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