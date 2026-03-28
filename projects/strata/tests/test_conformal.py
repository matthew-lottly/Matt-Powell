"""Tests for conformal calibration and coverage guarantees."""

import numpy as np
import pytest

from hetero_conformal.conformal import (
    ConformalResult,
    HeteroConformalCalibrator,
    PropagationAwareCalibrator,
)
from hetero_conformal.graph import generate_synthetic_infrastructure


@pytest.fixture
def calibration_data():
    """Produce synthetic predictions and labels for calibration tests."""
    rng = np.random.default_rng(42)
    n = 200
    node_types = ["power", "water", "telecom"]
    predictions, labels, cal_masks, test_masks = {}, {}, {}, {}

    for ntype in node_types:
        true = rng.uniform(0, 1, size=n).astype(np.float32)
        noise = rng.normal(0, 0.1, size=n).astype(np.float32)
        pred = np.clip(true + noise, 0, 1)
        predictions[ntype] = pred
        labels[ntype] = true

        idx = rng.permutation(n)
        cal_mask = np.zeros(n, dtype=bool)
        test_mask = np.zeros(n, dtype=bool)
        cal_mask[idx[:100]] = True
        test_mask[idx[100:]] = True
        cal_masks[ntype] = cal_mask
        test_masks[ntype] = test_mask

    return predictions, labels, cal_masks, test_masks


class TestHeteroConformalCalibrator:
    def test_calibrate_returns_quantiles(self, calibration_data):
        predictions, labels, cal_masks, _ = calibration_data
        cal = HeteroConformalCalibrator(alpha=0.1)
        quantiles = cal.calibrate(predictions, labels, cal_masks)
        assert set(quantiles.keys()) == {"power", "water", "telecom"}
        for q in quantiles.values():
            assert q > 0

    def test_predict_before_calibrate_raises(self, calibration_data):
        predictions, _, _, test_masks = calibration_data
        cal = HeteroConformalCalibrator(alpha=0.1)
        with pytest.raises(RuntimeError, match="calibrate"):
            cal.predict(predictions, test_masks)

    def test_prediction_intervals_contain_point(self, calibration_data):
        predictions, labels, cal_masks, test_masks = calibration_data
        cal = HeteroConformalCalibrator(alpha=0.1)
        cal.calibrate(predictions, labels, cal_masks)
        result = cal.predict(predictions, test_masks)
        for ntype in result.lower:
            assert np.all(result.point_pred[ntype] >= result.lower[ntype])
            assert np.all(result.point_pred[ntype] <= result.upper[ntype])

    def test_coverage_meets_target(self, calibration_data):
        predictions, labels, cal_masks, test_masks = calibration_data
        alpha = 0.1
        cal = HeteroConformalCalibrator(alpha=alpha)
        cal.calibrate(predictions, labels, cal_masks)
        result = cal.predict(predictions, test_masks)
        coverages = cal.verify_coverage(result, labels, test_masks)
        for ntype, cov in coverages.items():
            # With synthetic data and sufficient samples, coverage should
            # be close to or above 1-alpha
            assert cov >= (1 - alpha) - 0.05, (
                f"{ntype} coverage {cov:.3f} below target {1 - alpha:.2f}"
            )

    def test_invalid_alpha(self):
        with pytest.raises(ValueError):
            HeteroConformalCalibrator(alpha=0.0)
        with pytest.raises(ValueError):
            HeteroConformalCalibrator(alpha=1.0)

    def test_smaller_alpha_wider_intervals(self, calibration_data):
        predictions, labels, cal_masks, test_masks = calibration_data

        cal_tight = HeteroConformalCalibrator(alpha=0.2)
        cal_tight.calibrate(predictions, labels, cal_masks)
        res_tight = cal_tight.predict(predictions, test_masks)

        cal_wide = HeteroConformalCalibrator(alpha=0.05)
        cal_wide.calibrate(predictions, labels, cal_masks)
        res_wide = cal_wide.predict(predictions, test_masks)

        for ntype in res_tight.lower:
            width_tight = np.mean(res_tight.upper[ntype] - res_tight.lower[ntype])
            width_wide = np.mean(res_wide.upper[ntype] - res_wide.lower[ntype])
            assert width_wide >= width_tight


class TestPropagationAwareCalibrator:
    def test_calibrate_with_graph(self):
        graph = generate_synthetic_infrastructure(
            n_power=50, n_water=40, n_telecom=30, seed=42
        )
        rng = np.random.default_rng(42)
        predictions = {}
        for ntype in graph.node_labels:
            noise = rng.normal(0, 0.1, size=len(graph.node_labels[ntype]))
            predictions[ntype] = np.clip(
                graph.node_labels[ntype] + noise, 0, 1
            ).astype(np.float32)

        cal_masks = {ntype: graph.node_masks[ntype]["cal"] for ntype in graph.node_masks}
        test_masks = {ntype: graph.node_masks[ntype]["test"] for ntype in graph.node_masks}
        train_masks = {ntype: graph.node_masks[ntype]["train"] for ntype in graph.node_masks}

        cal = PropagationAwareCalibrator(alpha=0.1, neighborhood_weight=0.3)
        quantiles = cal.calibrate_with_propagation(
            predictions, graph.node_labels, cal_masks, train_masks,
            graph.edge_index, graph.num_nodes,
        )
        assert len(quantiles) == 3

        result = cal.predict(predictions, test_masks)
        coverages = cal.verify_coverage(result, graph.node_labels, test_masks)
        for ntype, cov in coverages.items():
            assert cov >= 0.8, f"{ntype} coverage too low: {cov:.3f}"
