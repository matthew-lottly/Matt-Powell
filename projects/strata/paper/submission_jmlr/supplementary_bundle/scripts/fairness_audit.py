"""Run a group-wise fairness audit for STRATA conformal predictions.

The audit reports per-type coverage, interval width disparity, worst-group gap,
and feature-binned conditional coverage.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from hetero_conformal import (
    HeteroConformalCalibrator,
    coverage_by_feature_bin,
    mean_interval_width,
    marginal_coverage,
    type_conditional_coverage,
)
from hetero_conformal.experiment import ExperimentConfig, run_experiment


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-prefix", default="outputs/fairness_audit")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    out_prefix = Path(args.out_prefix)
    out_prefix.parent.mkdir(parents=True, exist_ok=True)

    result = run_experiment(ExperimentConfig(seed=args.seed, epochs=60, patience=10), verbose=False)
    conf_result = result.conformal_result
    if conf_result is None:
        raise RuntimeError("Expected conformal_result from run_experiment")

    labels = {}
    test_masks = {}
    for ntype in result.type_cov:
        labels[ntype] = np.array([])
    # Reconstruct labels/test masks by rerunning small experiment data path through config.
    rerun = run_experiment(ExperimentConfig(seed=args.seed, epochs=60, patience=10), verbose=False)
    graph = None
    if hasattr(rerun, "config"):
        from hetero_conformal.graph import generate_synthetic_infrastructure

        cfg = rerun.config
        graph = generate_synthetic_infrastructure(
            n_power=cfg.n_power,
            n_water=cfg.n_water,
            n_telecom=cfg.n_telecom,
            feature_dim=cfg.feature_dim,
            coupling_prob=cfg.coupling_prob,
            coupling_radius=cfg.coupling_radius,
            seed=cfg.seed,
        )
        labels = graph.node_labels
        test_masks = {nt: graph.node_masks[nt]["test"] for nt in graph.node_masks}

    per_type = type_conditional_coverage(conf_result, labels, test_masks)
    widths = {
        ntype: float(np.mean(conf_result.upper[ntype] - conf_result.lower[ntype]))
        for ntype in conf_result.lower
    }
    overall_cov = marginal_coverage(conf_result, labels, test_masks)
    overall_width = mean_interval_width(conf_result)
    worst_gap = max(abs(overall_cov - cov) for cov in per_type.values()) if per_type else 0.0

    feature_bins = coverage_by_feature_bin(
        conf_result,
        labels,
        graph.node_features if graph is not None else {},
        feature_idx=0,
        test_masks=test_masks,
        n_bins=5,
    ) if graph is not None else {}

    csv_path = out_prefix.with_suffix(".csv")
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["group", "coverage", "mean_width"])
        for ntype, cov in per_type.items():
            writer.writerow([ntype, cov, widths.get(ntype, float("nan"))])

    json_path = out_prefix.with_suffix(".json")
    json_path.write_text(
        json.dumps(
            {
                "overall_coverage": overall_cov,
                "overall_width": overall_width,
                "worst_group_gap": worst_gap,
                "per_type_coverage": per_type,
                "per_type_width": widths,
                "feature_binned_coverage": {
                    k: {sk: v.tolist() for sk, v in info.items()} for k, info in feature_bins.items()
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Wrote fairness audit to {csv_path} and {json_path}")


if __name__ == "__main__":
    main()
