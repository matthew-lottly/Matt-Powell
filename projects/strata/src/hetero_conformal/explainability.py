"""Explainability and interpretability tools for STRATA.

Provides:
- Feature importance for conformal calibration
- Interval decomposition (what contributes to interval width)
- Calibration curve visualization data
- Node-level uncertainty attribution
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

import numpy as np

from .conformal import ConformalResult


def interval_decomposition(
    result: ConformalResult,
    sigma: Optional[Dict[str, np.ndarray]] = None,
    test_masks: Optional[Dict[str, np.ndarray]] = None,
) -> Dict[str, Dict[str, np.ndarray]]:
    """Decompose prediction interval width into components.

    For normalized conformal: width_i = 2 * q * sigma_i
    Returns per-node breakdown of: base_width (from q), sigma_contribution.

    Parameters
    ----------
    result : ConformalResult
    sigma : dict, optional
        Per-node normalization factors.
    test_masks : dict, optional
        If given, only decompose test nodes.

    Returns
    -------
    dict mapping ntype -> {
        'total_width': array,
        'base_quantile': float (the q value),
        'sigma_values': array (if sigma provided),
        'sigma_contribution_pct': array (% of width due to sigma variation),
    }
    """
    out: Dict[str, Dict[str, np.ndarray]] = {}
    for ntype in result.lower:
        entry: Dict[str, np.ndarray] = {}

        if test_masks is not None and ntype in test_masks:
            lo = result.lower[ntype]
            hi = result.upper[ntype]
        else:
            lo = result.lower[ntype]
            hi = result.upper[ntype]

        total_width = hi - lo
        entry["total_width"] = total_width

        q = result.quantiles.get(ntype, 1.0)
        entry["base_quantile"] = np.full_like(total_width, q)

        if sigma is not None and ntype in sigma:
            sig = sigma[ntype]
            if test_masks is not None and ntype in test_masks:
                sig = sig[test_masks[ntype]]
            entry["sigma_values"] = sig
            # sigma contribution: how much wider/narrower than uniform sigma=1
            mean_sigma = float(np.mean(sig)) if len(sig) > 0 else 1.0
            if mean_sigma > 0:
                entry["sigma_contribution_pct"] = (sig / mean_sigma - 1.0) * 100
            else:
                entry["sigma_contribution_pct"] = np.zeros_like(sig)

        out[ntype] = entry
    return out


def calibration_curve_data(
    result: ConformalResult,
    labels: Dict[str, np.ndarray],
    test_masks: Optional[Dict[str, np.ndarray]] = None,
    n_alpha_points: int = 20,
) -> Dict[str, np.ndarray]:
    """Compute calibration curve: expected coverage vs actual across alpha levels.

    Returns data suitable for plotting a calibration curve.
    A perfectly calibrated method should have actual_coverage ≈ expected_coverage.

    Parameters
    ----------
    result : ConformalResult
    labels : dict
    test_masks : dict, optional
    n_alpha_points : int
        Number of alpha levels to evaluate.

    Returns
    -------
    dict with 'expected_coverage', 'actual_coverage' arrays.
    """
    # Collect all residuals and widths
    all_residuals: list[np.ndarray] = []
    all_half_widths: list[np.ndarray] = []

    for ntype in result.lower:
        if test_masks is not None and ntype in test_masks:
            true = labels[ntype][test_masks[ntype]]
        else:
            true = labels[ntype]
        point = result.point_pred[ntype]
        half_w = (result.upper[ntype] - result.lower[ntype]) / 2
        resid = np.abs(true - point)
        all_residuals.append(resid)
        all_half_widths.append(half_w)

    residuals = np.concatenate(all_residuals)
    half_widths = np.concatenate(all_half_widths)

    if len(residuals) == 0:
        return {"expected_coverage": np.array([]), "actual_coverage": np.array([])}

    # Evaluate at different threshold fractions
    alphas = np.linspace(0.01, 0.99, n_alpha_points)
    expected = 1 - alphas
    actual = np.zeros(n_alpha_points)

    max_hw = np.max(half_widths) if len(half_widths) > 0 else 1.0
    for i, a in enumerate(alphas):
        threshold = np.quantile(half_widths, 1 - a) if len(half_widths) > 0 else max_hw
        covered = np.mean(residuals <= threshold)
        actual[i] = covered

    return {"expected_coverage": expected, "actual_coverage": actual}


def uncertainty_attribution(
    sigma: Dict[str, np.ndarray],
    node_features: Dict[str, np.ndarray],
    test_masks: Optional[Dict[str, np.ndarray]] = None,
    top_k: int = 5,
) -> Dict[str, Dict[str, np.ndarray]]:
    """Attribute uncertainty (sigma) to input features via correlation analysis.

    For each node type, computes the Pearson correlation between
    each feature dimension and the sigma value, identifying which
    features are most associated with high uncertainty.

    Parameters
    ----------
    sigma : dict
        Per-node normalization factors.
    node_features : dict
        Node feature matrices.
    test_masks : dict, optional
    top_k : int
        Number of top correlated features to return.

    Returns
    -------
    dict mapping ntype -> {
        'feature_correlations': (D,) array of correlations,
        'top_features': (top_k,) array of feature indices,
        'top_correlations': (top_k,) array of correlation values,
    }
    """
    out: Dict[str, Dict[str, np.ndarray]] = {}
    for ntype in sigma:
        sig = sigma[ntype]
        feat = node_features[ntype]
        if test_masks is not None and ntype in test_masks:
            sig = sig[test_masks[ntype]]
            feat = feat[test_masks[ntype]]

        if len(sig) < 3 or feat.shape[1] == 0:
            out[ntype] = {
                "feature_correlations": np.array([]),
                "top_features": np.array([], dtype=int),
                "top_correlations": np.array([]),
            }
            continue

        correlations = np.zeros(feat.shape[1])
        for d in range(feat.shape[1]):
            std_f = np.std(feat[:, d])
            std_s = np.std(sig)
            if std_f > 1e-10 and std_s > 1e-10:
                correlations[d] = float(np.corrcoef(feat[:, d], sig)[0, 1])

        k = min(top_k, len(correlations))
        top_idx = np.argsort(np.abs(correlations))[::-1][:k]

        out[ntype] = {
            "feature_correlations": correlations,
            "top_features": top_idx,
            "top_correlations": correlations[top_idx],
        }
    return out


def coverage_by_feature_bin(
    result: ConformalResult,
    labels: Dict[str, np.ndarray],
    node_features: Dict[str, np.ndarray],
    feature_idx: int,
    test_masks: Optional[Dict[str, np.ndarray]] = None,
    n_bins: int = 5,
) -> Dict[str, Dict[str, np.ndarray]]:
    """Compute coverage stratified by a specific feature value.

    Useful for detecting if conformal coverage varies with
    a particular input feature (which would indicate conditional
    miscoverage).

    Parameters
    ----------
    feature_idx : int
        Index of the feature to bin by.
    n_bins : int
        Number of bins.

    Returns
    -------
    dict mapping ntype -> {'bin_centers', 'coverage', 'bin_sizes'}
    """
    out: Dict[str, Dict[str, np.ndarray]] = {}
    for ntype in result.lower:
        if test_masks is not None and ntype in test_masks:
            true = labels[ntype][test_masks[ntype]]
            feat_vals = node_features[ntype][test_masks[ntype], feature_idx]
        else:
            true = labels[ntype]
            feat_vals = node_features[ntype][:, feature_idx]

        covered = (true >= result.lower[ntype]) & (true <= result.upper[ntype])

        if len(feat_vals) == 0:
            out[ntype] = {
                "bin_centers": np.array([]),
                "coverage": np.array([]),
                "bin_sizes": np.array([], dtype=int),
            }
            continue

        edges = np.percentile(feat_vals, np.linspace(0, 100, n_bins + 1))
        centers, coverages, sizes = [], [], []
        for i in range(n_bins):
            lo, hi = edges[i], edges[i + 1]
            sel = (feat_vals >= lo) & (feat_vals <= hi) if i == n_bins - 1 else (feat_vals >= lo) & (feat_vals < hi)
            n_sel = int(np.sum(sel))
            if n_sel > 0:
                coverages.append(float(np.mean(covered[sel])))
            else:
                coverages.append(float("nan"))
            centers.append((lo + hi) / 2)
            sizes.append(n_sel)

        out[ntype] = {
            "bin_centers": np.array(centers),
            "coverage": np.array(coverages),
            "bin_sizes": np.array(sizes, dtype=int),
        }
    return out
