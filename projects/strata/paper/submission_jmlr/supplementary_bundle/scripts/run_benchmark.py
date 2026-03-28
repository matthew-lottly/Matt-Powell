"""Full benchmark: 20-seed comparison, CSV output, tables, plots, and maps.

Usage:
    cd projects/strata
    python scripts/run_benchmark.py

Part of the STRATA project.
"""

from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

import numpy as np

# Ensure src is importable even without editable install
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from hetero_conformal.experiment import ExperimentConfig, run_experiment
from hetero_conformal.graph import generate_synthetic_infrastructure

OUT_DIR = Path(__file__).resolve().parent.parent / "outputs"
OUT_DIR.mkdir(exist_ok=True)

SEED_COUNT = int(os.environ.get("SEED_COUNT", "20"))
SEEDS = list(range(SEED_COUNT))
ALPHAS = [0.05, 0.10, 0.15, 0.20]
LAMBDAS = [0.0, 0.1, 0.3, 0.5, 1.0]
NODE_TYPES = ["power", "water", "telecom"]


# ── helpers ──────────────────────────────────────────────────────────────────

def _cfg(seed: int, alpha: float = 0.1, lam: float = 0.3, prop: bool = True) -> ExperimentConfig:
    return ExperimentConfig(
        seed=seed, alpha=alpha,
        neighborhood_weight=lam,
        use_propagation_aware=prop,
        epochs=200, patience=20,
    )


def _build_row(
    seed: int,
    method: str,
    result,
    predictions: dict,
    graph,
    test_masks: dict,
) -> dict:
    """Build a standardised metrics row for any calibrator variant."""
    from hetero_conformal.metrics import (
        rmse_per_type, marginal_coverage, type_conditional_coverage,
        prediction_set_efficiency, mean_interval_width, calibration_error,
    )
    m_cov = marginal_coverage(result, graph.node_labels, test_masks)
    t_cov = type_conditional_coverage(result, graph.node_labels, test_masks)
    widths = prediction_set_efficiency(result)
    m_width = mean_interval_width(result)
    ece = calibration_error(result, graph.node_labels, test_masks)
    rmse = rmse_per_type(predictions, graph.node_labels, test_masks)
    row: dict = {"seed": seed, "method": method, "marginal_cov": m_cov,
                 "mean_width": m_width, "ece": ece}
    for nt in NODE_TYPES:
        row[f"cov_{nt}"] = t_cov.get(nt, float("nan"))
        row[f"width_{nt}"] = widths.get(nt, float("nan"))
        row[f"rmse_{nt}"] = rmse.get(nt, float("nan"))
    return row


def _train_model_for_seed(seed: int, alpha: float = 0.1):
    """Train a single model for a seed and return (model, graph, predictions, masks)."""
    import torch
    from hetero_conformal.experiment import train_model, evaluate
    from hetero_conformal.model import HeteroGNN

    cfg = _cfg(seed, alpha=alpha, lam=0.0, prop=True)
    torch.manual_seed(cfg.seed)
    np.random.seed(cfg.seed)
    graph = generate_synthetic_infrastructure(
        n_power=cfg.n_power, n_water=cfg.n_water, n_telecom=cfg.n_telecom,
        feature_dim=cfg.feature_dim, coupling_prob=cfg.coupling_prob,
        coupling_radius=cfg.coupling_radius, seed=cfg.seed,
    )
    in_dims = {nt: f.shape[1] for nt, f in graph.node_features.items()}
    edge_types = list(graph.edge_index.keys())
    model = HeteroGNN(
        in_dims=in_dims, hidden_dim=cfg.hidden_dim,
        num_layers=cfg.num_layers, edge_types=edge_types,
        dropout=cfg.dropout,
    ).to(cfg.device)
    model, _, _ = train_model(model, graph, cfg)
    predictions = evaluate(model, graph, cfg)
    cal_masks = {nt: graph.node_masks[nt]["cal"] for nt in graph.node_masks}
    test_masks = {nt: graph.node_masks[nt]["test"] for nt in graph.node_masks}
    train_masks = {nt: graph.node_masks[nt]["train"] for nt in graph.node_masks}
    return model, graph, cfg, predictions, cal_masks, test_masks, train_masks


# ── 1. Baseline comparison (10 seeds) ───────────────────────────────────────

