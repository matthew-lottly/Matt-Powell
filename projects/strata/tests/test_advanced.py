"""Tests for advanced calibrators, ensemble, meta-calibrator, and diagnostics."""

import numpy as np
import pytest
import torch

from hetero_conformal.graph import generate_synthetic_infrastructure
from hetero_conformal.conformal import ConformalResult, PropagationAwareCalibrator
from hetero_conformal.advanced_calibrators import (
    LearnableLambdaCalibrator,
    AttentionCalibrator,
    CQRCalibrator,
    QuantileHead,
    pinball_loss,
)
from hetero_conformal.meta_calibrator import MetaCalibrator
from hetero_conformal.ensemble import EnsembleHeteroGNN, EnsembleCalibrator
from hetero_conformal.experiment import ExperimentConfig, train_model, evaluate
from hetero_conformal.model import HeteroGNN
from hetero_conformal.diagnostics import (
    full_diagnostic_report,
    nonexchangeability_test,
    paired_wilcoxon_test,
    multi_method_friedman_test,
)
from hetero_conformal.metrics import (
    marginal_coverage,
    type_conditional_coverage,
    mean_interval_width,
    calibration_error,
)


# ── shared fixtures ──────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def trained_setup():
    """Train a single model and return all artifacts needed for calibrator tests."""
    seed = 42
    graph = generate_synthetic_infrastructure(
        n_power=100, n_water=80, n_telecom=60, seed=seed,
    )
    cfg = ExperimentConfig(
        n_power=100, n_water=80, n_telecom=60,
        seed=seed, epochs=50, patience=10,
        hidden_dim=32, num_layers=2,
    )
    torch.manual_seed(seed)
    np.random.seed(seed)

    in_dims = {nt: f.shape[1] for nt, f in graph.node_features.items()}
    edge_types = list(graph.edge_index.keys())
    model = HeteroGNN(
        in_dims=in_dims, hidden_dim=cfg.hidden_dim,
        num_layers=cfg.num_layers, edge_types=edge_types, dropout=cfg.dropout,
    )
    model, _, _ = train_model(model, graph, cfg)
    predictions = evaluate(model, graph, cfg)
    cal_masks = {nt: graph.node_masks[nt]["cal"] for nt in graph.node_masks}
    test_masks = {nt: graph.node_masks[nt]["test"] for nt in graph.node_masks}
    train_masks = {nt: graph.node_masks[nt]["train"] for nt in graph.node_masks}

    # Extract hidden representations for CQR
    model.eval()
    import torch.nn.functional as F
    x_t = {nt: torch.tensor(graph.node_features[nt], dtype=torch.float32)
           for nt in graph.node_features}
    ei_t = {et: torch.tensor(ei, dtype=torch.long)
            for et, ei in graph.edge_index.items()}
    with torch.no_grad():
        h = {}
        for nt in x_t:
            h[nt] = F.relu(model.input_proj[nt](x_t[nt]))
        for layer in model.mp_layers:
            h_new = layer(h, ei_t, graph.num_nodes)
            for nt in h:
                h_new[nt] = F.relu(h_new[nt]) + h[nt]
            h = h_new

    return {
        "model": model,
        "graph": graph,
        "cfg": cfg,
        "predictions": predictions,
        "cal_masks": cal_masks,
        "test_masks": test_masks,
        "train_masks": train_masks,
        "hidden": h,
    }


# ── LearnableLambdaCalibrator tests ──────────────────────────────────────────

