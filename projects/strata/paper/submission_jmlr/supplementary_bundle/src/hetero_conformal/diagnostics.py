"""Diagnostics and statistical tests for conformal prediction evaluation.

Provides tools for:
- Calibration diagnostics (σ vs hit-rate, calibration curves)
- Conditional coverage analysis (by width decile, by node degree)
- Bootstrap confidence intervals for all metrics
- Paired statistical tests (Wilcoxon signed-rank)
- Non-exchangeability detection tests
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy import stats as sp_stats

from .conformal import ConformalResult
from .metrics import (
    calibration_error,
    marginal_coverage,
    mean_interval_width,
    type_conditional_coverage,
)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Sigma-vs-hit-rate analysis
# ─────────────────────────────────────────────────────────────────────────────

def sigma_vs_hitrate(
    sigma: Dict[str, np.ndarray],
    result: ConformalResult,
    labels: Dict[str, np.ndarray],
    test_masks: Dict[str, np.ndarray],
    n_bins: int = 10,
) -> Dict[str, Dict[str, np.ndarray]]:
    """Compute per-bin hit-rate as a function of σ.

    For each node type, bins test nodes by σ value and computes
    the empirical coverage in each bin. Ideally coverage should
    be uniform (≈ 1 - α) across all σ bins.

    Returns
    -------
    dict mapping ntype → {
        'sigma_bin_centers': np.ndarray,
        'hitrate': np.ndarray,
        'bin_sizes': np.ndarray,
    }
    """
    out: Dict[str, Dict[str, np.ndarray]] = {}
    for ntype in result.lower:
        mask = test_masks[ntype]
        sig = sigma[ntype][mask] if sigma[ntype].shape[0] > result.lower[ntype].shape[0] else sigma[ntype]
        true = labels[ntype][mask]
        covered = (true >= result.lower[ntype]) & (true <= result.upper[ntype])

        if len(sig) == 0:
            out[ntype] = {
                "sigma_bin_centers": np.array([]),
                "hitrate": np.array([]),
                "bin_sizes": np.array([]),
            }
            continue

        bin_edges = np.percentile(sig, np.linspace(0, 100, n_bins + 1))
        centers = []
        hitrates = []
        sizes = []
        for i in range(n_bins):
            lo, hi = bin_edges[i], bin_edges[i + 1]
            sel = (sig >= lo) & (sig <= hi) if i == n_bins - 1 else (sig >= lo) & (sig < hi)
            if np.sum(sel) == 0:
                continue
            centers.append((lo + hi) / 2)
            hitrates.append(float(np.mean(covered[sel])))
            sizes.append(int(np.sum(sel)))

        out[ntype] = {
            "sigma_bin_centers": np.array(centers),
            "hitrate": np.array(hitrates),
            "bin_sizes": np.array(sizes),
        }
    return out


# ─────────────────────────────────────────────────────────────────────────────
# 2. Conditional coverage by width decile
# ─────────────────────────────────────────────────────────────────────────────

def conditional_coverage_by_width_decile(
    result: ConformalResult,
    labels: Dict[str, np.ndarray],
    test_masks: Optional[Dict[str, np.ndarray]] = None,
    n_deciles: int = 10,
) -> Dict[str, np.ndarray]:
    """Compute coverage within each interval-width decile.

    Returns dict with keys 'decile_centers', 'coverage', 'width_edges'.
    Ideally coverage should be ≈ 1-α in every decile.
    """
    all_widths = []
    all_covered = []

    for ntype in result.lower:
        true = labels[ntype][test_masks[ntype]] if test_masks else labels[ntype]
        widths = result.upper[ntype] - result.lower[ntype]
        covered = (true >= result.lower[ntype]) & (true <= result.upper[ntype])
        all_widths.append(widths)
        all_covered.append(covered.astype(float))

    widths = np.concatenate(all_widths)
    covered = np.concatenate(all_covered)

    edges = np.percentile(widths, np.linspace(0, 100, n_deciles + 1))
    coverages = []
    centers = []

    for i in range(n_deciles):
        lo, hi = edges[i], edges[i + 1]
        sel = (widths >= lo) & (widths <= hi) if i == n_deciles - 1 else (widths >= lo) & (widths < hi)
        if np.sum(sel) == 0:
            coverages.append(float("nan"))
        else:
            coverages.append(float(np.mean(covered[sel])))
        centers.append((lo + hi) / 2)

    return {
        "decile_centers": np.array(centers),
        "coverage": np.array(coverages),
        "width_edges": edges,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 3. Conditional coverage by node degree
# ─────────────────────────────────────────────────────────────────────────────

def conditional_coverage_by_degree(
    result: ConformalResult,
    labels: Dict[str, np.ndarray],
    test_masks: Dict[str, np.ndarray],
    edge_index: Dict,
    num_nodes: Dict[str, int],
    n_bins: int = 5,
) -> Dict[str, Dict[str, np.ndarray]]:
    """Compute coverage as a function of node degree.

    Nodes with higher degree have more neighbors contributing to σ.
    This diagnostic reveals whether propagation-aware calibration
    adapts well to connectivity patterns.
    """
    # Compute degree per node type (vectorized)
    degree: Dict[str, np.ndarray] = {}
    for ntype in num_nodes:
        degree[ntype] = np.zeros(num_nodes[ntype], dtype=np.int64)
    for (src_t, rel, dst_t), ei in edge_index.items():
        if ei.shape[1] == 0:
            continue
        dst_idx = ei[1]
        np.add.at(degree[dst_t], dst_idx, 1)

    out: Dict[str, Dict[str, np.ndarray]] = {}
    for ntype in result.lower:
        mask = test_masks[ntype]
        deg = degree[ntype][mask]
        true = labels[ntype][mask]
        covered = (true >= result.lower[ntype]) & (true <= result.upper[ntype])

        if len(deg) == 0:
            out[ntype] = {"degree_bins": np.array([]), "coverage": np.array([])}
            continue

        unique_degs = np.unique(deg)
        if len(unique_degs) <= n_bins:
            bins = unique_degs
            coverages = []
            for d_val in bins:
                sel = deg == d_val
                if np.sum(sel) > 0:
                    coverages.append(float(np.mean(covered[sel])))
                else:
                    coverages.append(float("nan"))
            out[ntype] = {
                "degree_bins": bins,
                "coverage": np.array(coverages),
            }
        else:
            edges = np.percentile(deg, np.linspace(0, 100, n_bins + 1))
            bins_c = []
            coverages = []
            for i in range(n_bins):
                lo, hi = edges[i], edges[i + 1]
                sel = (deg >= lo) & (deg <= hi) if i == n_bins - 1 else (deg >= lo) & (deg < hi)
                if np.sum(sel) > 0:
                    coverages.append(float(np.mean(covered[sel])))
                else:
                    coverages.append(float("nan"))
                bins_c.append((lo + hi) / 2)
            out[ntype] = {
                "degree_bins": np.array(bins_c),
                "coverage": np.array(coverages),
            }
    return out


# ─────────────────────────────────────────────────────────────────────────────
# 4. Bootstrap confidence intervals
# ─────────────────────────────────────────────────────────────────────────────

def bootstrap_ci(
    metric_fn,
    result: ConformalResult,
    labels: Dict[str, np.ndarray],
    test_masks: Dict[str, np.ndarray],
    n_bootstrap: int = 1000,
    ci_level: float = 0.95,
    seed: int = 42,
) -> Dict[str, Any]:
    """Bootstrap confidence interval for a conformal metric.

    Parameters
    ----------
    metric_fn : callable
        Function (result, labels, test_masks) → float.
        e.g. marginal_coverage.
    n_bootstrap : int
        Number of bootstrap resamples.
    ci_level : float
        Confidence level (0.95 = 95% CI).

    Returns
    -------
    dict with 'point', 'ci_lower', 'ci_upper', 'se', 'samples'.
    """
    rng = np.random.default_rng(seed)
    point_est = metric_fn(result, labels, test_masks)

    # Collect all test node data
    all_true: List[np.ndarray] = []
    all_lo: List[np.ndarray] = []
    all_hi: List[np.ndarray] = []
    all_width: List[np.ndarray] = []
    for ntype in result.lower:
        mask = test_masks[ntype]
        all_true.append(labels[ntype][mask])
        all_lo.append(result.lower[ntype])
        all_hi.append(result.upper[ntype])
        all_width.append(result.upper[ntype] - result.lower[ntype])

    true = np.concatenate(all_true)
    lo = np.concatenate(all_lo)
    hi = np.concatenate(all_hi)
    n = len(true)

    samples = []
    for _ in range(n_bootstrap):
        idx = rng.choice(n, size=n, replace=True)
        t, l, h = true[idx], lo[idx], hi[idx]
        covered = np.mean((t >= l) & (t <= h))
        samples.append(float(covered))

    samples_arr = np.array(samples)
    alpha = 1 - ci_level
    ci_lo = float(np.percentile(samples_arr, 100 * alpha / 2))
    ci_hi = float(np.percentile(samples_arr, 100 * (1 - alpha / 2)))

    return {
        "point": point_est,
        "ci_lower": ci_lo,
        "ci_upper": ci_hi,
        "se": float(np.std(samples_arr)),
        "samples": samples_arr,
    }


def bootstrap_width_ci(
    result: ConformalResult,
    n_bootstrap: int = 1000,
    ci_level: float = 0.95,
    seed: int = 42,
) -> Dict[str, Any]:
    """Bootstrap CI for mean interval width."""
    rng = np.random.default_rng(seed)
    all_w = np.concatenate([result.upper[nt] - result.lower[nt] for nt in result.lower])
    n = len(all_w)
    point = float(np.mean(all_w))
    samples = []
    for _ in range(n_bootstrap):
        idx = rng.choice(n, size=n, replace=True)
        samples.append(float(np.mean(all_w[idx])))
    arr = np.array(samples)
    a = 1 - ci_level
    return {
        "point": point,
        "ci_lower": float(np.percentile(arr, 100 * a / 2)),
        "ci_upper": float(np.percentile(arr, 100 * (1 - a / 2))),
        "se": float(np.std(arr)),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 5. Paired statistical tests
# ─────────────────────────────────────────────────────────────────────────────

def paired_wilcoxon_test(
    metric_a: List[float],
    metric_b: List[float],
    alternative: str = "two-sided",
) -> Dict[str, float]:
    """Wilcoxon signed-rank test for paired metric comparisons.

    Compares two methods across multiple seeds to determine
    statistical significance.

    Parameters
    ----------
    metric_a, metric_b : list of float
        Metric values from method A and B (one per seed).
    alternative : str
        'two-sided', 'greater', or 'less'.

    Returns
    -------
    dict with 'statistic', 'p_value', 'significant_0.05'.
    """
    a = np.array(metric_a)
    b = np.array(metric_b)
    if len(a) != len(b) or len(a) < 5:
        return {"statistic": float("nan"), "p_value": 1.0, "significant_0.05": False}

    diff = a - b
    if np.all(diff == 0):
        return {"statistic": 0.0, "p_value": 1.0, "significant_0.05": False}

    result = sp_stats.wilcoxon(a, b, alternative=alternative)
    stat_val: float = float(getattr(result, 'statistic', 0.0))
    p_val: float = float(getattr(result, 'pvalue', 1.0))
    return {
        "statistic": stat_val,
        "p_value": p_val,
        "significant_0.05": p_val < 0.05,
    }


def paired_t_test(
    metric_a: List[float],
    metric_b: List[float],
) -> Dict[str, float]:
    """Paired t-test for metric comparison across seeds."""
    a = np.array(metric_a)
    b = np.array(metric_b)
    if len(a) != len(b) or len(a) < 2:
        return {"statistic": float("nan"), "p_value": 1.0, "significant_0.05": False}
    stat, pval = sp_stats.ttest_rel(a, b)
    return {
        "statistic": float(stat),
        "p_value": float(pval),
        "significant_0.05": bool(pval < 0.05),
    }


def multi_method_friedman_test(
    method_metrics: Dict[str, List[float]],
) -> Dict[str, float]:
    """Friedman test for comparing multiple methods across seeds.

    Non-parametric alternative to repeated-measures ANOVA.
    """
    arrays = list(method_metrics.values())
    if len(arrays) < 3 or any(len(a) < 3 for a in arrays):
        return {"statistic": float("nan"), "p_value": 1.0}
    stat, pval = sp_stats.friedmanchisquare(*arrays)
    return {"statistic": float(stat), "p_value": float(pval)}


# ─────────────────────────────────────────────────────────────────────────────
# 6. Non-exchangeability detection
# ─────────────────────────────────────────────────────────────────────────────

def nonexchangeability_test(
    scores: np.ndarray,
    n_permutations: int = 10000,
    seed: int = 42,
) -> Dict[str, float]:
    """Test for non-exchangeability using a runs test.

    Checks whether conformal scores exhibit sequential dependence
    that would violate the exchangeability assumption.

    Uses the Wald-Wolfowitz runs test on binarized scores
    (above/below median).

    Returns
    -------
    dict with 'statistic', 'p_value', 'n_runs', 'expected_runs'.
    """
    if len(scores) < 10:
        return {
            "statistic": float("nan"),
            "p_value": 1.0,
            "n_runs": 0,
            "expected_runs": 0.0,
        }
    median = np.median(scores)
    binary = (scores >= median).astype(int)
    n1 = int(np.sum(binary))
    n0 = len(binary) - n1

    if n0 == 0 or n1 == 0:
        return {
            "statistic": float("nan"),
            "p_value": 1.0,
            "n_runs": 0,
            "expected_runs": 0.0,
        }

    # Count runs
    n_runs = 1
    for i in range(1, len(binary)):
        if binary[i] != binary[i - 1]:
            n_runs += 1

    # Expected runs under exchangeability
    n = len(binary)
    expected = 1 + 2 * n0 * n1 / n
    var = 2 * n0 * n1 * (2 * n0 * n1 - n) / (n**2 * (n - 1))
    var = max(var, 1e-12)

    z = (n_runs - expected) / np.sqrt(var)
    p_value = 2 * (1 - sp_stats.norm.cdf(abs(z)))

    return {
        "statistic": float(z),
        "p_value": float(p_value),
        "n_runs": n_runs,
        "expected_runs": float(expected),
    }


def spatial_autocorrelation_test(
    scores: np.ndarray,
    positions: np.ndarray,
    k_neighbors: int = 5,
) -> Dict[str, float]:
    """Moran's I test for spatial autocorrelation in conformal scores.

    Detects whether nearby nodes have correlated scores, which would
    indicate spatial non-exchangeability.

    Parameters
    ----------
    scores : array of shape (N,)
    positions : array of shape (N, 2) — node coordinates
    k_neighbors : int
        Number of nearest neighbors for weight matrix.

    Returns
    -------
    dict with 'morans_i', 'z_score', 'p_value'.
    """
    n = len(scores)
    if n < k_neighbors + 1:
        return {"morans_i": float("nan"), "z_score": float("nan"), "p_value": 1.0}

    # Build k-NN weight matrix
    from scipy.spatial import KDTree
    tree = KDTree(positions)
    query_result = tree.query(positions, k=k_neighbors + 1)
    indices_arr: np.ndarray = np.asarray(query_result[1])
    indices = indices_arr[:, 1:]  # exclude self

    # Compute Moran's I
    z = scores - np.mean(scores)
    numerator = 0.0
    s0 = 0.0
    for i in range(n):
        for j_idx in range(k_neighbors):
            j = indices[i, j_idx]
            numerator += z[i] * z[j]
            s0 += 1.0

    denominator = np.sum(z**2)
    if denominator < 1e-12 or s0 < 1:
        return {"morans_i": 0.0, "z_score": 0.0, "p_value": 1.0}

    morans_i = (n / s0) * (numerator / denominator)

    # Expected under null
    ei = -1.0 / (n - 1)
    # Approximate z-score
    var_i = 1.0 / (n - 1)  # simplified
    z_score = (morans_i - ei) / np.sqrt(max(var_i, 1e-12))
    p_value = 2 * (1 - sp_stats.norm.cdf(abs(z_score)))

    return {
        "morans_i": float(morans_i),
        "z_score": float(z_score),
        "p_value": float(p_value),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 7. Summary report
# ─────────────────────────────────────────────────────────────────────────────

def full_diagnostic_report(
    result: ConformalResult,
    labels: Dict[str, np.ndarray],
    test_masks: Dict[str, np.ndarray],
    sigma: Optional[Dict[str, np.ndarray]] = None,
    edge_index: Optional[Dict] = None,
    num_nodes: Optional[Dict[str, int]] = None,
    n_bootstrap: int = 1000,
) -> Dict[str, Any]:
    """Generate a comprehensive diagnostic report.

    Returns a nested dict with all diagnostic results.
    """
    report: Dict[str, Any] = {}

    # Basic metrics
    report["marginal_coverage"] = marginal_coverage(result, labels, test_masks)
    report["type_coverage"] = type_conditional_coverage(result, labels, test_masks)
    report["mean_width"] = mean_interval_width(result)
    report["ece"] = calibration_error(result, labels, test_masks)

    # Conditional coverage by width decile
    report["width_decile"] = conditional_coverage_by_width_decile(
        result, labels, test_masks
    )

    # Bootstrap CIs
    cov_ci = bootstrap_ci(marginal_coverage, result, labels, test_masks, n_bootstrap)
    report["coverage_ci"] = {
        "point": cov_ci["point"],
        "ci_lower": cov_ci["ci_lower"],
        "ci_upper": cov_ci["ci_upper"],
        "se": cov_ci["se"],
    }
    width_ci = bootstrap_width_ci(result, n_bootstrap)
    report["width_ci"] = {
        "point": width_ci["point"],
        "ci_lower": width_ci["ci_lower"],
        "ci_upper": width_ci["ci_upper"],
        "se": width_ci["se"],
    }

    # Sigma analysis
    if sigma is not None:
        report["sigma_vs_hitrate"] = sigma_vs_hitrate(
            sigma, result, labels, test_masks
        )

    # Degree-based coverage
    if edge_index is not None and num_nodes is not None:
        report["degree_coverage"] = conditional_coverage_by_degree(
            result, labels, test_masks, edge_index, num_nodes
        )

    return report