def run_baseline_sweep() -> list[dict]:
    rows: list[dict] = []
    for seed in SEEDS:
        # compare mondrian CP, CHMP (mean), CHMP (median), CHMP (median+floor)
        variants = [
            ("mondrian_cp", False, 0.0, None, 0.0),
            ("chmp_mean", True, 0.3, "mean", 0.0),
            ("chmp_median", True, 0.3, "median", 0.0),
            ("chmp_median_floor", True, 0.3, "median", 0.1),
        ]

        # build per-seed config, data, and train once
        cfg_base = _cfg(seed, alpha=0.1, lam=0.0, prop=True)
        graph = generate_synthetic_infrastructure(
            n_power=cfg_base.n_power, n_water=cfg_base.n_water, n_telecom=cfg_base.n_telecom,
            feature_dim=cfg_base.feature_dim, coupling_prob=cfg_base.coupling_prob,
            coupling_radius=cfg_base.coupling_radius, seed=cfg_base.seed,
        )

        # local imports to avoid top-level changes
        from hetero_conformal.experiment import train_model, evaluate
        from hetero_conformal.model import HeteroGNN
        from hetero_conformal.conformal import PropagationAwareCalibrator, HeteroConformalCalibrator
        from hetero_conformal.metrics import (
            rmse_per_type, marginal_coverage, type_conditional_coverage,
            prediction_set_efficiency, mean_interval_width, calibration_error,
        )

        in_dims = {nt: f.shape[1] for nt, f in graph.node_features.items()}
        edge_types = list(graph.edge_index.keys())
        model = HeteroGNN(
            in_dims=in_dims,
            hidden_dim=cfg_base.hidden_dim,
            num_layers=cfg_base.num_layers,
            edge_types=edge_types,
            dropout=cfg_base.dropout,
        ).to(cfg_base.device)

        model, _, _ = train_model(model, graph, cfg_base)
        predictions = evaluate(model, graph, cfg_base)

        cal_masks = {ntype: graph.node_masks[ntype]["cal"] for ntype in graph.node_masks}
        test_masks = {ntype: graph.node_masks[ntype]["test"] for ntype in graph.node_masks}
        train_masks = {ntype: graph.node_masks[ntype]["train"] for ntype in graph.node_masks}

        for method, prop, lam, agg, floor in variants:
            if prop and lam > 0:
                calibrator = PropagationAwareCalibrator(alpha=cfg_base.alpha, neighborhood_weight=lam)
                calibrator.neighbor_agg = getattr(cfg_base, "neighbor_agg", "mean") if agg is None else agg
                calibrator.trimmed_frac = getattr(cfg_base, "trimmed_frac", 0.0)
                calibrator.floor_sigma = getattr(cfg_base, "floor_sigma", 0.0) if floor is None else floor
                _ = calibrator.calibrate_with_propagation(
                    predictions, graph.node_labels, cal_masks, train_masks,
                    graph.edge_index, graph.num_nodes,
                )
            else:
                calibrator = HeteroConformalCalibrator(alpha=cfg_base.alpha)
                _ = calibrator.calibrate(predictions, graph.node_labels, cal_masks)

            conf_result = calibrator.predict(predictions, test_masks)

            # compute metrics
            rmse = rmse_per_type(predictions, graph.node_labels, test_masks)
            m_cov = marginal_coverage(conf_result, graph.node_labels, test_masks)
            t_cov = type_conditional_coverage(conf_result, graph.node_labels, test_masks)
            widths = prediction_set_efficiency(conf_result)
            m_width = mean_interval_width(conf_result)
            ece = calibration_error(conf_result, graph.node_labels, test_masks)

            row = {
                "seed": seed,
                "method": method,
                "marginal_cov": m_cov,
                "mean_width": m_width,
                "ece": ece,
            }
            for nt in NODE_TYPES:
                row[f"cov_{nt}"] = t_cov.get(nt, float("nan"))
                row[f"width_{nt}"] = widths.get(nt, float("nan"))
                row[f"rmse_{nt}"] = rmse.get(nt, float("nan"))
            rows.append(row)
            print(f"  seed={seed} {method}: cov={m_cov:.4f} width={m_width:.4f}")
    return rows


# ── 2. Lambda sensitivity (10 seeds × 5 lambdas) ───────────────────────────

def run_lambda_sweep() -> list[dict]:
    rows: list[dict] = []
    # Train once per seed, then re-run only the calibrator for each lambda
    for seed in SEEDS:
        # build per-seed config and data
        cfg_base = _cfg(seed, alpha=0.1, lam=0.0, prop=True)
        graph = generate_synthetic_infrastructure(
            n_power=cfg_base.n_power, n_water=cfg_base.n_water, n_telecom=cfg_base.n_telecom,
            feature_dim=cfg_base.feature_dim, coupling_prob=cfg_base.coupling_prob,
            coupling_radius=cfg_base.coupling_radius, seed=cfg_base.seed,
        )

        # local imports to avoid top-level changes
        from hetero_conformal.experiment import train_model, evaluate
        from hetero_conformal.model import HeteroGNN
        from hetero_conformal.conformal import PropagationAwareCalibrator, HeteroConformalCalibrator
        from hetero_conformal.metrics import (
            rmse_per_type, marginal_coverage, type_conditional_coverage,
            prediction_set_efficiency, mean_interval_width, calibration_error,
        )

        # build and train model once
        in_dims = {nt: f.shape[1] for nt, f in graph.node_features.items()}
        edge_types = list(graph.edge_index.keys())
        model = HeteroGNN(
            in_dims=in_dims,
            hidden_dim=cfg_base.hidden_dim,
            num_layers=cfg_base.num_layers,
            edge_types=edge_types,
            dropout=cfg_base.dropout,
        ).to(cfg_base.device)

        model, _, _ = train_model(model, graph, cfg_base)
        predictions = evaluate(model, graph, cfg_base)

        cal_masks = {ntype: graph.node_masks[ntype]["cal"] for ntype in graph.node_masks}
        test_masks = {ntype: graph.node_masks[ntype]["test"] for ntype in graph.node_masks}
        train_masks = {ntype: graph.node_masks[ntype]["train"] for ntype in graph.node_masks}

        for lam in LAMBDAS:
            if lam > 0:
                calibrator = PropagationAwareCalibrator(alpha=cfg_base.alpha, neighborhood_weight=lam)
                calibrator.neighbor_agg = getattr(cfg_base, "neighbor_agg", "mean")
                calibrator.trimmed_frac = getattr(cfg_base, "trimmed_frac", 0.0)
                calibrator.floor_sigma = getattr(cfg_base, "floor_sigma", 0.0)
                _ = calibrator.calibrate_with_propagation(
                    predictions, graph.node_labels, cal_masks, train_masks,
                    graph.edge_index, graph.num_nodes,
                )
            else:
                calibrator = HeteroConformalCalibrator(alpha=cfg_base.alpha)
                _ = calibrator.calibrate(predictions, graph.node_labels, cal_masks)

            conf_result = calibrator.predict(predictions, test_masks)

            # compute metrics
            rmse = rmse_per_type(predictions, graph.node_labels, test_masks)
            m_cov = marginal_coverage(conf_result, graph.node_labels, test_masks)
            t_cov = type_conditional_coverage(conf_result, graph.node_labels, test_masks)
            widths = prediction_set_efficiency(conf_result)
            m_width = mean_interval_width(conf_result)
            ece = calibration_error(conf_result, graph.node_labels, test_masks)

            row = {
                "seed": seed, "lambda": lam,
                "marginal_cov": m_cov,
                "mean_width": m_width,
                "ece": ece,
            }
            for nt in NODE_TYPES:
                row[f"cov_{nt}"] = t_cov.get(nt, float("nan"))
                row[f"width_{nt}"] = widths.get(nt, float("nan"))
            rows.append(row)

    return rows


