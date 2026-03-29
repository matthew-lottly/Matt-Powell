"""Evaluation metrics for conformalized heterogeneous graph predictions."""

from __future__ import annotations

from typing import Dict, Optional

import numpy as np

from .conformal import ConformalResult


def marginal_coverage(
    result: ConformalResult,
    labels: Dict[str, np.ndarray],
    test_masks: Optional[Dict[str, np.ndarray]] = None,
) -> float:
    """Compute marginal coverage across all node types.

    Returns the fraction of test nodes whose true label falls
    within the prediction interval [lower, upper].
    """
    total, covered = 0, 0
    for ntype in result.lower:
        if test_masks is not None and ntype in test_masks:
            true = labels[ntype][test_masks[ntype]]
        else:
            true = labels[ntype]
        c = np.sum((true >= result.lower[ntype]) & (true <= result.upper[ntype]))
        covered += c
        total += len(true)
    return float(covered / total) if total > 0 else 0.0


def type_conditional_coverage(
    result: ConformalResult,
    labels: Dict[str, np.ndarray],
    test_masks: Optional[Dict[str, np.ndarray]] = None,
) -> Dict[str, float]:
    """Compute coverage separately for each node type (Mondrian guarantee)."""
    coverages = {}
    for ntype in result.lower:
        if test_masks is not None and ntype in test_masks:
            true = labels[ntype][test_masks[ntype]]
        else:
            true = labels[ntype]
        if len(true) == 0:
            coverages[ntype] = 0.0
            continue
        c = np.mean((true >= result.lower[ntype]) & (true <= result.upper[ntype]))
        coverages[ntype] = float(c)
    return coverages


def prediction_set_efficiency(result: ConformalResult) -> Dict[str, float]:
    """Compute average interval width per node type (smaller = more efficient)."""
    widths = {}
    for ntype in result.lower:
        w = result.upper[ntype] - result.lower[ntype]
        widths[ntype] = float(np.mean(w)) if len(w) > 0 else 0.0
    return widths


def mean_interval_width(result: ConformalResult) -> float:
    """Compute overall mean prediction interval width."""
    all_widths = []
    for ntype in result.lower:
        w = result.upper[ntype] - result.lower[ntype]
        all_widths.append(w)
    if not all_widths:
        return 0.0
    combined = np.concatenate(all_widths)
    return float(np.mean(combined)) if len(combined) > 0 else 0.0


def calibration_error(
    result: ConformalResult,
    labels: Dict[str, np.ndarray],
    test_masks: Optional[Dict[str, np.ndarray]] = None,
    n_bins: int = 10,
) -> float:
    """Expected Calibration Error (ECE) for prediction intervals.

    Bins predictions by interval width and measures coverage deviation
    from the target (1 - alpha) in each bin.
    """
    target = 1.0 - result.alpha
    all_widths, all_covered = [], []

    for ntype in result.lower:
        if test_masks is not None and ntype in test_masks:
            true = labels[ntype][test_masks[ntype]]
        else:
            true = labels[ntype]
        widths = result.upper[ntype] - result.lower[ntype]
        covered = (true >= result.lower[ntype]) & (true <= result.upper[ntype])
        all_widths.append(widths)
        all_covered.append(covered.astype(float))

    if not all_widths:
        return 0.0

    widths = np.concatenate(all_widths)
    covered = np.concatenate(all_covered)

    bin_edges = np.percentile(widths, np.linspace(0, 100, n_bins + 1))
    ece = 0.0
    total = len(widths)

    for i in range(n_bins):
        lo, hi = bin_edges[i], bin_edges[i + 1]
        if i == n_bins - 1:
            mask = (widths >= lo) & (widths <= hi)
        else:
            mask = (widths >= lo) & (widths < hi)
        if np.sum(mask) == 0:
            continue
        bin_coverage = np.mean(covered[mask])
        bin_weight = np.sum(mask) / total
        ece += bin_weight * abs(bin_coverage - target)

    return float(ece)


def rmse_per_type(
    predictions: Dict[str, np.ndarray],
    labels: Dict[str, np.ndarray],
    test_masks: Optional[Dict[str, np.ndarray]] = None,
) -> Dict[str, float]:
    """Root mean squared error per node type."""
    rmses = {}
    for ntype in predictions:
        if test_masks is not None and ntype in test_masks:
            pred = predictions[ntype][test_masks[ntype]]
            true = labels[ntype][test_masks[ntype]]
        else:
            pred = predictions[ntype]
            true = labels[ntype]
        if len(true) == 0:
            rmses[ntype] = 0.0
            continue
        rmses[ntype] = float(np.sqrt(np.mean((pred - true) ** 2)))
    return rmses


def per_type_ece(
    result: ConformalResult,
    labels: Dict[str, np.ndarray],
    test_masks: Optional[Dict[str, np.ndarray]] = None,
    n_bins: int = 10,
) -> Dict[str, float]:
    """Compute ECE per node type by binning interval widths and measuring
    coverage deviation from the target (1 - alpha).
    """
    out: Dict[str, float] = {}
    target = 1.0 - result.alpha

    for ntype in result.lower:
        if test_masks is not None and ntype in test_masks:
            true = labels[ntype][test_masks[ntype]]
            widths = result.upper[ntype] - result.lower[ntype]
            covered = (true >= result.lower[ntype]) & (true <= result.upper[ntype])
        else:
            true = labels[ntype]
            widths = result.upper[ntype] - result.lower[ntype]
            covered = (true >= result.lower[ntype]) & (true <= result.upper[ntype])

        if len(widths) == 0:
            out[ntype] = 0.0
            continue

        # Use percentile bins similar to global ECE for stability
        bin_edges = np.percentile(widths, np.linspace(0, 100, n_bins + 1))
        ece = 0.0
        total = len(widths)

        for i in range(n_bins):
            lo, hi = bin_edges[i], bin_edges[i + 1]
            if i == n_bins - 1:
                mask = (widths >= lo) & (widths <= hi)
            else:
                mask = (widths >= lo) & (widths < hi)
            if np.sum(mask) == 0:
                continue
            bin_coverage = np.mean(covered[mask].astype(float))
            bin_weight = np.sum(mask) / total
            ece += bin_weight * abs(bin_coverage - target)

        out[ntype] = float(ece)

    return out
