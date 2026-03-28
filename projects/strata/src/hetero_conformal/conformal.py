"""Conformalized prediction for heterogeneous graphs.

Implements split conformal calibration with Mondrian grouping by node type,
producing prediction intervals with coverage guarantees that hold across
the heterogeneous infrastructure graph.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

import numpy as np


@dataclass
class ConformalResult:
    """Stores conformalized prediction intervals and diagnostics."""

    lower: Dict[str, np.ndarray]
    upper: Dict[str, np.ndarray]
    point_pred: Dict[str, np.ndarray]
    alpha: float
    quantiles: Dict[str, float]


class HeteroConformalCalibrator:
    """Split conformal calibrator with Mondrian grouping by node type.

    After training a HeteroGNN, call ``calibrate()`` on the calibration set
    to compute per-type nonconformity quantiles, then ``predict()`` on the
    test set to obtain prediction intervals with valid coverage.

    Coverage guarantee (Theorem 1 in the paper):
        For each node type t and significance level alpha,
        P(Y_i in C_t(X_i)) >= 1 - alpha
        holds marginally over the calibration + test exchangeability.
    """

    def __init__(self, alpha: float = 0.1):
        """
        Parameters
        ----------
        alpha : float
            Miscoverage level. Default 0.1 gives 90% coverage target.
        """
        if not 0 < alpha < 1:
            raise ValueError(f"alpha must be in (0, 1), got {alpha}")
        self.alpha = alpha
        self._cal_scores: Dict[str, np.ndarray] = {}
        self._quantiles: Dict[str, float] = {}
        self._calibrated = False

    def calibrate(
        self,
        predictions: Dict[str, np.ndarray],
        labels: Dict[str, np.ndarray],
        cal_masks: Dict[str, np.ndarray],
    ) -> Dict[str, float]:
        """Compute per-type conformity quantiles on the calibration set.

        Parameters
        ----------
        predictions : dict
            Point predictions per node type, shape (N_t,).
        labels : dict
            Ground truth labels per node type, shape (N_t,).
        cal_masks : dict
            Boolean calibration masks per node type.

        Returns
        -------
        dict mapping node type -> calibrated quantile value.
        """
        self._cal_scores = {}
        self._quantiles = {}

        for ntype in predictions:
            mask = cal_masks[ntype]
            pred = predictions[ntype][mask]
            true = labels[ntype][mask]
            scores = np.abs(pred - true)
            self._cal_scores[ntype] = scores

            n_cal = len(scores)
            if n_cal == 0:
                self._quantiles[ntype] = float("inf")
                continue

            # Finite-sample corrected quantile: ceil((n+1)(1-alpha)) / n
            level = np.ceil((n_cal + 1) * (1 - self.alpha)) / n_cal
            level = min(level, 1.0)
            q = float(np.quantile(scores, level))
            self._quantiles[ntype] = q

        self._calibrated = True
        return dict(self._quantiles)

    def predict(
        self,
        predictions: Dict[str, np.ndarray],
        test_masks: Optional[Dict[str, np.ndarray]] = None,
    ) -> ConformalResult:
        """Produce conformalized prediction intervals.

        Parameters
        ----------
        predictions : dict
            Point predictions per node type.
        test_masks : dict, optional
            If given, only populate intervals for test nodes.

        Returns
        -------
        ConformalResult with lower/upper bounds per node type.
        """
        if not self._calibrated:
            raise RuntimeError("Must call calibrate() before predict()")

        lower, upper, point = {}, {}, {}

        for ntype in predictions:
            pred = predictions[ntype]
            q = self._quantiles[ntype]
            lo = pred - q
            hi = pred + q

            if test_masks is not None and ntype in test_masks:
                mask = test_masks[ntype]
                lower[ntype] = lo[mask]
                upper[ntype] = hi[mask]
                point[ntype] = pred[mask]
            else:
                lower[ntype] = lo
                upper[ntype] = hi
                point[ntype] = pred

        return ConformalResult(
            lower=lower,
            upper=upper,
            point_pred=point,
            alpha=self.alpha,
            quantiles=dict(self._quantiles),
        )

    def verify_coverage(
        self,
        result: ConformalResult,
        labels: Dict[str, np.ndarray],
        test_masks: Optional[Dict[str, np.ndarray]] = None,
    ) -> Dict[str, float]:
        """Empirically verify coverage on test data.

        Returns
        -------
        dict mapping node type -> empirical coverage fraction.
        """
        coverages = {}
        for ntype in result.lower:
            if test_masks is not None and ntype in test_masks:
                true = labels[ntype][test_masks[ntype]]
            else:
                true = labels[ntype]
            covered = (true >= result.lower[ntype]) & (true <= result.upper[ntype])
            coverages[ntype] = float(np.mean(covered)) if len(covered) > 0 else 0.0
        return coverages


class PropagationAwareCalibrator(HeteroConformalCalibrator):
    """Normalized conformal calibrator with propagation-aware difficulty.

    Uses **normalized nonconformity scores** (Lei & Wasserman, 2014) where
    the normalization factor captures multi-hop error propagation:

        s_i = |y_i - ŷ_i| / σ_i,  where  σ_i = 1 + λ · avg_neighbor_residual_i

    The neighbor residuals are **frozen from the training set only**, so σ_i
    is a deterministic constant per node.  Each calibration/test score s_i
    is therefore a function of only its own (X_i, Y_i) divided by a fixed
    constant, preserving exchangeability (Barber et al., 2022).

    Prediction intervals invert the score:
        C_i = [ŷ_i − q̂ · σ_i,  ŷ_i + q̂ · σ_i]

    Nodes in high-error neighborhoods have larger σ_i → wider intervals,
    matching the physical intuition that error propagates through
    infrastructure coupling.
    """

    def __init__(self, alpha: float = 0.1, neighborhood_weight: float = 0.3):
        super().__init__(alpha)
        self.neighborhood_weight = neighborhood_weight
        self._sigma: Dict[str, np.ndarray] = {}
        # Aggregation method for neighbor difficulty: 'mean', 'median', or 'trimmed'
        self.neighbor_agg: str = "mean"
        # Fraction to trim from each tail when using trimmed mean (0.0-0.5)
        self.trimmed_frac: float = 0.0
        # Minimum floor for sigma values (helps avoid extremely small denominators)
        self.floor_sigma: float = 0.0

    def calibrate_with_propagation(
        self,
        predictions: Dict[str, np.ndarray],
        labels: Dict[str, np.ndarray],
        cal_masks: Dict[str, np.ndarray],
        train_masks: Dict[str, np.ndarray],
        edge_index: Dict[Tuple[str, str, str], np.ndarray],
        num_nodes: Dict[str, int],
    ) -> Dict[str, float]:
        """Calibrate using normalized nonconformity scores.

        The difficulty estimate σ_i uses ONLY training-set residuals
        (frozen before calibration), so the conformal guarantee is preserved.

        Parameters
        ----------
        predictions, labels, cal_masks : as in base class
        train_masks : dict
            Boolean training masks per node type. Neighbor residuals
            are drawn exclusively from training nodes.
        edge_index : dict
            Edge index arrays per edge type.
        num_nodes : dict
            Number of nodes per type.
        """
        self._cal_scores = {}
        self._quantiles = {}

        # Compute frozen training-set residuals (these are constants)
        train_residuals: Dict[str, np.ndarray] = {}
        for ntype in predictions:
            residuals = np.abs(predictions[ntype] - labels[ntype])
            frozen = np.zeros_like(residuals)
            frozen[train_masks[ntype]] = residuals[train_masks[ntype]]
            train_residuals[ntype] = frozen

        # Build per-node frozen neighbor aggregation (using only training residuals)
        frozen_neighbor_avg: Dict[str, np.ndarray] = {}
        for ntype in predictions:
            n = num_nodes[ntype]

            if self.neighbor_agg == "mean":
                neighbor_sum = np.zeros(n, dtype=np.float64)
                neighbor_count = np.zeros(n, dtype=np.float64)
                for (src_type, rel, dst_type), ei in edge_index.items():
                    if dst_type != ntype or ei.shape[1] == 0:
                        continue
                    src_idx, dst_idx = ei[0], ei[1]
                    # Vectorized: filter edges where source is in training set
                    train_mask_src = train_masks[src_type][src_idx]
                    valid_src = src_idx[train_mask_src]
                    valid_dst = dst_idx[train_mask_src]
                    np.add.at(neighbor_sum, valid_dst, train_residuals[src_type][valid_src])
                    np.add.at(neighbor_count, valid_dst, 1.0)
                safe_count = np.maximum(neighbor_count, 1.0)
                frozen_neighbor_avg[ntype] = (neighbor_sum / safe_count).astype(np.float32)
            else:
                # For 'median' or 'trimmed' aggregation, collect neighbor residual lists
                neighbor_lists: list[list[float]] = [[] for _ in range(n)]
                for (src_type, rel, dst_type), ei in edge_index.items():
                    if dst_type != ntype or ei.shape[1] == 0:
                        continue
                    src_idx, dst_idx = ei[0], ei[1]
                    train_mask_src = train_masks[src_type][src_idx]
                    valid_src = src_idx[train_mask_src]
                    valid_dst = dst_idx[train_mask_src]
                    valid_resid = train_residuals[src_type][valid_src]
                    for e in range(len(valid_dst)):
                        neighbor_lists[int(valid_dst[e])].append(float(valid_resid[e]))

                agg = np.zeros(n, dtype=np.float32)
                for i in range(n):
                    vals = neighbor_lists[i]
                    if not vals:
                        agg[i] = 0.0
                        continue
                    arr = np.array(vals, dtype=np.float64)
                    if self.neighbor_agg == "median":
                        agg[i] = float(np.median(arr))
                    else:
                        # trimmed mean
                        frac = float(max(0.0, min(0.5, getattr(self, "trimmed_frac", 0.0))))
                        if frac <= 0.0:
                            agg[i] = float(np.mean(arr))
                        else:
                            k = int(len(arr) * frac)
                            if k * 2 >= len(arr):
                                agg[i] = float(np.mean(arr))
                            else:
                                arr_sorted = np.sort(arr)
                                trimmed = arr_sorted[k: len(arr) - k]
                                agg[i] = float(np.mean(trimmed))
                frozen_neighbor_avg[ntype] = agg.astype(np.float32)

        # Compute per-node difficulty σ_i = 1 + λ * max(frozen_avg_i, floor)
        # The floor applies to the neighbor contribution, ensuring nodes with
        # few or no training-set neighbors still get a minimum difficulty bump.
        for ntype in predictions:
            avg = frozen_neighbor_avg[ntype]
            floor = float(getattr(self, "floor_sigma", 0.0) or 0.0)
            if floor > 0.0:
                avg = np.maximum(avg, floor)
            sig = 1.0 + self.neighborhood_weight * avg
            self._sigma[ntype] = sig

        # Compute normalized nonconformity scores on calibration nodes
        for ntype in predictions:
            mask = cal_masks[ntype]
            raw_scores = np.abs(predictions[ntype][mask] - labels[ntype][mask])
            sigma_cal = self._sigma[ntype][mask]
            normalized = raw_scores / sigma_cal
            self._cal_scores[ntype] = normalized

            n_cal = len(normalized)
            if n_cal == 0:
                self._quantiles[ntype] = float("inf")
                continue

            level = np.ceil((n_cal + 1) * (1 - self.alpha)) / n_cal
            level = min(level, 1.0)
            self._quantiles[ntype] = float(np.quantile(normalized, level))

        self._calibrated = True
        self._frozen_neighbor_avg = frozen_neighbor_avg
        return dict(self._quantiles)

    def predict(
        self,
        predictions: Dict[str, np.ndarray],
        test_masks: Optional[Dict[str, np.ndarray]] = None,
    ) -> ConformalResult:
        """Produce conformalized prediction intervals with locally-adaptive widths.

        Interval at node i: [ŷ_i − q̂ · σ_i, ŷ_i + q̂ · σ_i]
        where σ_i = 1 + λ · frozen_neighbor_avg_i.
        """
        if not self._calibrated:
            raise RuntimeError("Must call calibrate_with_propagation() first")

        lower, upper, point = {}, {}, {}

        for ntype in predictions:
            pred = predictions[ntype]
            q = self._quantiles[ntype]
            sigma = self._sigma[ntype]
            width = q * sigma
            lo = pred - width
            hi = pred + width

            if test_masks is not None and ntype in test_masks:
                mask = test_masks[ntype]
                lower[ntype] = lo[mask]
                upper[ntype] = hi[mask]
                point[ntype] = pred[mask]
            else:
                lower[ntype] = lo
                upper[ntype] = hi
                point[ntype] = pred

        return ConformalResult(
            lower=lower,
            upper=upper,
            point_pred=point,
            alpha=self.alpha,
            quantiles=dict(self._quantiles),
        )