# ── 3. Alpha sweep (10 seeds × 4 alphas, CHMP only) ────────────────────────

def run_alpha_sweep() -> list[dict]:
    rows: list[dict] = []
    for seed in SEEDS:
        # train once per seed, then recalibrate for each alpha
        cfg_base = _cfg(seed, alpha=0.1, lam=0.3, prop=True)
        graph = generate_synthetic_infrastructure(
            n_power=cfg_base.n_power, n_water=cfg_base.n_water, n_telecom=cfg_base.n_telecom,
            feature_dim=cfg_base.feature_dim, coupling_prob=cfg_base.coupling_prob,
            coupling_radius=cfg_base.coupling_radius, seed=cfg_base.seed,
        )

        from hetero_conformal.experiment import train_model, evaluate
        from hetero_conformal.model import HeteroGNN
        from hetero_conformal.conformal import PropagationAwareCalibrator
        from hetero_conformal.metrics import (
            rmse_per_type, marginal_coverage, type_conditional_coverage,
            prediction_set_efficiency, mean_interval_width, calibration_error,
        )

        in_dims = {nt: f.shape[1] for nt, f in graph.node_features.items()}
        edge_types = list(graph.edge_index.keys())
        model = HeteroGNN(
            in_dims=in_dims,
            hidden_dim=cfg_base.hidden_dim,
            num_layers=cfg_base.num_layers,
            edge_types=edge_types,
            dropout=cfg_base.dropout,
        ).to(cfg_base.device)

        model, _, _ = train_model(model, graph, cfg_base)
        predictions = evaluate(model, graph, cfg_base)

        cal_masks = {ntype: graph.node_masks[ntype]["cal"] for ntype in graph.node_masks}
        test_masks = {ntype: graph.node_masks[ntype]["test"] for ntype in graph.node_masks}
        train_masks = {ntype: graph.node_masks[ntype]["train"] for ntype in graph.node_masks}

        for alpha in ALPHAS:
            calibrator = PropagationAwareCalibrator(alpha=alpha, neighborhood_weight=0.3)
            calibrator.neighbor_agg = getattr(cfg_base, "neighbor_agg", "mean")
            calibrator.trimmed_frac = getattr(cfg_base, "trimmed_frac", 0.0)
            calibrator.floor_sigma = getattr(cfg_base, "floor_sigma", 0.0)
            _ = calibrator.calibrate_with_propagation(
                predictions, graph.node_labels, cal_masks, train_masks,
                graph.edge_index, graph.num_nodes,
            )

            conf_result = calibrator.predict(predictions, test_masks)

            # compute metrics
            rmse = rmse_per_type(predictions, graph.node_labels, test_masks)
            m_cov = marginal_coverage(conf_result, graph.node_labels, test_masks)
            t_cov = type_conditional_coverage(conf_result, graph.node_labels, test_masks)
            widths = prediction_set_efficiency(conf_result)
            m_width = mean_interval_width(conf_result)
            ece = calibration_error(conf_result, graph.node_labels, test_masks)

            row = {
                "seed": seed, "alpha": alpha,
                "marginal_cov": m_cov,
                "mean_width": m_width,
                "ece": ece,
            }
            for nt in NODE_TYPES:
                row[f"cov_{nt}"] = t_cov.get(nt, float("nan"))
                row[f"width_{nt}"] = widths.get(nt, float("nan"))
            rows.append(row)
    return rows


# ── 4. Advanced calibrator comparison ───────────────────────────────────────

