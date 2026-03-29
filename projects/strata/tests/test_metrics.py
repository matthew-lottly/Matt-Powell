"""Tests for evaluation metrics."""

import numpy as np
import pytest

from hetero_conformal.conformal import ConformalResult
from hetero_conformal.metrics import (
    calibration_error,
    marginal_coverage,
    mean_interval_width,
    prediction_set_efficiency,
    rmse_per_type,
    type_conditional_coverage,
)


@pytest.fixture
def perfect_result():
    """Conformal result where all true labels are covered."""
    rng = np.random.default_rng(0)
    true = {"power": rng.uniform(0, 1, 50).astype(np.float32)}
    pred = true["power"].copy()
    return (
        ConformalResult(
            lower={"power": pred - 0.5},
            upper={"power": pred + 0.5},
            point_pred={"power": pred},
            alpha=0.1,
            quantiles={"power": 0.5},
        ),
        true,
    )


@pytest.fixture
def multi_type_result():
    rng = np.random.default_rng(1)
    types = ["power", "water", "telecom"]
    lower, upper, point, labels = {}, {}, {}, {}
    for t in types:
        n = 100
        true = rng.uniform(0, 1, n).astype(np.float32)
        pred = np.clip(true + rng.normal(0, 0.05, n), 0, 1).astype(np.float32)
        q = 0.2
        lower[t] = pred - q
        upper[t] = pred + q
        point[t] = pred
        labels[t] = true
    result = ConformalResult(lower=lower, upper=upper, point_pred=point, alpha=0.1, quantiles={t: 0.2 for t in types})
    return result, labels


class TestMarginalCoverage:
    def test_perfect_coverage(self, perfect_result):
        result, labels = perfect_result
        cov = marginal_coverage(result, labels)
        assert cov == 1.0

    def test_zero_width_intervals(self):
        pred = np.array([0.5, 0.5, 0.5])
        true = np.array([0.3, 0.5, 0.7])
        result = ConformalResult(
            lower={"a": pred}, upper={"a": pred},
            point_pred={"a": pred}, alpha=0.1, quantiles={"a": 0.0},
        )
        cov = marginal_coverage(result, {"a": true})
        assert cov == pytest.approx(1 / 3)


class TestTypeConditionalCoverage:
    def test_per_type(self, multi_type_result):
        result, labels = multi_type_result
        covs = type_conditional_coverage(result, labels)
        assert set(covs.keys()) == {"power", "water", "telecom"}
        for c in covs.values():
            assert 0.0 <= c <= 1.0


class TestPredictionSetEfficiency:
    def test_widths_positive(self, multi_type_result):
        result, _ = multi_type_result
        widths = prediction_set_efficiency(result)
        for w in widths.values():
            assert w > 0

    def test_mean_width(self, multi_type_result):
        result, _ = multi_type_result
        mw = mean_interval_width(result)
        assert mw > 0


class TestCalibrationError:
    def test_ece_nonnegative(self, multi_type_result):
        result, labels = multi_type_result
        ece = calibration_error(result, labels)
        assert ece >= 0.0

    def test_ece_bounded(self, multi_type_result):
        result, labels = multi_type_result
        ece = calibration_error(result, labels)
        assert ece <= 1.0


class TestRMSE:
    def test_perfect_predictions(self):
        pred = {"a": np.array([1.0, 2.0, 3.0])}
        labels = {"a": np.array([1.0, 2.0, 3.0])}
        rmse = rmse_per_type(pred, labels)
        assert rmse["a"] == pytest.approx(0.0)

    def test_nonzero_rmse(self):
        pred = {"a": np.array([1.0, 2.0, 3.0])}
        labels = {"a": np.array([1.1, 2.1, 3.1])}
        rmse = rmse_per_type(pred, labels)
        assert rmse["a"] > 0
