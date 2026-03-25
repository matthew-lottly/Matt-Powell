"""Tests for new publication-strengthening features:
- Cinelli-Hazlett OVB sensitivity analysis
- Staggered difference-in-differences
- Cross-design diagnostics
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from causal_lens.diagnostics import ovb_bounds
from causal_lens.panel import StaggeredDiD
from causal_lens.design_diagnostics import (
    compare_designs,
    diagnose_bunching,
    diagnose_did,
    diagnose_iv,
    diagnose_observational,
    diagnose_rd,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def ovb_data() -> pd.DataFrame:
    """Synthetic data with a known confounding structure."""
    rng = np.random.default_rng(42)
    n = 500
    x1 = rng.normal(size=n)
    x2 = rng.normal(size=n)
    # Treatment is influenced by x1 and x2
    d = (0.5 * x1 + 0.3 * x2 + rng.normal(size=n) > 0).astype(float)
    # Outcome depends on treatment, x1, x2
    y = 2.0 * d + 1.5 * x1 + 0.8 * x2 + rng.normal(size=n)
    return pd.DataFrame({"y": y, "d": d, "x1": x1, "x2": x2})


@pytest.fixture()
def staggered_panel() -> pd.DataFrame:
    """Synthetic staggered-adoption panel data."""
    rng = np.random.default_rng(123)
    n_units = 30
    n_periods = 10
    rows = []
    cohorts = {}
    for i in range(n_units):
        if i < 10:
            # Never treated
            cohorts[i] = np.inf
        elif i < 20:
            # Treated starting period 5
            cohorts[i] = 5
        else:
            # Treated starting period 7
            cohorts[i] = 7

    for i in range(n_units):
        unit_fe = rng.normal() * 2
        for t in range(1, n_periods + 1):
            treated = 1 if t >= cohorts[i] else 0
            # True effect = 3.0 for all cohorts
            y = unit_fe + 0.5 * t + 3.0 * treated + rng.normal()
            rows.append({
                "unit": i,
                "time": t,
                "outcome": y,
                "cohort": cohorts[i],
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# OVB Sensitivity Tests
# ---------------------------------------------------------------------------

class TestOVBBounds:
    def test_returns_ovb_summary(self, ovb_data: pd.DataFrame) -> None:
        result = ovb_bounds(
            ovb_data,
            outcome_col="y",
            treatment_col="d",
            covariates=["x1", "x2"],
        )
        assert result.treatment_effect != 0.0
        assert result.treatment_se > 0.0
        assert 0.0 <= result.r2_y_treatment <= 1.0
        assert 0.0 <= result.r2_y_full <= 1.0
        assert 0.0 <= result.robustness_value <= 1.0

    def test_robustness_value_positive_when_significant(self, ovb_data: pd.DataFrame) -> None:
        result = ovb_bounds(
            ovb_data,
            outcome_col="y",
            treatment_col="d",
            covariates=["x1", "x2"],
        )
        # With a true effect of 2.0 and n=500, this should be significant
        assert result.robustness_value > 0.0
        assert result.robustness_value_alpha is not None
        assert result.robustness_value_alpha > 0.0

    def test_benchmark_bounds_computed(self, ovb_data: pd.DataFrame) -> None:
        result = ovb_bounds(
            ovb_data,
            outcome_col="y",
            treatment_col="d",
            covariates=["x1", "x2"],
            benchmark_covariates=["x1"],
        )
        assert len(result.bounds) == 1
        bound = result.bounds[0]
        assert 0.0 <= bound.r2yz_dx <= 1.0
        assert 0.0 <= bound.r2dz_x <= 1.0
        assert bound.adjusted_effect is not None

    def test_all_covariates_as_benchmarks(self, ovb_data: pd.DataFrame) -> None:
        result = ovb_bounds(
            ovb_data,
            outcome_col="y",
            treatment_col="d",
            covariates=["x1", "x2"],
        )
        # Default: each covariate is its own benchmark
        assert len(result.bounds) == 2

    def test_scaled_bounds_with_ky_kd(self, ovb_data: pd.DataFrame) -> None:
        result_base = ovb_bounds(
            ovb_data,
            outcome_col="y",
            treatment_col="d",
            covariates=["x1", "x2"],
            benchmark_covariates=["x1"],
            kd=1.0,
            ky=1.0,
        )
        result_scaled = ovb_bounds(
            ovb_data,
            outcome_col="y",
            treatment_col="d",
            covariates=["x1", "x2"],
            benchmark_covariates=["x1"],
            kd=2.0,
            ky=2.0,
        )
        # Scaled bounds should have higher R² values (capped at 1)
        assert result_scaled.bounds[0].r2dz_x >= result_base.bounds[0].r2dz_x
        assert result_scaled.bounds[0].r2yz_dx >= result_base.bounds[0].r2yz_dx

    def test_to_dict(self, ovb_data: pd.DataFrame) -> None:
        result = ovb_bounds(
            ovb_data,
            outcome_col="y",
            treatment_col="d",
            covariates=["x1", "x2"],
        )
        d = result.to_dict()
        assert "treatment_effect" in d
        assert "robustness_value" in d
        assert "bounds" in d
        assert isinstance(d["bounds"], list)


# ---------------------------------------------------------------------------
# Staggered DiD Tests
# ---------------------------------------------------------------------------

class TestStaggeredDiD:
    def test_basic_fit(self, staggered_panel: pd.DataFrame) -> None:
        estimator = StaggeredDiD(
            unit_col="unit",
            time_col="time",
            outcome_col="outcome",
            cohort_col="cohort",
            control="never_treated",
        )
        result = estimator.fit(staggered_panel)
        assert result.method == "StaggeredDiD"
        assert result.n_groups == 2  # cohorts 5 and 7
        assert result.n_units == 30
        # True effect is 3.0; allow generous tolerance for small sample
        assert abs(result.att - 3.0) < 2.0

    def test_not_yet_treated_control(self, staggered_panel: pd.DataFrame) -> None:
        estimator = StaggeredDiD(
            unit_col="unit",
            time_col="time",
            outcome_col="outcome",
            cohort_col="cohort",
            control="not_yet_treated",
        )
        result = estimator.fit(staggered_panel)
        assert result.method == "StaggeredDiD"
        assert result.att != 0.0  # Should find an effect

    def test_group_effects_returned(self, staggered_panel: pd.DataFrame) -> None:
        estimator = StaggeredDiD(
            unit_col="unit",
            time_col="time",
            outcome_col="outcome",
            cohort_col="cohort",
        )
        result = estimator.fit(staggered_panel)
        assert len(result.group_effects) == 2
        assert len(result.group_weights) == 2
        # Weights should sum to 1
        assert abs(sum(result.group_weights.values()) - 1.0) < 1e-10

    def test_confidence_interval(self, staggered_panel: pd.DataFrame) -> None:
        estimator = StaggeredDiD(
            unit_col="unit",
            time_col="time",
            outcome_col="outcome",
            cohort_col="cohort",
        )
        result = estimator.fit(staggered_panel)
        if result.se is not None and result.se > 0:
            assert result.ci_low is not None
            assert result.ci_high is not None
            assert result.ci_low < result.att < result.ci_high

    def test_invalid_control_raises(self) -> None:
        with pytest.raises(ValueError, match="control must be"):
            StaggeredDiD(
                unit_col="unit",
                time_col="time",
                outcome_col="outcome",
                cohort_col="cohort",
                control="invalid",
            )

    def test_no_cohorts_raises(self) -> None:
        # All units are never-treated
        df = pd.DataFrame({
            "unit": [0, 0, 1, 1],
            "time": [1, 2, 1, 2],
            "outcome": [1.0, 2.0, 1.5, 2.5],
            "cohort": [np.inf, np.inf, np.inf, np.inf],
        })
        estimator = StaggeredDiD(
            unit_col="unit",
            time_col="time",
            outcome_col="outcome",
            cohort_col="cohort",
        )
        with pytest.raises(ValueError, match="No treatment cohorts"):
            estimator.fit(df)

    def test_to_dict(self, staggered_panel: pd.DataFrame) -> None:
        estimator = StaggeredDiD(
            unit_col="unit",
            time_col="time",
            outcome_col="outcome",
            cohort_col="cohort",
        )
        result = estimator.fit(staggered_panel)
        d = result.to_dict()
        assert "att" in d
        assert "group_effects" in d
        assert "n_groups" in d


# ---------------------------------------------------------------------------
# Cross-Design Diagnostics Tests
# ---------------------------------------------------------------------------

class TestDesignDiagnostics:
    def test_observational_diagnostics(self) -> None:
        diags = diagnose_observational(
            overlap_ok=True,
            max_smd=0.05,
            e_value=3.5,
            ess_ratio=0.8,
        )
        assert len(diags) == 4
        assert all(d.design == "Observational" for d in diags)
        assert all(d.passes for d in diags)

    def test_observational_failure(self) -> None:
        diags = diagnose_observational(
            overlap_ok=False,
            max_smd=0.25,
        )
        assert len(diags) == 2
        assert not diags[0].passes  # overlap
        assert not diags[1].passes  # SMD

    def test_did_diagnostics(self) -> None:
        diags = diagnose_did(parallel_trends_p=0.45, n_pre_periods=3)
        assert len(diags) == 1
        assert diags[0].passes is True
        assert diags[0].design == "Difference-in-Differences"

    def test_did_violation(self) -> None:
        diags = diagnose_did(parallel_trends_p=0.01, n_pre_periods=3)
        assert not diags[0].passes

    def test_iv_diagnostics(self) -> None:
        diags = diagnose_iv(first_stage_f=25.0)
        assert len(diags) == 1
        assert diags[0].passes is True

    def test_iv_weak_instrument(self) -> None:
        diags = diagnose_iv(first_stage_f=5.0)
        assert not diags[0].passes

    def test_rd_diagnostics(self) -> None:
        diags = diagnose_rd(
            mccrary_p=0.5,
            bandwidth=0.5,
            n_effective=100,
        )
        assert len(diags) == 2
        assert all(d.passes for d in diags)

    def test_rd_fuzzy(self) -> None:
        diags = diagnose_rd(
            mccrary_p=0.3,
            bandwidth=0.5,
            n_effective=50,
            first_stage_f=15.0,
            is_fuzzy=True,
        )
        assert len(diags) == 3  # McCrary + effective N + first-stage F

    def test_bunching_diagnostics(self) -> None:
        diags = diagnose_bunching(
            excess_mass=1.5,
            excluded_range=(-1.0, 1.0),
            counterfactual_r2=0.95,
        )
        assert len(diags) == 2
        assert all(d.passes for d in diags)

    def test_compare_designs(self) -> None:
        obs = diagnose_observational(overlap_ok=True, max_smd=0.05)
        did = diagnose_did(parallel_trends_p=0.5, n_pre_periods=3)
        iv = diagnose_iv(first_stage_f=20.0)
        merged = compare_designs(obs, did, iv)
        assert len(merged) == len(obs) + len(did) + len(iv)
        # Should be sorted by design name
        designs = [d.design for d in merged]
        assert designs == sorted(designs)

    def test_to_dict(self) -> None:
        diags = diagnose_observational(overlap_ok=True, max_smd=0.05)
        d = diags[0].to_dict()
        assert "design" in d
        assert "passes" in d
        assert "diagnostic_value" in d