def run_advanced_sweep() -> list[dict]:
    """Run novel calibrator variants: meta-calibrator, learnable λ,
    attention-based, and CQR across all seeds.
    """
    import torch
    import torch.nn.functional as F
    from hetero_conformal.meta_calibrator import MetaCalibrator
    from hetero_conformal.advanced_calibrators import (
        LearnableLambdaCalibrator,
        AttentionCalibrator,
        CQRCalibrator,
    )
    from hetero_conformal.metrics import (
        marginal_coverage, type_conditional_coverage,
        prediction_set_efficiency, mean_interval_width, calibration_error,
    )

    rows: list[dict] = []
    for seed in SEEDS:
        model, graph, cfg, predictions, cal_masks, test_masks, train_masks = \
            _train_model_for_seed(seed)

        # ─── MetaCalibrator (learned σ_i) ───
        try:
            meta_cal = MetaCalibrator(alpha=cfg.alpha)
            meta_cal.calibrate(
                graph.node_features, predictions, graph.node_labels,
                cal_masks, train_masks, graph.edge_index, graph.num_nodes,
            )
            result = meta_cal.predict(predictions, test_masks)
            rows.append(_build_row(seed, "meta_learned", result, predictions, graph, test_masks))
            print(f"  seed={seed} meta_learned: cov={marginal_coverage(result, graph.node_labels, test_masks):.4f}")
        except Exception as e:
            print(f"  WARN: meta_learned seed={seed} failed: {e}")

        # ─── Learnable λ (per-type optimized) ───
        try:
            ll_cal = LearnableLambdaCalibrator(alpha=cfg.alpha)
            ll_cal.calibrate(
                predictions, graph.node_labels, cal_masks, train_masks,
                graph.edge_index, graph.num_nodes,
            )
            result = ll_cal.predict(predictions, test_masks)
            rows.append(_build_row(seed, "chmp_learned_lambda", result, predictions, graph, test_masks))
            print(f"  seed={seed} chmp_learned_lambda: cov={marginal_coverage(result, graph.node_labels, test_masks):.4f}")
        except Exception as e:
            print(f"  WARN: chmp_learned_lambda seed={seed} failed: {e}")

        # ─── Attention-based neighbor difficulty ───
        try:
            attn_cal = AttentionCalibrator(alpha=cfg.alpha, attn_epochs=50)
            attn_cal.calibrate(
                graph.node_features, predictions, graph.node_labels,
                cal_masks, train_masks, graph.edge_index, graph.num_nodes,
            )
            result = attn_cal.predict(predictions, test_masks)
            rows.append(_build_row(seed, "chmp_attention", result, predictions, graph, test_masks))
            print(f"  seed={seed} chmp_attention: cov={marginal_coverage(result, graph.node_labels, test_masks):.4f}")
        except Exception as e:
            print(f"  WARN: chmp_attention seed={seed} failed: {e}")

        # ─── CQR + propagation ───
        try:
            model.eval()
            x_t = {nt: torch.tensor(graph.node_features[nt], dtype=torch.float32)
                   for nt in graph.node_features}
            ei_t = {et: torch.tensor(ei, dtype=torch.long)
                    for et, ei in graph.edge_index.items()}
            with torch.no_grad():
                h: dict = {}
                for nt in x_t:
                    h[nt] = F.relu(model.input_proj[nt](x_t[nt]))
                for layer in model.mp_layers:
                    h_new = layer(h, ei_t, graph.num_nodes)
                    for nt in h:
                        h_new[nt] = F.relu(h_new[nt]) + h[nt]
                    h = h_new

            # Increase quantile head training epochs and enable verbose logging
            cqr_cal = CQRCalibrator(alpha=cfg.alpha, quantile_epochs=200, lr=1e-3, verbose=True)
            cqr_cal.train_quantile_heads(h, graph.node_labels, train_masks, cfg.hidden_dim)
            cqr_cal.calibrate(
                predictions, graph.node_labels, cal_masks, train_masks,
                graph.edge_index, graph.num_nodes,
            )
            result = cqr_cal.predict(predictions, test_masks)
            rows.append(_build_row(seed, "cqr_propagation", result, predictions, graph, test_masks))
            print(f"  seed={seed} cqr_propagation: cov={marginal_coverage(result, graph.node_labels, test_masks):.4f}")
            # Save per-head quantile training losses for inspection
            try:
                import json
                out_losses = {k: v for k, v in cqr_cal._quantile_losses.items()}
                out_path = os.path.join(os.getcwd(), "outputs", f"cqr_quantile_losses_seed{seed}.json")
                with open(out_path, "w") as fh:
                    json.dump(out_losses, fh)
                print(f"  wrote {out_path}")
            except Exception as e:
                print(f"  WARN: failed to save quantile losses: {e}")
        except Exception as e:
            print(f"  WARN: cqr_propagation seed={seed} failed: {e}")

    return rows


# ── 5. Ensemble comparison ──────────────────────────────────────────────────

def run_ensemble_sweep() -> list[dict]:
    """Run ensemble-based conformal prediction across seeds."""
    from hetero_conformal.ensemble import EnsembleHeteroGNN, EnsembleCalibrator
    from hetero_conformal.metrics import marginal_coverage

    rows: list[dict] = []
    for seed in SEEDS:
        try:
            cfg = _cfg(seed, alpha=0.1, lam=0.3, prop=True)
            graph = generate_synthetic_infrastructure(
                n_power=cfg.n_power, n_water=cfg.n_water, n_telecom=cfg.n_telecom,
                feature_dim=cfg.feature_dim, coupling_prob=cfg.coupling_prob,
                coupling_radius=cfg.coupling_radius, seed=cfg.seed,
            )
            cal_masks = {nt: graph.node_masks[nt]["cal"] for nt in graph.node_masks}
            test_masks = {nt: graph.node_masks[nt]["test"] for nt in graph.node_masks}

            ensemble = EnsembleHeteroGNN(n_members=3)
            ensemble.build_and_train(graph, cfg, base_seed=seed)
            mean_preds, var_preds = ensemble.predict(graph)

            ens_cal = EnsembleCalibrator(alpha=cfg.alpha)
            ens_cal.calibrate(mean_preds, var_preds, graph.node_labels, cal_masks)
            result = ens_cal.predict(mean_preds, test_masks)

            rows.append(_build_row(seed, "ensemble_cp", result, mean_preds, graph, test_masks))
            print(f"  seed={seed} ensemble_cp: cov={marginal_coverage(result, graph.node_labels, test_masks):.4f}")
        except Exception as e:
            print(f"  WARN: ensemble_cp seed={seed} failed: {e}")
    return rows


