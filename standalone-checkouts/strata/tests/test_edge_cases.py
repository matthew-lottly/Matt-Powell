"""Edge-case tests for STRATA components.

Covers: empty masks, zero neighbors, numerical overflow, single-node types,
CQR propagation=False, ensemble n_members=1, and degenerate graph structures.
"""

import numpy as np
import pytest
import torch

from hetero_conformal.graph import HeteroInfraGraph, generate_synthetic_infrastructure
from hetero_conformal.model import HeteroGNN
from hetero_conformal.conformal import HeteroConformalCalibrator, PropagationAwareCalibrator
from hetero_conformal.metrics import (
    marginal_coverage,
    type_conditional_coverage,
    mean_interval_width,
    calibration_error,
    per_type_ece,
    prediction_set_efficiency,
    rmse_per_type,
)
from hetero_conformal.ensemble import EnsembleHeteroGNN, EnsembleCalibrator
from hetero_conformal.advanced_calibrators import (
    LearnableLambdaCalibrator,
    CQRCalibrator,
    AttentionCalibrator,
)
from hetero_conformal.meta_calibrator import MetaCalibrator
from hetero_conformal.diagnostics import (
    nonexchangeability_test,
    spatial_autocorrelation_test,
    bootstrap_ci,
    bootstrap_width_ci,
    full_diagnostic_report,
)
from hetero_conformal.conformal import ConformalResult


# ─── Fixtures ───────────────────────────────────────────────────────────────