class TestLearnableLambdaCalibrator:
    def test_calibrate_returns_quantiles(self, trained_setup):
        s = trained_setup
        cal = LearnableLambdaCalibrator(alpha=0.1)
        q = cal.calibrate(
            s["predictions"], s["graph"].node_labels, s["cal_masks"],
            s["train_masks"], s["graph"].edge_index, s["graph"].num_nodes,
        )
        assert set(q.keys()) == {"power", "water", "telecom"}
        for v in q.values():
            assert np.isfinite(v) and v > 0

    def test_per_type_lambdas_selected(self, trained_setup):
        s = trained_setup
        cal = LearnableLambdaCalibrator(alpha=0.1)
        cal.calibrate(
            s["predictions"], s["graph"].node_labels, s["cal_masks"],
            s["train_masks"], s["graph"].edge_index, s["graph"].num_nodes,
        )
        assert set(cal.optimal_lambdas.keys()) == {"power", "water", "telecom"}
        for lam in cal.optimal_lambdas.values():
            assert 0.0 <= lam <= 1.0

    def test_predict_before_calibrate_raises(self, trained_setup):
        cal = LearnableLambdaCalibrator(alpha=0.1)
        with pytest.raises(RuntimeError, match="calibrate"):
            cal.predict(trained_setup["predictions"], trained_setup["test_masks"])

    def test_coverage_reasonable(self, trained_setup):
        s = trained_setup
        cal = LearnableLambdaCalibrator(alpha=0.1)
        cal.calibrate(
            s["predictions"], s["graph"].node_labels, s["cal_masks"],
            s["train_masks"], s["graph"].edge_index, s["graph"].num_nodes,
        )
        result = cal.predict(s["predictions"], s["test_masks"])
        cov = marginal_coverage(result, s["graph"].node_labels, s["test_masks"])
        assert cov >= 0.75, f"Coverage too low: {cov:.3f}"

    def test_intervals_contain_predictions(self, trained_setup):
        s = trained_setup
        cal = LearnableLambdaCalibrator(alpha=0.1)
        cal.calibrate(
            s["predictions"], s["graph"].node_labels, s["cal_masks"],
            s["train_masks"], s["graph"].edge_index, s["graph"].num_nodes,
        )
        result = cal.predict(s["predictions"], s["test_masks"])
        for nt in result.lower:
            assert np.all(result.point_pred[nt] >= result.lower[nt])
            assert np.all(result.point_pred[nt] <= result.upper[nt])


# ── AttentionCalibrator tests ────────────────────────────────────────────────

class TestAttentionCalibrator:
    def test_calibrate_and_predict(self, trained_setup):
        s = trained_setup
        cal = AttentionCalibrator(alpha=0.1, attn_epochs=10)
        cal.calibrate(
            s["graph"].node_features, s["predictions"], s["graph"].node_labels,
            s["cal_masks"], s["train_masks"], s["graph"].edge_index, s["graph"].num_nodes,
        )
        result = cal.predict(s["predictions"], s["test_masks"])
        assert set(result.lower.keys()) == {"power", "water", "telecom"}
        for nt in result.lower:
            assert len(result.lower[nt]) > 0
            assert np.all(np.isfinite(result.lower[nt]))
            assert np.all(np.isfinite(result.upper[nt]))

    def test_coverage_reasonable(self, trained_setup):
        s = trained_setup
        cal = AttentionCalibrator(alpha=0.1, attn_epochs=20)
        cal.calibrate(
            s["graph"].node_features, s["predictions"], s["graph"].node_labels,
            s["cal_masks"], s["train_masks"], s["graph"].edge_index, s["graph"].num_nodes,
        )
        result = cal.predict(s["predictions"], s["test_masks"])
        cov = marginal_coverage(result, s["graph"].node_labels, s["test_masks"])
        assert cov >= 0.75, f"Coverage too low: {cov:.3f}"


# ── CQRCalibrator tests ─────────────────────────────────────────────────────

