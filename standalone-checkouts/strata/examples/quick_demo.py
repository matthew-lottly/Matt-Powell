#!/usr/bin/env python
"""STRATA Quick Demo — end-to-end conformal prediction on infrastructure graphs.

This example demonstrates the core STRATA pipeline:
1. Generate a synthetic heterogeneous infrastructure graph
2. Train a HeteroGNN model
3. Apply multiple conformal calibration methods
4. Evaluate coverage, width, and calibration error
5. Run diagnostics

Usage:
    python examples/quick_demo.py
"""

import numpy as np
import torch

from hetero_conformal import (
    generate_synthetic_infrastructure,
    HeteroGNN,
    HeteroConformalCalibrator,
    PropagationAwareCalibrator,
    MetaCalibrator,
    EnsembleHeteroGNN,
    EnsembleCalibrator,
    StreamingConformalCalibrator,
    AdaptiveConformalCalibrator,
    marginal_coverage,
    type_conditional_coverage,
    mean_interval_width,
    calibration_error,
    interval_decomposition,
    uncertainty_attribution,
)
from hetero_conformal.experiment import ExperimentConfig, train_model


def main():
    # ── 1. Generate Data ────────────────────────────────────────────────────
    print("=" * 60)
    print("STRATA Quick Demo")
    print("=" * 60)

    seed = 42
    torch.manual_seed(seed)
    np.random.seed(seed)

    graph = generate_synthetic_infrastructure(
        n_power=200, n_water=150, n_telecom=100, seed=seed,
    )
    print(f"\n{graph.summary()}")

    # ── 2. Train Model ──────────────────────────────────────────────────────
    print("\n── Training HeteroGNN ──")
    config = ExperimentConfig(
        hidden_dim=64, num_layers=3, epochs=100, patience=20,
    )
    in_dims = {nt: f.shape[1] for nt, f in graph.node_features.items()}
    edge_types = list(graph.edge_index.keys())
    model = HeteroGNN(
        in_dims=in_dims, hidden_dim=config.hidden_dim,
        num_layers=config.num_layers, edge_types=edge_types,
        dropout=config.dropout,
    )
    model, losses, _ = train_model(model, graph, config)
    print(f"  Final training loss: {losses[-1]:.4f} ({len(losses)} epochs)")

    # ── 3. Get Predictions ──────────────────────────────────────────────────
    model.eval()
    with torch.no_grad():
        x = {nt: torch.tensor(f, dtype=torch.float32)
             for nt, f in graph.node_features.items()}
        ei = {et: torch.tensor(e, dtype=torch.long)
              for et, e in graph.edge_index.items()}
        preds = {nt: p.numpy() for nt, p in model(x, ei, graph.num_nodes).items()}

    train_masks = {nt: m["train"] for nt, m in graph.node_masks.items()}
    cal_masks = {nt: m["cal"] for nt, m in graph.node_masks.items()}
    test_masks = {nt: m["test"] for nt, m in graph.node_masks.items()}

    # ── 4. Conformal Calibration Methods ────────────────────────────────────
    print("\n── Conformal Calibration ──")
    methods = {}

    # Method 1: Vanilla (Mondrian split conformal)
    vanilla = HeteroConformalCalibrator(alpha=0.1)
    vanilla.calibrate(preds, graph.node_labels, cal_masks)
    methods["Vanilla"] = vanilla.predict(preds, test_masks)

    # Method 2: Propagation-Aware
    prop = PropagationAwareCalibrator(alpha=0.1, neighborhood_weight=0.3)
    prop.calibrate_with_propagation(
        preds, graph.node_labels, cal_masks, train_masks,
        graph.edge_index, graph.num_nodes,
    )
    methods["Propagation"] = prop.predict(preds, test_masks)

    # Method 3: Meta-Calibrator
    meta = MetaCalibrator(alpha=0.1, meta_epochs=100)
    meta.calibrate(
        graph.node_features, preds, graph.node_labels,
        cal_masks, train_masks, graph.edge_index, graph.num_nodes,
    )
    methods["Meta"] = meta.predict(preds, test_masks)

    # ── 5. Evaluate Results ─────────────────────────────────────────────────
    print("\n── Results ──")
    print(f"{'Method':<16} {'Coverage':>10} {'Width':>10} {'ECE':>10}")
    print("-" * 50)

    for name, result in methods.items():
        cov = marginal_coverage(result, graph.node_labels, test_masks)
        width = mean_interval_width(result)
        ece = calibration_error(result, graph.node_labels, test_masks)
        print(f"{name:<16} {cov:>10.3f} {width:>10.3f} {ece:>10.4f}")

    # Per-type coverage for best method
    print("\n── Per-Type Coverage (Propagation) ──")
    type_cov = type_conditional_coverage(methods["Propagation"], graph.node_labels, test_masks)
    for nt, cov in type_cov.items():
        print(f"  {nt}: {cov:.3f}")

    # ── 6. Streaming Demo ───────────────────────────────────────────────────
    print("\n── Streaming Conformal Demo ──")
    stream = StreamingConformalCalibrator(alpha=0.1, window_size=200)
    # Simulate streaming by feeding batches from cal set
    for nt in cal_masks:
        mask = cal_masks[nt]
        stream.update(
            {nt: preds[nt][mask]},
            {nt: graph.node_labels[nt][mask]},
        )
    print(f"  Window sizes: {stream.window_sizes}")
    stream_result = stream.predict({nt: preds[nt][test_masks[nt]] for nt in test_masks})
    stream_cov = marginal_coverage(
        stream_result,
        {nt: graph.node_labels[nt][test_masks[nt]] for nt in test_masks},
    )
    print(f"  Streaming coverage: {stream_cov:.3f}")

    # ── 7. Explainability ───────────────────────────────────────────────────
    print("\n── Uncertainty Attribution ──")
    if hasattr(prop, '_sigma'):
        attrib = uncertainty_attribution(
            prop._sigma, graph.node_features, test_masks, top_k=3,
        )
        for nt, info in attrib.items():
            if len(info["top_features"]) > 0:
                print(f"  {nt}: top features = {info['top_features']}, "
                      f"correlations = {info['top_correlations']}")

    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