def _make_tiny_graph(n_power=5, n_water=3, n_telecom=2, feat_dim=4, seed=42):
    """Create a minimal HeteroInfraGraph for testing."""
    rng = np.random.default_rng(seed)
    graph = HeteroInfraGraph()
    counts = {"power": n_power, "water": n_water, "telecom": n_telecom}
    for ntype, n in counts.items():
        if n == 0:
            continue
        graph.node_features[ntype] = rng.standard_normal((n, feat_dim)).astype(np.float32)
        graph.node_positions[ntype] = rng.uniform(0, 1, (n, 2)).astype(np.float32)
        graph.node_labels[ntype] = rng.standard_normal(n).astype(np.float32)
        mask = np.zeros(n, dtype=bool)
        n_train = max(1, n // 3)
        n_cal = max(1, n // 3)
        mask[:n_train] = True
        graph.node_masks[ntype] = {
            "train": mask.copy(),
            "cal": np.roll(mask.copy(), n_train)[:n] & ~mask,
            "test": np.ones(n, dtype=bool),
        }
        # Fix: make sure test doesn't overlap
        graph.node_masks[ntype]["test"] = ~(graph.node_masks[ntype]["train"] | graph.node_masks[ntype]["cal"])
        if not graph.node_masks[ntype]["test"].any():
            graph.node_masks[ntype]["test"][-1] = True

    # Add minimal edges
    for src_t, rel, dst_t in [("power", "feeds", "power"), ("water", "pipes", "water")]:
        if src_t in counts and counts[src_t] > 1:
            n = counts[src_t]
            src = np.arange(n - 1, dtype=np.int64)
            dst = np.arange(1, n, dtype=np.int64)
            graph.edge_index[(src_t, rel, dst_t)] = np.stack([
                np.concatenate([src, dst]),
                np.concatenate([dst, src]),
            ])
        else:
            graph.edge_index[(src_t, rel, dst_t)] = np.zeros((2, 0), dtype=np.int64)

    # Cross edges
    for src_t, rel, dst_t in [("power", "colocated", "water"), ("water", "colocated", "telecom"), ("power", "colocated", "telecom")]:
        if src_t in counts and dst_t in counts and counts[src_t] > 0 and counts[dst_t] > 0:
            graph.edge_index[(src_t, rel, dst_t)] = np.array([[0], [0]], dtype=np.int64)
        else:
            graph.edge_index[(src_t, rel, dst_t)] = np.zeros((2, 0), dtype=np.int64)

    # telecom self-edges
    if "telecom" in counts and counts["telecom"] > 1:
        graph.edge_index[("telecom", "connects", "telecom")] = np.array([[0], [1]], dtype=np.int64)
    else:
        graph.edge_index[("telecom", "connects", "telecom")] = np.zeros((2, 0), dtype=np.int64)

    return graph


def _get_predictions(graph, seed=0):
    """Get predictions from a quick-trained model."""
    torch.manual_seed(seed)
    in_dims = {nt: f.shape[1] for nt, f in graph.node_features.items()}
    edge_types = list(graph.edge_index.keys())
    model = HeteroGNN(in_dims=in_dims, hidden_dim=16, num_layers=2,
                      edge_types=edge_types, dropout=0.0)
    model.eval()
    with torch.no_grad():
        x = {nt: torch.tensor(f, dtype=torch.float32) for nt, f in graph.node_features.items()}
        ei = {et: torch.tensor(e, dtype=torch.long) for et, e in graph.edge_index.items()}
        preds = model(x, ei, graph.num_nodes)
    return {nt: p.numpy() for nt, p in preds.items()}


# ─── Empty / Zero Tests ────────────────────────────────────────────────────

class TestEmptyMasks:
    """Tests with empty calibration or test masks."""

    def test_calibrator_empty_cal_mask(self):
        """HeteroConformalCalibrator handles empty calibration set."""
        cal = HeteroConformalCalibrator(alpha=0.1)
        preds = {"power": np.array([1.0, 2.0, 3.0])}
        labels = {"power": np.array([1.1, 2.1, 3.1])}
        masks = {"power": np.array([False, False, False])}
        q = cal.calibrate(preds, labels, masks)
        assert q["power"] == float("inf")

    def test_predict_after_empty_cal(self):
        """Prediction with inf quantile gives infinite intervals."""
        cal = HeteroConformalCalibrator(alpha=0.1)
        preds = {"power": np.array([1.0, 2.0])}
        labels = {"power": np.array([1.1, 2.1])}
        cal.calibrate(preds, labels, {"power": np.array([False, False])})
        result = cal.predict(preds)
        assert np.all(np.isinf(result.upper["power"] - result.lower["power"]))

    def test_coverage_empty_type(self):
        """Coverage computation with empty type."""
        result = ConformalResult(
            lower={"power": np.array([])},
            upper={"power": np.array([])},
            point_pred={"power": np.array([])},
            alpha=0.1,
            quantiles={"power": 1.0},
        )
        cov = marginal_coverage(result, {"power": np.array([])}, {"power": np.array([], dtype=bool)})
        assert cov == 0.0

    def test_metrics_empty_predictions(self):
        """All metric functions handle empty arrays gracefully."""
        result = ConformalResult(
            lower={"power": np.array([])},
            upper={"power": np.array([])},
            point_pred={"power": np.array([])},
            alpha=0.1,
            quantiles={"power": 1.0},
        )
        assert mean_interval_width(result) == 0.0
        assert prediction_set_efficiency(result) == {"power": 0.0}


class TestZeroNeighbors:
    """Tests for nodes with zero neighbors."""

    def test_propagation_zero_neighbors(self):
        """PropagationAwareCalibrator handles isolated nodes."""
        graph = _make_tiny_graph(n_power=3, n_water=0, n_telecom=0)
        # Remove all edges
        for key in list(graph.edge_index.keys()):
            graph.edge_index[key] = np.zeros((2, 0), dtype=np.int64)

        preds = {"power": np.array([1.0, 2.0, 3.0])}
        labels = {"power": np.array([1.1, 1.9, 3.2])}
        cal_masks = {"power": np.array([True, True, False])}
        train_masks = {"power": np.array([True, True, False])}

        cal = PropagationAwareCalibrator(alpha=0.1, neighborhood_weight=0.5)
        cal.calibrate_with_propagation(
            preds, labels, cal_masks, train_masks,
            graph.edge_index, graph.num_nodes,
        )
        # Sigma should be 1.0 for all (no neighbors)
        for s in cal._sigma["power"]:
            assert s == pytest.approx(1.0, abs=1e-5)

    def test_meta_calibrator_zero_neighbors(self):
        """MetaCalibrator works with isolated nodes."""
        graph = _make_tiny_graph(n_power=10, n_water=0, n_telecom=0)
        for key in list(graph.edge_index.keys()):
            graph.edge_index[key] = np.zeros((2, 0), dtype=np.int64)

        preds = {"power": np.random.randn(10).astype(np.float32)}
        labels = {"power": np.random.randn(10).astype(np.float32)}
        train_masks = {"power": np.array([True]*5 + [False]*5)}
        cal_masks = {"power": np.array([False]*5 + [True]*3 + [False]*2)}

        mc = MetaCalibrator(alpha=0.1, meta_epochs=10)
        mc.calibrate(
            graph.node_features, preds, labels,
            cal_masks, train_masks, graph.edge_index, graph.num_nodes,
        )
        result = mc.predict(preds)
        assert "power" in result.lower


class TestNumericalStability:
    """Tests for numerical edge cases."""

    def test_very_large_residuals(self):
        """Calibrator handles very large residuals."""
        cal = HeteroConformalCalibrator(alpha=0.1)
        preds = {"power": np.array([1e10, -1e10, 0.0])}
        labels = {"power": np.array([-1e10, 1e10, 0.0])}
        masks = {"power": np.array([True, True, True])}
        q = cal.calibrate(preds, labels, masks)
        assert np.isfinite(q["power"])

    def test_identical_predictions_labels(self):
        """All residuals are zero — quantile should be 0."""
        cal = HeteroConformalCalibrator(alpha=0.1)
        vals = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        q = cal.calibrate({"power": vals}, {"power": vals}, {"power": np.ones(5, dtype=bool)})
        assert q["power"] == pytest.approx(0.0)

    def test_constant_predictions(self):
        """All predictions are the same value."""
        cal = HeteroConformalCalibrator(alpha=0.1)
        preds = {"power": np.ones(10)}
        labels = {"power": np.random.randn(10)}
        masks = {"power": np.ones(10, dtype=bool)}
        q = cal.calibrate(preds, labels, masks)
        assert np.isfinite(q["power"])


class TestSingleNodeType:
    """Tests with only a single node in a type."""

    def test_single_cal_node(self):
        """Calibration with exactly 1 calibration node."""
        cal = HeteroConformalCalibrator(alpha=0.1)
        preds = {"power": np.array([1.0, 2.0])}
        labels = {"power": np.array([1.5, 2.5])}
        masks = {"power": np.array([True, False])}
        q = cal.calibrate(preds, labels, masks)
        assert np.isfinite(q["power"])

    def test_single_node_graph(self):
        """Model works with a graph that has 1 node per type."""
        graph = _make_tiny_graph(n_power=1, n_water=1, n_telecom=1)
        preds = _get_predictions(graph)
        for nt in preds:
            assert len(preds[nt]) == 1


class TestCQREdgeCases:
    """CQR calibrator edge cases."""

    def _get_hidden(self, graph):
        """Get GNN hidden representations for CQR."""
        torch.manual_seed(0)
        in_dims = {nt: f.shape[1] for nt, f in graph.node_features.items()}
        edge_types = list(graph.edge_index.keys())
        model = HeteroGNN(in_dims=in_dims, hidden_dim=16, num_layers=2,
                          edge_types=edge_types, dropout=0.0)
        model.eval()
        x = {nt: torch.tensor(f, dtype=torch.float32) for nt, f in graph.node_features.items()}
        ei = {et: torch.tensor(e, dtype=torch.long) for et, e in graph.edge_index.items()}
        # Forward through GNN layers (skip output heads) to get hidden reps
        import torch.nn.functional as F
        h = {}
        for ntype in x:
            h[ntype] = F.relu(model.input_proj[ntype](x[ntype]))
        for layer in model.mp_layers:
            h_new = layer(h, ei, graph.num_nodes)
            for ntype in h:
                h_new[ntype] = F.relu(h_new[ntype])
                h_new[ntype] = h_new[ntype] + h[ntype]
            h = h_new
        return {nt: t.detach() for nt, t in h.items()}

    def test_cqr_propagation_false(self):
        """CQR works with use_propagation=False."""
        graph = _make_tiny_graph(n_power=20, n_water=15, n_telecom=10)
        preds = _get_predictions(graph)
        hidden = self._get_hidden(graph)

        cqr = CQRCalibrator(alpha=0.1, use_propagation=False, quantile_epochs=5, verbose=False)
        cqr.train_quantile_heads(
            hidden, graph.node_labels,
            {nt: m["train"] for nt, m in graph.node_masks.items()},
            hidden_dim=16,
        )
        cqr.calibrate(
            preds, graph.node_labels,
            {nt: m["cal"] for nt, m in graph.node_masks.items()},
            {nt: m["train"] for nt, m in graph.node_masks.items()},
            graph.edge_index, graph.num_nodes,
        )
        result = cqr.predict(
            preds,
            {nt: m["test"] for nt, m in graph.node_masks.items()},
        )
        for nt in result.lower:
            assert np.all(result.lower[nt] <= result.upper[nt])

    def test_cqr_quantile_inversion_handling(self):
        """CQR handles cases where lower > upper quantile."""
        graph = _make_tiny_graph(n_power=20, n_water=15, n_telecom=10)
        hidden = self._get_hidden(graph)

        cqr = CQRCalibrator(alpha=0.1, quantile_epochs=2, verbose=False)
        cqr.train_quantile_heads(
            hidden, graph.node_labels,
            {nt: m["train"] for nt, m in graph.node_masks.items()},
            hidden_dim=16,
        )
        # After training, quantile bounds should be properly ordered
        for nt in cqr._q_lo:
            assert np.all(cqr._q_lo[nt] <= cqr._q_hi[nt]), f"Quantile inversion in {nt}"


class TestEnsembleEdgeCases:
    """Ensemble edge cases."""

    def test_ensemble_single_member(self):
        """Ensemble with n_members=1 works like a single model."""
        from hetero_conformal.experiment import ExperimentConfig
        graph = generate_synthetic_infrastructure(
            n_power=30, n_water=20, n_telecom=15, seed=42,
        )
        config = ExperimentConfig(
            hidden_dim=16, num_layers=2, epochs=5, patience=5,
        )
        ens = EnsembleHeteroGNN(n_members=1)
        ens.build_and_train(graph, config)
        mean_pred, var_pred = ens.predict(graph)
        for nt in var_pred:
            # Variance should be exactly 0 with 1 member
            assert np.allclose(var_pred[nt], 0.0)

    def test_ensemble_calibrator_zero_variance(self):
        """EnsembleCalibrator handles zero variance gracefully."""
        cal = EnsembleCalibrator(alpha=0.1)
        preds = {"power": np.array([1.0, 2.0, 3.0, 4.0, 5.0])}
        var = {"power": np.zeros(5)}  # zero variance
        labels = {"power": np.array([1.1, 2.1, 3.1, 4.1, 5.1])}
        masks = {"power": np.ones(5, dtype=bool)}
        q = cal.calibrate(preds, var, labels, masks)
        assert np.isfinite(q["power"])


class TestDiagnosticsEdgeCases:
    """Diagnostics with edge-case inputs."""

    def test_nonexchangeability_few_scores(self):
        """Runs test with < 10 scores returns nan."""
        result = nonexchangeability_test(np.array([1.0, 2.0, 3.0]))
        assert np.isnan(result["statistic"])
        assert result["p_value"] == 1.0

    def test_spatial_autocorrelation_few_points(self):
        """Moran's I with too few points returns nan."""
        result = spatial_autocorrelation_test(
            np.array([1.0, 2.0]), np.array([[0, 0], [1, 1]]), k_neighbors=5,
        )
        assert np.isnan(result["morans_i"])

    def test_bootstrap_ci_small_sample(self):
        """Bootstrap CI works with small samples."""
        result = ConformalResult(
            lower={"power": np.array([0.0, 1.0])},
            upper={"power": np.array([2.0, 3.0])},
            point_pred={"power": np.array([1.0, 2.0])},
            alpha=0.1,
            quantiles={"power": 1.0},
        )
        labels = {"power": np.array([1.0, 2.5])}
        masks = {"power": np.array([True, True])}
        ci = bootstrap_ci(marginal_coverage, result, labels, masks, n_bootstrap=100)
        assert "ci_lower" in ci
        assert "ci_upper" in ci

    def test_full_diagnostic_report_minimal(self):
        """Full diagnostic report with minimal data."""
        graph = _make_tiny_graph(n_power=10, n_water=8, n_telecom=5)
        preds = _get_predictions(graph)

        cal = HeteroConformalCalibrator(alpha=0.1)
        cal_masks = {nt: m["cal"] for nt, m in graph.node_masks.items()}
        test_masks = {nt: m["test"] for nt, m in graph.node_masks.items()}
        cal.calibrate(preds, graph.node_labels, cal_masks)
        result = cal.predict(preds, test_masks)

        report = full_diagnostic_report(
            result, graph.node_labels, test_masks,
            edge_index=graph.edge_index, num_nodes=graph.num_nodes,
            n_bootstrap=50,
        )
        assert "marginal_coverage" in report
        assert "coverage_ci" in report


class TestModelEdgeCases:
    """HeteroGNN model edge cases."""

    def test_model_no_edges(self):
        """Model handles graph with no edges."""
        graph = _make_tiny_graph(n_power=5, n_water=3, n_telecom=2)
        for key in list(graph.edge_index.keys()):
            graph.edge_index[key] = np.zeros((2, 0), dtype=np.int64)
        preds = _get_predictions(graph)
        for nt in preds:
            assert preds[nt].shape[0] == graph.num_nodes[nt]

    def test_model_self_loops_only(self):
        """Model handles graph with only self-loops."""
        graph = _make_tiny_graph(n_power=5, n_water=3, n_telecom=2)
        for key in list(graph.edge_index.keys()):
            src_t, _, dst_t = key
            if src_t == dst_t:
                n = graph.num_nodes[src_t]
                idx = np.arange(n, dtype=np.int64)
                graph.edge_index[key] = np.stack([idx, idx])
            else:
                graph.edge_index[key] = np.zeros((2, 0), dtype=np.int64)
        preds = _get_predictions(graph)
        for nt in preds:
            assert np.all(np.isfinite(preds[nt]))

    def test_model_dropout_zero(self):
        """Model with dropout=0 is fully deterministic."""
        graph = _make_tiny_graph()
        torch.manual_seed(42)
        in_dims = {nt: f.shape[1] for nt, f in graph.node_features.items()}
        model = HeteroGNN(in_dims=in_dims, hidden_dim=16, num_layers=2,
                          edge_types=list(graph.edge_index.keys()), dropout=0.0)
        model.eval()
        x = {nt: torch.tensor(f) for nt, f in graph.node_features.items()}
        ei = {et: torch.tensor(e, dtype=torch.long) for et, e in graph.edge_index.items()}
        with torch.no_grad():
            p1 = model(x, ei, graph.num_nodes)
            p2 = model(x, ei, graph.num_nodes)
        for nt in p1:
            assert torch.allclose(p1[nt], p2[nt])


class TestLearnableLambdaEdgeCases:
    """LearnableLambdaCalibrator edge cases."""

    def test_very_small_cal_set(self):
        """Lambda calibrator with < 10 cal nodes defaults to lambda=0."""
        cal = LearnableLambdaCalibrator(alpha=0.1)
        preds = {"power": np.random.randn(5).astype(np.float32)}
        labels = {"power": np.random.randn(5).astype(np.float32)}
        cal_masks = {"power": np.array([True]*3 + [False]*2)}
        train_masks = {"power": np.array([True]*2 + [False]*3)}
        edge_index = {("power", "feeds", "power"): np.array([[0, 1], [1, 2]], dtype=np.int64)}

        q = cal.calibrate(preds, labels, cal_masks, train_masks, edge_index, {"power": 5})
        assert np.isfinite(q["power"])
        # With < 10 cal nodes, lambda should default to 0
        assert cal.optimal_lambdas.get("power", 0.0) == 0.0


class TestAttentionCalibratorEdgeCases:
    """AttentionCalibrator edge cases."""

    def test_attention_varying_feature_dims(self):
        """AttentionCalibrator handles different feature dims per type."""
        graph = HeteroInfraGraph()
        graph.node_features = {
            "power": np.random.randn(10, 4).astype(np.float32),
            "water": np.random.randn(8, 6).astype(np.float32),
        }
        graph.node_labels = {
            "power": np.random.randn(10).astype(np.float32),
            "water": np.random.randn(8).astype(np.float32),
        }
        graph.node_masks = {
            "power": {"train": np.array([True]*5 + [False]*5),
                      "cal": np.array([False]*5 + [True]*3 + [False]*2),
                      "test": np.array([False]*8 + [True]*2)},
            "water": {"train": np.array([True]*4 + [False]*4),
                      "cal": np.array([False]*4 + [True]*2 + [False]*2),
                      "test": np.array([False]*6 + [True]*2)},
        }
        graph.edge_index = {
            ("power", "feeds", "power"): np.array([[0, 1, 2], [1, 2, 3]], dtype=np.int64),
            ("water", "pipes", "water"): np.array([[0, 1], [1, 2]], dtype=np.int64),
            ("power", "colocated", "water"): np.array([[0], [0]], dtype=np.int64),
            ("water", "colocated", "telecom"): np.zeros((2, 0), dtype=np.int64),
            ("power", "colocated", "telecom"): np.zeros((2, 0), dtype=np.int64),
            ("telecom", "connects", "telecom"): np.zeros((2, 0), dtype=np.int64),
        }

        preds = {nt: np.random.randn(n).astype(np.float32)
                 for nt, n in graph.num_nodes.items()}

        attn = AttentionCalibrator(alpha=0.1, attn_epochs=5)
        attn.calibrate(
            graph.node_features, preds, graph.node_labels,
            {nt: m["cal"] for nt, m in graph.node_masks.items()},
            {nt: m["train"] for nt, m in graph.node_masks.items()},
            graph.edge_index, graph.num_nodes,
        )
        result = attn.predict(preds)
        for nt in result.lower:
            assert np.all(np.isfinite(result.lower[nt]))