# ── 6. Diagnostics ──────────────────────────────────────────────────────────

def run_diagnostics(seed: int = 0) -> dict:
    """Run full diagnostic analysis for a single seed."""
    import torch
    from hetero_conformal.conformal import PropagationAwareCalibrator
    from hetero_conformal.diagnostics import (
        full_diagnostic_report,
        nonexchangeability_test,
        spatial_autocorrelation_test,
    )
    from hetero_conformal.experiment import train_model, evaluate
    from hetero_conformal.model import HeteroGNN

    model, graph, cfg, predictions, cal_masks, test_masks, train_masks = \
        _train_model_for_seed(seed)

    # Calibrate with CHMP
    calibrator = PropagationAwareCalibrator(alpha=cfg.alpha, neighborhood_weight=0.3)
    calibrator.neighbor_agg = "mean"
    calibrator.calibrate_with_propagation(
        predictions, graph.node_labels, cal_masks, train_masks,
        graph.edge_index, graph.num_nodes,
    )
    result = calibrator.predict(predictions, test_masks)

    # Sigma values (from calibrator internals)
    sigma = {}
    for nt in test_masks:
        if hasattr(calibrator, "_sigma") and nt in calibrator._sigma:
            sigma[nt] = calibrator._sigma[nt]
        else:
            sigma[nt] = np.ones(graph.num_nodes[nt], dtype=np.float32)

    report = full_diagnostic_report(
        result, graph.node_labels, test_masks,
        sigma=sigma, edge_index=graph.edge_index,
        num_nodes=graph.num_nodes,
    )

    # Non-exchangeability tests on calibration scores
    report["nonexchangeability"] = {}
    for nt in cal_masks:
        cal_resid = np.abs(graph.node_labels[nt][cal_masks[nt]] - predictions[nt][cal_masks[nt]])
        sig_cal = sigma[nt][cal_masks[nt]] if sigma[nt].shape[0] > np.sum(cal_masks[nt]) else np.ones(np.sum(cal_masks[nt]))
        scores = cal_resid / sig_cal
        report["nonexchangeability"][nt] = nonexchangeability_test(scores)

    # Spatial autocorrelation
    report["spatial_autocorrelation"] = {}
    for nt in test_masks:
        pos = graph.node_positions[nt][test_masks[nt]]
        true = graph.node_labels[nt][test_masks[nt]]
        covered = ((true >= result.lower[nt]) & (true <= result.upper[nt])).astype(float)
        if len(covered) >= 10:
            report["spatial_autocorrelation"][nt] = spatial_autocorrelation_test(covered, pos)

    return report


def run_statistical_tests(baseline_rows: list[dict], advanced_rows: list[dict]) -> dict:
    """Paired Wilcoxon tests between baseline (mondrian_cp) and each method."""
    from hetero_conformal.diagnostics import paired_wilcoxon_test, multi_method_friedman_test

    all_rows = baseline_rows + advanced_rows
    methods = sorted({r["method"] for r in all_rows})

    # Collect per-seed coverage for each method
    method_cov: dict[str, list[float]] = {}
    method_ece: dict[str, list[float]] = {}
    method_width: dict[str, list[float]] = {}
    for m in methods:
        method_cov[m] = [r["marginal_cov"] for r in all_rows if r["method"] == m]
        method_ece[m] = [r["ece"] for r in all_rows if r["method"] == m]
        method_width[m] = [r["mean_width"] for r in all_rows if r["method"] == m]

    results: dict = {"pairwise_coverage": {}, "pairwise_ece": {}, "pairwise_width": {}}
    ref = "mondrian_cp"
    if ref in method_cov:
        for m in methods:
            if m == ref or len(method_cov[m]) != len(method_cov[ref]):
                continue
            results["pairwise_coverage"][f"{ref}_vs_{m}"] = paired_wilcoxon_test(
                method_cov[ref], method_cov[m]
            )
            results["pairwise_ece"][f"{ref}_vs_{m}"] = paired_wilcoxon_test(
                method_ece[ref], method_ece[m]
            )
            results["pairwise_width"][f"{ref}_vs_{m}"] = paired_wilcoxon_test(
                method_width[ref], method_width[m]
            )

    # Friedman test across all methods
    if len(methods) >= 3:
        results["friedman_coverage"] = multi_method_friedman_test(method_cov)
        results["friedman_ece"] = multi_method_friedman_test(method_ece)

    return results


# ── CSV helpers ──────────────────────────────────────────────────────────────

def _write_csv(path: Path, rows: list[dict]):
    if not rows:
        return
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote {path}")


# ── Tables (Markdown) ───────────────────────────────────────────────────────

def build_summary_table(rows: list[dict], group_col: str, path: Path):
    """Aggregate rows by `group_col` and write a Markdown table."""
    groups: dict[str, list[dict]] = {}
    for r in rows:
        k = str(r[group_col])
        groups.setdefault(k, []).append(r)

    lines = [
        f"| {group_col} | Marginal Cov | Mean Width | ECE |"
        + "".join(f" Cov {nt} |" for nt in NODE_TYPES),
        "| --- | ---: | ---: | ---: |" + " ---: |" * len(NODE_TYPES),
    ]
    for k in sorted(groups, key=lambda x: (x if not x.replace(".", "").replace("-","").isdigit() else float(x))):
        g = groups[k]
        mc = np.mean([r["marginal_cov"] for r in g])
        mw = np.mean([r["mean_width"] for r in g])
        me = np.mean([r["ece"] for r in g])
        type_covs = "".join(
            f" {np.mean([r[f'cov_{nt}'] for r in g]):.4f} |"
            for nt in NODE_TYPES
        )
        lines.append(f"| {k} | {mc:.4f} | {mw:.4f} | {me:.4f} |{type_covs}")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  wrote {path}")