class TestCQRCalibrator:
    def test_quantile_head_output_shape(self):
        head = QuantileHead(hidden_dim=32)
        h = torch.randn(10, 32)
        lo, hi = head(h)
        assert lo.shape == (10,)
        assert hi.shape == (10,)

    def test_quantile_head_ordering(self):
        """hi should always be >= lo due to softplus parameterization."""
        head = QuantileHead(hidden_dim=32)
        h = torch.randn(100, 32)
        lo, hi = head(h)
        assert torch.all(hi >= lo), "Upper quantile must be >= lower quantile"

    def test_pinball_loss_nonnegative(self):
        pred = torch.randn(50)
        target = torch.randn(50)
        loss = pinball_loss(pred, target, 0.1)
        assert loss.item() >= 0

    def test_pinball_loss_zero_at_perfect(self):
        target = torch.randn(50)
        loss = pinball_loss(target, target, 0.5)
        assert loss.item() < 1e-6

    def test_train_quantile_heads(self, trained_setup):
        s = trained_setup
        cqr = CQRCalibrator(alpha=0.1, quantile_epochs=20, verbose=False)
        cqr.train_quantile_heads(
            s["hidden"], s["graph"].node_labels,
            s["train_masks"], s["cfg"].hidden_dim,
        )
        for nt in s["hidden"]:
            assert nt in cqr._q_lo
            assert nt in cqr._q_hi
            assert np.all(cqr._q_hi[nt] >= cqr._q_lo[nt])

    def test_cqr_calibrate_and_predict(self, trained_setup):
        s = trained_setup
        cqr = CQRCalibrator(alpha=0.1, quantile_epochs=20, verbose=False)
        cqr.train_quantile_heads(
            s["hidden"], s["graph"].node_labels,
            s["train_masks"], s["cfg"].hidden_dim,
        )
        cqr.calibrate(
            s["predictions"], s["graph"].node_labels, s["cal_masks"],
            s["train_masks"], s["graph"].edge_index, s["graph"].num_nodes,
        )
        result = cqr.predict(s["predictions"], s["test_masks"])
        assert set(result.lower.keys()) == {"power", "water", "telecom"}
        for nt in result.lower:
            assert len(result.lower[nt]) > 0
            assert np.all(np.isfinite(result.lower[nt]))

    def test_cqr_coverage_reasonable(self, trained_setup):
        s = trained_setup
        cqr = CQRCalibrator(alpha=0.1, quantile_epochs=50, verbose=False)
        cqr.train_quantile_heads(
            s["hidden"], s["graph"].node_labels,
            s["train_masks"], s["cfg"].hidden_dim,
        )
        cqr.calibrate(
            s["predictions"], s["graph"].node_labels, s["cal_masks"],
            s["train_masks"], s["graph"].edge_index, s["graph"].num_nodes,
        )
        result = cqr.predict(s["predictions"], s["test_masks"])
        cov = marginal_coverage(result, s["graph"].node_labels, s["test_masks"])
        assert cov >= 0.75, f"CQR coverage too low: {cov:.3f}"

    def test_loss_traces_recorded(self, trained_setup):
        s = trained_setup
        cqr = CQRCalibrator(alpha=0.1, quantile_epochs=10, verbose=False)
        cqr.train_quantile_heads(
            s["hidden"], s["graph"].node_labels,
            s["train_masks"], s["cfg"].hidden_dim,
        )
        for nt in s["hidden"]:
            assert nt in cqr._quantile_losses
            assert len(cqr._quantile_losses[nt]) == 10


# ── MetaCalibrator tests ─────────────────────────────────────────────────────

class TestMetaCalibrator:
    def test_calibrate_and_predict(self, trained_setup):
        s = trained_setup
        meta = MetaCalibrator(alpha=0.1)
        meta.calibrate(
            s["graph"].node_features, s["predictions"], s["graph"].node_labels,
            s["cal_masks"], s["train_masks"], s["graph"].edge_index, s["graph"].num_nodes,
        )
        result = meta.predict(s["predictions"], s["test_masks"])
        assert set(result.lower.keys()) == {"power", "water", "telecom"}
        for nt in result.lower:
            assert np.all(result.point_pred[nt] >= result.lower[nt])
            assert np.all(result.point_pred[nt] <= result.upper[nt])

    def test_coverage_reasonable(self, trained_setup):
        s = trained_setup
        meta = MetaCalibrator(alpha=0.1)
        meta.calibrate(
            s["graph"].node_features, s["predictions"], s["graph"].node_labels,
            s["cal_masks"], s["train_masks"], s["graph"].edge_index, s["graph"].num_nodes,
        )
        result = meta.predict(s["predictions"], s["test_masks"])
        cov = marginal_coverage(result, s["graph"].node_labels, s["test_masks"])
        assert cov >= 0.75, f"Meta-calibrator coverage too low: {cov:.3f}"


# ── EnsembleCalibrator tests ─────────────────────────────────────────────────

class TestEnsembleCalibrator:
    def test_ensemble_train_and_predict(self, trained_setup):
        s = trained_setup
        cfg = ExperimentConfig(
            n_power=100, n_water=80, n_telecom=60,
            seed=42, epochs=20, patience=5,
            hidden_dim=32, num_layers=2,
        )
        ens = EnsembleHeteroGNN(n_members=2)
        ens.build_and_train(s["graph"], cfg, base_seed=42)
        mean_preds, var_preds = ens.predict(s["graph"])
        for nt in mean_preds:
            assert np.all(np.isfinite(mean_preds[nt]))
            assert np.all(var_preds[nt] >= 0)

    def test_ensemble_calibrator_coverage(self, trained_setup):
        s = trained_setup
        cfg = ExperimentConfig(
            n_power=100, n_water=80, n_telecom=60,
            seed=42, epochs=20, patience=5,
            hidden_dim=32, num_layers=2,
        )
        ens = EnsembleHeteroGNN(n_members=2)
        ens.build_and_train(s["graph"], cfg, base_seed=42)
        mean_preds, var_preds = ens.predict(s["graph"])

        ens_cal = EnsembleCalibrator(alpha=0.1)
        ens_cal.calibrate(mean_preds, var_preds, s["graph"].node_labels, s["cal_masks"])
        result = ens_cal.predict(mean_preds, s["test_masks"])
        cov = marginal_coverage(result, s["graph"].node_labels, s["test_masks"])
        assert cov >= 0.70, f"Ensemble coverage too low: {cov:.3f}"


