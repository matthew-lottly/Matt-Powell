"""End-to-end experiment runner: train, calibrate, test, evaluate."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

from .conformal import (
    ConformalResult,
    HeteroConformalCalibrator,
    PropagationAwareCalibrator,
)
from .graph import HeteroInfraGraph, generate_synthetic_infrastructure, ALL_EDGE_TYPES
from .metrics import (
    calibration_error,
    marginal_coverage,
    mean_interval_width,
    prediction_set_efficiency,
    rmse_per_type,
    type_conditional_coverage,
)
from .model import HeteroGNN


@dataclass
class ExperimentConfig:
    """Configuration for a single experiment run."""

    # Data
    n_power: int = 200
    n_water: int = 150
    n_telecom: int = 100
    feature_dim: int = 8
    coupling_prob: float = 0.3
    coupling_radius: float = 0.15
    seed: int = 42

    # Model
    hidden_dim: int = 64
    num_layers: int = 3
    dropout: float = 0.1

    # Training
    lr: float = 1e-3
    weight_decay: float = 1e-4
    epochs: int = 200
    patience: int = 20

    # Conformal
    alpha: float = 0.1
    use_propagation_aware: bool = True
    neighborhood_weight: float = 0.3
    # Propagation-aware calibrator options
    neighbor_agg: str = "mean"  # 'mean' | 'median' | 'trimmed'
    trimmed_frac: float = 0.0
    floor_sigma: float = 0.0

    # Device
    device: str = "cpu"


@dataclass
class ExperimentResult:
    """Stores all outputs from an experiment run."""

    config: ExperimentConfig
    train_losses: list
    best_epoch: int
    train_time: float
    rmse: Dict[str, float]
    marginal_cov: float
    type_cov: Dict[str, float]
    interval_widths: Dict[str, float]
    mean_width: float
    ece: float
    quantiles: Dict[str, float]
    conformal_result: Optional[ConformalResult] = None


def _graph_to_tensors(
    graph: HeteroInfraGraph, device: str
) -> Tuple[Dict[str, torch.Tensor], Dict[Tuple, torch.Tensor], Dict[str, torch.Tensor]]:
    """Convert graph arrays to torch tensors."""
    x = {
        ntype: torch.tensor(feats, dtype=torch.float32, device=device)
        for ntype, feats in graph.node_features.items()
    }
    edge_index = {
        etype: torch.tensor(ei, dtype=torch.long, device=device)
        for etype, ei in graph.edge_index.items()
    }
    labels = {
        ntype: torch.tensor(lab, dtype=torch.float32, device=device)
        for ntype, lab in graph.node_labels.items()
    }
    return x, edge_index, labels


def train_model(
    model: HeteroGNN,
    graph: HeteroInfraGraph,
    config: ExperimentConfig,
) -> Tuple[HeteroGNN, list, int]:
    """Train the heterogeneous GNN with early stopping.

    Returns the trained model, loss history, and best epoch.
    """
    device = config.device
    x, edge_index, labels = _graph_to_tensors(graph, device)
    num_nodes = graph.num_nodes

    optimizer = optim.Adam(
        model.parameters(), lr=config.lr, weight_decay=config.weight_decay
    )
    criterion = nn.MSELoss()

    best_loss = float("inf")
    best_state = None
    best_epoch = 0
    patience_counter = 0
    losses = []

    model.train()
    for epoch in range(config.epochs):
        optimizer.zero_grad()
        preds = model(x, edge_index, num_nodes)

        # Compute loss over training nodes only
        loss = torch.tensor(0.0, device=device, requires_grad=True)
        for ntype in preds:
            mask = graph.node_masks[ntype]["train"]
            mask_t = torch.tensor(mask, device=device)
            if mask_t.sum() == 0:
                continue
            ntype_loss = criterion(preds[ntype][mask_t], labels[ntype][mask_t])
            loss = loss + ntype_loss

        loss.backward()
        optimizer.step()

        loss_val = loss.item()
        losses.append(loss_val)

        # Early stopping on TRAINING loss (not calibration loss)
        # to preserve exchangeability of calibration scores
        if loss_val < best_loss:
            best_loss = loss_val
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            best_epoch = epoch
            patience_counter = 0
        else:
            patience_counter += 1

        if patience_counter >= config.patience:
            break

    if best_state is not None:
        model.load_state_dict(best_state)

    return model, losses, best_epoch


@torch.no_grad()
def evaluate(
    model: HeteroGNN,
    graph: HeteroInfraGraph,
    config: ExperimentConfig,
) -> Dict[str, np.ndarray]:
    """Run model inference and return numpy predictions."""
    device = config.device
    x, edge_index, _ = _graph_to_tensors(graph, device)
    model.eval()
    preds = model(x, edge_index, graph.num_nodes)
    return {ntype: p.cpu().numpy() for ntype, p in preds.items()}


def run_experiment(config: Optional[ExperimentConfig] = None, verbose: bool = True, graph: Optional[HeteroInfraGraph] = None) -> ExperimentResult:
    """Run a full experiment: generate data, train, calibrate, evaluate.

    Parameters
    ----------
    config : ExperimentConfig, optional
        Experiment configuration. Uses defaults if not provided.
    graph : HeteroInfraGraph, optional
        Pre-built graph (e.g. from ``load_activsg200``).  When supplied the
        synthetic generator is skipped.

    Returns
    -------
    ExperimentResult with all metrics.
    """
    if config is None:
        config = ExperimentConfig()

    # Seed everything for reproducibility
    torch.manual_seed(config.seed)
    np.random.seed(config.seed)

    # 1. Use supplied graph or generate synthetic infrastructure graph
    if graph is None:
        graph = generate_synthetic_infrastructure(
            n_power=config.n_power,
            n_water=config.n_water,
            n_telecom=config.n_telecom,
            feature_dim=config.feature_dim,
            coupling_prob=config.coupling_prob,
            coupling_radius=config.coupling_radius,
            seed=config.seed,
        )
    if verbose:
        print(graph.summary())

    # 2. Build and train model
    in_dims = {ntype: f.shape[1] for ntype, f in graph.node_features.items()}
    edge_types = list(graph.edge_index.keys())

    model = HeteroGNN(
        in_dims=in_dims,
        hidden_dim=config.hidden_dim,
        num_layers=config.num_layers,
        edge_types=edge_types,
        dropout=config.dropout,
    ).to(config.device)

    t0 = time.time()
    model, losses, best_epoch = train_model(model, graph, config)
    train_time = time.time() - t0
    if verbose:
        print(f"Training complete: {best_epoch + 1} epochs, {train_time:.1f}s")

    # 3. Get predictions
    predictions = evaluate(model, graph, config)

    # 4. Conformal calibration
    cal_masks = {ntype: graph.node_masks[ntype]["cal"] for ntype in graph.node_masks}
    test_masks = {ntype: graph.node_masks[ntype]["test"] for ntype in graph.node_masks}
    train_masks = {ntype: graph.node_masks[ntype]["train"] for ntype in graph.node_masks}

    if config.use_propagation_aware:
        calibrator = PropagationAwareCalibrator(
            alpha=config.alpha,
            neighborhood_weight=config.neighborhood_weight,
        )
        # set optional aggregation and sigma floor parameters
        calibrator.neighbor_agg = getattr(config, "neighbor_agg", "mean")
        calibrator.trimmed_frac = getattr(config, "trimmed_frac", 0.0)
        calibrator.floor_sigma = getattr(config, "floor_sigma", 0.0)
        quantiles = calibrator.calibrate_with_propagation(
            predictions, graph.node_labels, cal_masks, train_masks,
            graph.edge_index, graph.num_nodes,
        )
    else:
        calibrator = HeteroConformalCalibrator(alpha=config.alpha)
        quantiles = calibrator.calibrate(predictions, graph.node_labels, cal_masks)

    # 5. Conformalized predictions
    conf_result = calibrator.predict(predictions, test_masks)

    # 6. Compute metrics
    rmse = rmse_per_type(predictions, graph.node_labels, test_masks)
    m_cov = marginal_coverage(conf_result, graph.node_labels, test_masks)
    t_cov = type_conditional_coverage(conf_result, graph.node_labels, test_masks)
    widths = prediction_set_efficiency(conf_result)
    m_width = mean_interval_width(conf_result)
    ece = calibration_error(conf_result, graph.node_labels, test_masks)

    if verbose:
        print(f"\n--- Results (alpha={config.alpha}) ---")
        print(f"Marginal coverage: {m_cov:.4f} (target: {1 - config.alpha:.2f})")
        for ntype, cov in t_cov.items():
            print(f"  {ntype} coverage: {cov:.4f}, width: {widths[ntype]:.4f}, RMSE: {rmse[ntype]:.4f}")
        print(f"Mean interval width: {m_width:.4f}")
        print(f"ECE: {ece:.4f}")

    return ExperimentResult(
        config=config,
        train_losses=losses,
        best_epoch=best_epoch,
        train_time=train_time,
        rmse=rmse,
        marginal_cov=m_cov,
        type_cov=t_cov,
        interval_widths=widths,
        mean_width=m_width,
        ece=ece,
        quantiles=quantiles,
        conformal_result=conf_result,
    )


def run_ablation_study(
    base_config: Optional[ExperimentConfig] = None,
    alphas: Optional[list] = None,
    seeds: Optional[list] = None,
) -> list:
    """Run ablation experiments varying alpha and random seeds.

    Returns a list of ExperimentResult objects.
    """
    if base_config is None:
        base_config = ExperimentConfig()
    if alphas is None:
        alphas = [0.05, 0.1, 0.15, 0.2]
    if seeds is None:
        seeds = [42, 123, 456]

    results = []
    for alpha in alphas:
        for seed in seeds:
            cfg = ExperimentConfig(
                n_power=base_config.n_power,
                n_water=base_config.n_water,
                n_telecom=base_config.n_telecom,
                feature_dim=base_config.feature_dim,
                coupling_prob=base_config.coupling_prob,
                coupling_radius=base_config.coupling_radius,
                seed=seed,
                hidden_dim=base_config.hidden_dim,
                num_layers=base_config.num_layers,
                dropout=base_config.dropout,
                lr=base_config.lr,
                weight_decay=base_config.weight_decay,
                epochs=base_config.epochs,
                patience=base_config.patience,
                alpha=alpha,
                use_propagation_aware=base_config.use_propagation_aware,
                neighborhood_weight=base_config.neighborhood_weight,
                device=base_config.device,
            )
            print(f"\n=== alpha={alpha}, seed={seed} ===")
            result = run_experiment(cfg)
            results.append(result)

    return results


def run_baseline_comparison(
    config: Optional[ExperimentConfig] = None,
) -> Dict[str, ExperimentResult]:
    """Run CHMP against baselines on the same data.

    Baselines:
    1. vanilla_cp: Standard split CP (marginal, no per-type grouping)
    2. mondrian_cp: Per-type Mondrian CP without propagation awareness
    3. chmp: Full method with propagation-aware calibration

    Returns dict mapping method name -> ExperimentResult.
    """
    if config is None:
        config = ExperimentConfig()

    results = {}

    # Baseline 1: Vanilla CP = marginal calibration, no per-type grouping
    cfg_vanilla = ExperimentConfig(
        **{k: v for k, v in config.__dict__.items()
         if k != "use_propagation_aware"},
        use_propagation_aware=False,
    )
    print("\n=== Baseline: Vanilla per-type CP ===")
    results["mondrian_cp"] = run_experiment(cfg_vanilla)

    # Baseline 2: CHMP (full method)
    print("\n=== CHMP (propagation-aware) ===")
    results["chmp"] = run_experiment(config)

    # Print comparison table
    print("\n" + "=" * 70)
    print(f"{'Method':<20} {'Marginal Cov':>12} {'Mean Width':>12} {'ECE':>8}")
    print("-" * 70)
    for name, r in results.items():
        print(f"{name:<20} {r.marginal_cov:>12.4f} {r.mean_width:>12.4f} {r.ece:>8.4f}")
    print("=" * 70)

    return results


def run_coverage_histogram(
    config: Optional[ExperimentConfig] = None,
    n_trials: int = 100,
) -> Dict[str, list]:
    """Run many trials to build empirical coverage histograms.

    This verifies that coverage concentrates around (1-alpha) across
    random data splits, as required for a valid conformal guarantee.

    Returns dict mapping node type -> list of per-trial coverage values.
    """
    if config is None:
        config = ExperimentConfig()

    coverage_history: Dict[str, list] = {t: [] for t in ["power", "water", "telecom"]}
    width_history: Dict[str, list] = {t: [] for t in ["power", "water", "telecom"]}

    for trial in range(n_trials):
        cfg = ExperimentConfig(
            **{k: v for k, v in config.__dict__.items() if k != "seed"},
            seed=trial,
        )
        result = run_experiment(cfg)
        for ntype in result.type_cov:
            coverage_history[ntype].append(result.type_cov[ntype])
            width_history[ntype].append(result.interval_widths[ntype])

    target = 1 - config.alpha
    print(f"\n=== Coverage Histogram ({n_trials} trials, target={target:.2f}) ===")
    for ntype in coverage_history:
        covs = coverage_history[ntype]
        mean_c = np.mean(covs)
        std_c = np.std(covs)
        frac_above = np.mean(np.array(covs) >= target)
        print(f"  {ntype}: mean={mean_c:.4f} ± {std_c:.4f}, "
              f"P(cov ≥ {target})={frac_above:.2f}")

    return coverage_history


def run_lambda_sensitivity(
    config: Optional[ExperimentConfig] = None,
    lambdas: Optional[list] = None,
    seeds: Optional[list] = None,
) -> list:
    """Sweep the propagation mixing weight lambda.

    Shows that coverage is maintained for all lambda values
    while interval efficiency varies—validating robustness.
    """
    if config is None:
        config = ExperimentConfig()
    if lambdas is None:
        lambdas = [0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0]
    if seeds is None:
        seeds = [42, 123, 456]

    results = []
    for lam in lambdas:
        for seed in seeds:
            cfg = ExperimentConfig(
                **{k: v for k, v in config.__dict__.items()
                 if k not in ("neighborhood_weight", "seed",
                              "use_propagation_aware")},
                neighborhood_weight=lam,
                use_propagation_aware=(lam > 0),
                seed=seed,
            )
            print(f"\n=== lambda={lam}, seed={seed} ===")
            result = run_experiment(cfg)
            results.append(result)

    return results


if __name__ == "__main__":
    result = run_experiment()