# ── Plots ────────────────────────────────────────────────────────────────────

def plot_baseline_boxplots(rows: list[dict]):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
    metrics = [("marginal_cov", "Marginal Coverage"), ("mean_width", "Mean Width"), ("ece", "ECE")]
    methods = sorted({r["method"] for r in rows})

    for ax, (col, title) in zip(axes, metrics):
        data = [[r[col] for r in rows if r["method"] == m] for m in methods]
        bp = ax.boxplot(data, tick_labels=methods, patch_artist=True)
        colors = ["#4C72B0", "#DD8452"]
        for patch, color in zip(bp["boxes"], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)
        if col == "marginal_cov":
            ax.axhline(0.9, color="red", ls="--", lw=1, label="target 0.90")
            ax.legend(fontsize=8)
        ax.set_title(title)
        ax.grid(axis="y", alpha=0.3)

    fig.suptitle(f"Baseline Comparison ({SEED_COUNT} seeds, α=0.10)", fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "baseline_boxplots.png", dpi=150)
    plt.close(fig)
    print("  wrote baseline_boxplots.png")


def plot_coverage_by_type(rows: list[dict]):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    methods = sorted({r["method"] for r in rows})
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))

    for ax, nt in zip(axes, NODE_TYPES):
        col = f"cov_{nt}"
        data = [[r[col] for r in rows if r["method"] == m] for m in methods]
        bp = ax.boxplot(data, tick_labels=methods, patch_artist=True)
        colors = ["#4C72B0", "#DD8452"]
        for patch, color in zip(bp["boxes"], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)
        ax.axhline(0.9, color="red", ls="--", lw=1)
        ax.set_title(f"{nt.capitalize()} Coverage")
        ax.set_ylim(0.6, 1.05)
        ax.grid(axis="y", alpha=0.3)

    fig.suptitle(f"Per-Type Coverage ({SEED_COUNT} seeds, α=0.10)", fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "coverage_by_type.png", dpi=150)
    plt.close(fig)
    print("  wrote coverage_by_type.png")


def plot_lambda_sensitivity(rows: list[dict]):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    lambdas_sorted = sorted(set(r["lambda"] for r in rows))
    mean_cov = [np.mean([r["marginal_cov"] for r in rows if r["lambda"] == l]) for l in lambdas_sorted]
    std_cov = [np.std([r["marginal_cov"] for r in rows if r["lambda"] == l]) for l in lambdas_sorted]
    mean_w = [np.mean([r["mean_width"] for r in rows if r["lambda"] == l]) for l in lambdas_sorted]
    std_w = [np.std([r["mean_width"] for r in rows if r["lambda"] == l]) for l in lambdas_sorted]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.5))
    ax1.errorbar(lambdas_sorted, mean_cov, yerr=std_cov, marker="o", capsize=3)
    ax1.axhline(0.9, color="red", ls="--", lw=1, label="target")
    ax1.set_xlabel("λ (neighborhood weight)")
    ax1.set_ylabel("Marginal Coverage")
    ax1.set_title("Coverage vs λ")
    ax1.legend()
    ax1.grid(alpha=0.3)

    ax2.errorbar(lambdas_sorted, mean_w, yerr=std_w, marker="s", capsize=3, color="#DD8452")
    ax2.set_xlabel("λ (neighborhood weight)")
    ax2.set_ylabel("Mean Interval Width")
    ax2.set_title("Efficiency vs λ")
    ax2.grid(alpha=0.3)

    fig.suptitle(f"Lambda Sensitivity ({SEED_COUNT} seeds, α=0.10)", fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "lambda_sensitivity.png", dpi=150)
    plt.close(fig)
    print("  wrote lambda_sensitivity.png")


def plot_alpha_calibration(rows: list[dict]):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    alphas_sorted = sorted(set(r["alpha"] for r in rows))
    mean_cov = [np.mean([r["marginal_cov"] for r in rows if r["alpha"] == a]) for a in alphas_sorted]
    targets = [1 - a for a in alphas_sorted]

    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot([0.75, 1.0], [0.75, 1.0], "k--", lw=1, label="ideal")
    ax.scatter(targets, mean_cov, s=80, zorder=5, label=f"CHMP (mean over {SEED_COUNT} seeds)")
    for t, mc in zip(targets, mean_cov):
        ax.annotate(f"α={1-t:.2f}", (float(t), float(mc)), textcoords="offset points", xytext=(8, -8), fontsize=8)
    ax.set_xlabel("Target Coverage (1−α)")
    ax.set_ylabel("Empirical Coverage")
    ax.set_title("Calibration Plot")
    ax.legend()
    ax.grid(alpha=0.3)
    ax.set_xlim(0.75, 1.0)
    ax.set_ylim(0.75, 1.0)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "alpha_calibration.png", dpi=150)
    plt.close(fig)
    print("  wrote alpha_calibration.png")


# ── Spatial map ──────────────────────────────────────────────────────────────