# ── PropagationAwareCalibrator floor_sigma tests ─────────────────────────────

class TestFloorSigma:
    def test_floor_changes_results(self, trained_setup):
        """floor_sigma > 0 should change sigma values for nodes with low neighbor residuals."""
        s = trained_setup
        cal_no_floor = PropagationAwareCalibrator(alpha=0.1, neighborhood_weight=0.3)
        cal_no_floor.neighbor_agg = "median"
        cal_no_floor.floor_sigma = 0.0
        cal_no_floor.calibrate_with_propagation(
            s["predictions"], s["graph"].node_labels, s["cal_masks"],
            s["train_masks"], s["graph"].edge_index, s["graph"].num_nodes,
        )

        cal_floor = PropagationAwareCalibrator(alpha=0.1, neighborhood_weight=0.3)
        cal_floor.neighbor_agg = "median"
        cal_floor.floor_sigma = 0.5  # large enough to affect some nodes
        cal_floor.calibrate_with_propagation(
            s["predictions"], s["graph"].node_labels, s["cal_masks"],
            s["train_masks"], s["graph"].edge_index, s["graph"].num_nodes,
        )

        # Sigma with floor should be >= sigma without (and differ for some nodes)
        differences_found = False
        for nt in cal_no_floor._sigma:
            if np.any(cal_floor._sigma[nt] > cal_no_floor._sigma[nt] + 1e-6):
                differences_found = True
        assert differences_found, "floor_sigma should create differences in sigma values"


# ── Diagnostics tests ────────────────────────────────────────────────────────

class TestDiagnostics:
    def test_nonexchangeability_test(self):
        rng = np.random.default_rng(42)
        scores = rng.standard_normal(100)
        result = nonexchangeability_test(scores)
        assert "statistic" in result
        assert "p_value" in result

    def test_paired_wilcoxon(self):
        rng = np.random.default_rng(42)
        a = rng.uniform(0.85, 0.95, size=20)
        b = rng.uniform(0.85, 0.95, size=20)
        result = paired_wilcoxon_test(a.tolist(), b.tolist())
        assert "statistic" in result
        assert "p_value" in result

    def test_friedman_test(self):
        rng = np.random.default_rng(42)
        data = {
            "method_a": rng.uniform(0.85, 0.95, size=10).tolist(),
            "method_b": rng.uniform(0.85, 0.95, size=10).tolist(),
            "method_c": rng.uniform(0.85, 0.95, size=10).tolist(),
        }
        result = multi_method_friedman_test(data)
        assert "statistic" in result
        assert "p_value" in result

    def test_full_diagnostic_report(self, trained_setup):
        s = trained_setup
        cal = PropagationAwareCalibrator(alpha=0.1, neighborhood_weight=0.3)
        cal.calibrate_with_propagation(
            s["predictions"], s["graph"].node_labels, s["cal_masks"],
            s["train_masks"], s["graph"].edge_index, s["graph"].num_nodes,
        )
        result = cal.predict(s["predictions"], s["test_masks"])
        sigma = {nt: cal._sigma[nt] for nt in s["test_masks"]}

        report = full_diagnostic_report(
            result, s["graph"].node_labels, s["test_masks"],
            sigma=sigma, edge_index=s["graph"].edge_index,
            num_nodes=s["graph"].num_nodes,
        )
        assert "marginal_coverage" in report
        assert "type_coverage" in report
        assert "mean_width" in report
        assert "ece" in report
        assert "coverage_ci" in report


# ── Integration test: full pipeline ──────────────────────────────────────────

class TestFullPipeline:
    def test_end_to_end_experiment(self):
        """Run a complete experiment and verify all outputs."""
        from hetero_conformal.experiment import run_experiment
        cfg = ExperimentConfig(
            n_power=60, n_water=40, n_telecom=30,
            seed=99, epochs=30, patience=5,
            hidden_dim=16, num_layers=2,
        )
        result = run_experiment(cfg)
        assert result.marginal_cov >= 0.5
        assert result.mean_width > 0
        assert 0 <= result.ece <= 1
        assert len(result.rmse) == 3
        for nt in ["power", "water", "telecom"]:
            assert nt in result.rmse
            assert result.rmse[nt] > 0