def plot_spatial_map(seed: int = 0):
    """Plot a spatial map of the graph with node risk scores and intervals."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection

    cfg = _cfg(seed, alpha=0.1, lam=0.3, prop=True)
    graph = generate_synthetic_infrastructure(
        n_power=cfg.n_power, n_water=cfg.n_water, n_telecom=cfg.n_telecom,
        feature_dim=cfg.feature_dim, coupling_prob=cfg.coupling_prob,
        coupling_radius=cfg.coupling_radius, seed=cfg.seed,
    )
    r = run_experiment(cfg, verbose=False)

    fig, axes = plt.subplots(1, 3, figsize=(18, 5.5))
    cmap = plt.cm.RdYlGn_r  # type: ignore[attr-defined]
    markers = {"power": "^", "water": "s", "telecom": "o"}
    titles = [
        "Risk Scores (Ground Truth)",
        "Prediction Intervals (Width)",
        "Coverage Map (Hit/Miss)",
    ]

    for ax, title in zip(axes, titles):
        ax.set_title(title, fontsize=11)
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.set_aspect("equal")

    # Panel 1: ground truth risk
    ax = axes[0]
    sc = None
    for nt in NODE_TYPES:
        pos = graph.node_positions[nt]
        labels = graph.node_labels[nt]
        sc = ax.scatter(pos[:, 0], pos[:, 1], c=labels, cmap=cmap,
                        marker=markers[nt], s=30, alpha=0.8, edgecolors="k",
                        linewidths=0.3, vmin=0, vmax=1, label=nt)
    if sc is not None:
        fig.colorbar(sc, ax=ax, label="Risk Score", shrink=0.8)
    ax.legend(loc="lower left", fontsize=8)

    # Panel 2: interval widths on test nodes
    assert r.conformal_result is not None, "conformal_result is required for plotting"
    ax = axes[1]
    sc = None
    for nt in NODE_TYPES:
        test_mask = graph.node_masks[nt]["test"]
        pos = graph.node_positions[nt][test_mask]
        widths = r.conformal_result.upper[nt] - r.conformal_result.lower[nt]
        sc = ax.scatter(pos[:, 0], pos[:, 1], c=widths, cmap="YlOrRd",
                        marker=markers[nt], s=35, alpha=0.85, edgecolors="k",
                        linewidths=0.3, label=nt)
    if sc is not None:
        fig.colorbar(sc, ax=ax, label="Interval Width", shrink=0.8)
    ax.legend(loc="lower left", fontsize=8)

    # Panel 3: coverage hit/miss
    ax = axes[2]
    for nt in NODE_TYPES:
        test_mask = graph.node_masks[nt]["test"]
        pos = graph.node_positions[nt][test_mask]
        true = graph.node_labels[nt][test_mask]
        lo = r.conformal_result.lower[nt]
        hi = r.conformal_result.upper[nt]
        hit = (true >= lo) & (true <= hi)
        colors = ["#2ca02c" if h else "#d62728" for h in hit]
        ax.scatter(pos[:, 0], pos[:, 1], c=colors,
                   marker=markers[nt], s=35, alpha=0.85, edgecolors="k",
                   linewidths=0.3, label=nt)
    # manual legend for hit/miss
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#2ca02c", markersize=8, label="Covered"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#d62728", markersize=8, label="Missed"),
    ]
    ax.legend(handles=legend_elements, loc="lower left", fontsize=8)

    # Draw some cross-edges lightly in all panels
    for ax_i in axes:
        for (src_type, rel, dst_type), ei in graph.edge_index.items():
            if src_type == dst_type or ei.shape[1] == 0:
                continue
            src_pos = graph.node_positions[src_type]
            dst_pos = graph.node_positions[dst_type]
            # sample up to 200 edges for visual clarity
            n_draw = min(200, ei.shape[1])
            idx = np.random.default_rng(0).choice(ei.shape[1], n_draw, replace=False)
            segs = np.stack([src_pos[ei[0, idx]], dst_pos[ei[1, idx]]], axis=1)
            segs_list = segs.tolist()
            lc = LineCollection(segs_list, colors="gray", alpha=0.06, linewidths=0.3)
            ax_i.add_collection(lc)

    fig.suptitle(f"Spatial Infrastructure Map (seed={seed}, α=0.10)", fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "spatial_map.png", dpi=150)
    plt.close(fig)
    print("  wrote spatial_map.png")


def plot_per_type_width_map(seed: int = 0):
    """One map per infrastructure type showing interval width heatmap."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    cfg = _cfg(seed, alpha=0.1, lam=0.3, prop=True)
    graph = generate_synthetic_infrastructure(
        n_power=cfg.n_power, n_water=cfg.n_water, n_telecom=cfg.n_telecom,
        feature_dim=cfg.feature_dim, coupling_prob=cfg.coupling_prob,
        coupling_radius=cfg.coupling_radius, seed=cfg.seed,
    )
    r = run_experiment(cfg, verbose=False)

    assert r.conformal_result is not None, "conformal_result is required for plotting"

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    markers = {"power": "^", "water": "s", "telecom": "o"}

    for ax, nt in zip(axes, NODE_TYPES):
        test_mask = graph.node_masks[nt]["test"]
        pos = graph.node_positions[nt][test_mask]
        widths = r.conformal_result.upper[nt] - r.conformal_result.lower[nt]
        sc = ax.scatter(pos[:, 0], pos[:, 1], c=widths, cmap="YlOrRd",
                        marker=markers[nt], s=50, alpha=0.9,
                        edgecolors="k", linewidths=0.4)
        fig.colorbar(sc, ax=ax, shrink=0.8, label="Width")
        ax.set_title(f"{nt.capitalize()} — Interval Width", fontsize=11)
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.set_aspect("equal")
        ax.grid(alpha=0.2)

    fig.suptitle(f"Per-Type Interval Width Maps (seed={seed})", fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "per_type_width_map.png", dpi=150)
    plt.close(fig)
    print("  wrote per_type_width_map.png")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("STRATA Benchmark Suite (Full)")
    print("=" * 60)

    # 1. Baseline comparison
    print(f"\n[1/9] Baseline comparison ({SEED_COUNT} seeds)…")
    baseline_rows = run_baseline_sweep()
    _write_csv(OUT_DIR / "baseline_comparison.csv", baseline_rows)
    build_summary_table(baseline_rows, "method", OUT_DIR / "baseline_table.md")
    plot_baseline_boxplots(baseline_rows)
    plot_coverage_by_type(baseline_rows)

    # 2. Lambda sensitivity
    print(f"\n[2/9] Lambda sensitivity ({SEED_COUNT} seeds × {len(LAMBDAS)} lambdas)…")
    lambda_rows = run_lambda_sweep()
    _write_csv(OUT_DIR / "lambda_sensitivity.csv", lambda_rows)
    build_summary_table(lambda_rows, "lambda", OUT_DIR / "lambda_table.md")
    plot_lambda_sensitivity(lambda_rows)

    # 3. Alpha calibration
    print(f"\n[3/9] Alpha sweep ({SEED_COUNT} seeds × {len(ALPHAS)} alphas)…")
    alpha_rows = run_alpha_sweep()
    _write_csv(OUT_DIR / "alpha_sweep.csv", alpha_rows)
    build_summary_table(alpha_rows, "alpha", OUT_DIR / "alpha_table.md")
    plot_alpha_calibration(alpha_rows)

    # 4. Advanced calibrators
    print(f"\n[4/9] Advanced calibrators ({SEED_COUNT} seeds)…")
    advanced_rows = run_advanced_sweep()
    _write_csv(OUT_DIR / "advanced_comparison.csv", advanced_rows)
    build_summary_table(advanced_rows, "method", OUT_DIR / "advanced_table.md")

    # 5. Ensemble comparison
    print(f"\n[5/9] Ensemble comparison ({SEED_COUNT} seeds)…")
    ensemble_rows = run_ensemble_sweep()
    _write_csv(OUT_DIR / "ensemble_comparison.csv", ensemble_rows)

    # 6. Full method comparison table
    print("\n[6/9] Full method comparison table…")
    all_method_rows = baseline_rows + advanced_rows + ensemble_rows
    _write_csv(OUT_DIR / "full_comparison.csv", all_method_rows)
    build_summary_table(all_method_rows, "method", OUT_DIR / "full_comparison_table.md")

    # 7. Statistical tests
    print("\n[7/9] Statistical tests (Wilcoxon, Friedman)…")
    stat_results = run_statistical_tests(baseline_rows, advanced_rows + ensemble_rows)
    with open(OUT_DIR / "statistical_tests.json", "w") as f:
        json.dump(stat_results, f, indent=2, default=str)
    print(f"  wrote {OUT_DIR / 'statistical_tests.json'}")

    # 8. Spatial maps
    print("\n[8/9] Spatial maps (seed 0)…")
    plot_spatial_map(seed=0)
    plot_per_type_width_map(seed=0)

    # 9. Diagnostics
    print("\n[9/9] Diagnostics (seed 0)…")
    diag_report = run_diagnostics(seed=0)
    # Serialise report (convert numpy arrays for JSON)
    def _serialise(obj: object) -> object:
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if hasattr(obj, 'item') and hasattr(obj, 'dtype'):
            return obj.item()  # type: ignore[union-attr]
        if isinstance(obj, dict):
            return {k: _serialise(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_serialise(v) for v in obj]
        return obj
    with open(OUT_DIR / "diagnostics.json", "w") as f:
        json.dump(_serialise(diag_report), f, indent=2)
    print(f"  wrote {OUT_DIR / 'diagnostics.json'}")

    # Write summary JSON
    print("\nWriting final summary…")
    summary = {
        "baseline": _aggregate(baseline_rows, "method"),
        "advanced": _aggregate(advanced_rows, "method") if advanced_rows else {},
        "ensemble": _aggregate(ensemble_rows, "method") if ensemble_rows else {},
        "lambda": _aggregate_num(lambda_rows, "lambda"),
        "alpha": _aggregate_num(alpha_rows, "alpha"),
    }
    with open(OUT_DIR / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    print(f"  wrote {OUT_DIR / 'summary.json'}")

    print("\n" + "=" * 60)
    print("Done. All outputs in:", OUT_DIR)
    print("=" * 60)


def _aggregate(rows: list[dict], key: str) -> dict:
    groups: dict[str, list[dict]] = {}
    for r in rows:
        groups.setdefault(str(r[key]), []).append(r)
    out = {}
    for k, g in groups.items():
        out[k] = {
            "mean_cov": float(np.mean([r["marginal_cov"] for r in g])),
            "std_cov": float(np.std([r["marginal_cov"] for r in g])),
            "mean_width": float(np.mean([r["mean_width"] for r in g])),
            "std_width": float(np.std([r["mean_width"] for r in g])),
            "mean_ece": float(np.mean([r["ece"] for r in g])),
        }
    return out


def _aggregate_num(rows: list[dict], key: str) -> dict:
    return _aggregate(rows, key)


if __name__ == "__main__":
    main()
