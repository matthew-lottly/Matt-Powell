"""Online and streaming conformal prediction for STRATA.

Provides:
- StreamingConformalCalibrator: online conformal prediction with sliding window
- AdaptiveConformalCalibrator: distribution-shift-aware conformal prediction

These methods handle temporal non-stationarity common in infrastructure
monitoring (e.g., seasonal load patterns, evolving network topology).

References:
    - Gibbs & Candes (2021): Adaptive Conformal Inference Under Distribution Shift
    - Zaffran et al. (2022): Adaptive Conformal Predictions for Time Series
"""

from __future__ import annotations

from collections import deque
from typing import Dict, Optional

import numpy as np

from .conformal import ConformalResult


class StreamingConformalCalibrator:
    """Online conformal prediction with a sliding window of scores.

    Maintains a fixed-size window of recent nonconformity scores and
    recomputes quantiles on the fly. Suitable for monitoring scenarios
    where new data arrives continuously.

    Parameters
    ----------
    alpha : float
        Target miscoverage rate.
    window_size : int
        Number of recent scores to keep. Larger = more stable but slower adaptation.
    """

    def __init__(self, alpha: float = 0.1, window_size: int = 500):
        self.alpha = alpha
        self.window_size = window_size
        self._score_windows: Dict[str, deque] = {}
        self._quantiles: Dict[str, float] = {}

    def update(
        self,
        predictions: Dict[str, np.ndarray],
        labels: Dict[str, np.ndarray],
        sigma: Optional[Dict[str, np.ndarray]] = None,
    ) -> Dict[str, float]:
        """Update with new observations and recompute quantiles.

        Parameters
        ----------
        predictions : dict
            New point predictions per node type.
        labels : dict
            New ground truth labels per node type.
        sigma : dict, optional
            Per-node normalization factors. If None, uses |residual| directly.

        Returns
        -------
        dict mapping node type -> updated quantile.
        """
        for ntype in predictions:
            if ntype not in self._score_windows:
                self._score_windows[ntype] = deque(maxlen=self.window_size)

            residuals = np.abs(predictions[ntype] - labels[ntype])
            if sigma is not None and ntype in sigma:
                scores = residuals / np.maximum(sigma[ntype], 1e-8)
            else:
                scores = residuals

            for s in scores:
                self._score_windows[ntype].append(float(s))

            # Recompute quantile from window
            window = np.array(self._score_windows[ntype])
            n = len(window)
            level = min(np.ceil((n + 1) * (1 - self.alpha)) / n, 1.0)
            self._quantiles[ntype] = float(np.quantile(window, level))

        return dict(self._quantiles)

    def predict(
        self,
        predictions: Dict[str, np.ndarray],
        sigma: Optional[Dict[str, np.ndarray]] = None,
    ) -> ConformalResult:
        """Produce prediction intervals using current quantiles.

        Parameters
        ----------
        predictions : dict
            Point predictions per node type.
        sigma : dict, optional
            Per-node normalization factors.
        """
        if not self._quantiles:
            raise RuntimeError("Must call update() before predict()")

        lower, upper, point = {}, {}, {}
        for ntype in predictions:
            pred = predictions[ntype]
            q = self._quantiles.get(ntype, float("inf"))
            if sigma is not None and ntype in sigma:
                width = q * sigma[ntype]
            else:
                width = q
            lower[ntype] = pred - width
            upper[ntype] = pred + width
            point[ntype] = pred

        return ConformalResult(
            lower=lower, upper=upper, point_pred=point,
            alpha=self.alpha, quantiles=dict(self._quantiles),
        )

    @property
    def window_sizes(self) -> Dict[str, int]:
        """Current number of scores in each window."""
        return {nt: len(w) for nt, w in self._score_windows.items()}


class AdaptiveConformalCalibrator:
    """Distribution-shift-aware conformal prediction.

    Implements the adaptive conformal inference (ACI) method of
    Gibbs & Candes (2021), which adjusts the effective alpha based
    on recent coverage performance.

    When coverage is below target, alpha is decreased (wider intervals).
    When coverage is above target, alpha is increased (narrower intervals).

    Parameters
    ----------
    alpha : float
        Target miscoverage rate.
    gamma : float
        Step size for alpha adjustment (default 0.005).
        Larger = faster adaptation but more volatile.
    window_size : int
        Number of recent scores to maintain.
    """

    def __init__(
        self,
        alpha: float = 0.1,
        gamma: float = 0.005,
        window_size: int = 500,
    ):
        self.alpha_target = alpha
        self.gamma = gamma
        self.window_size = window_size
        self._alpha_t: float = alpha
        self._score_windows: Dict[str, deque] = {}
        self._quantiles: Dict[str, float] = {}
        self._alpha_history: list[float] = [alpha]

    def update(
        self,
        predictions: Dict[str, np.ndarray],
        labels: Dict[str, np.ndarray],
        sigma: Optional[Dict[str, np.ndarray]] = None,
    ) -> Dict[str, float]:
        """Update scores and adapt alpha based on recent coverage.

        Parameters
        ----------
        predictions, labels, sigma : see StreamingConformalCalibrator.update
        """
        # Check coverage of new batch with CURRENT quantiles
        if self._quantiles:
            total, covered = 0, 0
            for ntype in predictions:
                q = self._quantiles.get(ntype, float("inf"))
                if sigma is not None and ntype in sigma:
                    width = q * sigma[ntype]
                else:
                    width = q
                lo = predictions[ntype] - width
                hi = predictions[ntype] + width
                c = np.sum((labels[ntype] >= lo) & (labels[ntype] <= hi))
                covered += c
                total += len(labels[ntype])
            if total > 0:
                empirical_coverage = covered / total
                # ACI update: alpha_t+1 = alpha_t + gamma * (alpha_target - err_t)
                err_t = 1.0 - empirical_coverage
                self._alpha_t = self._alpha_t + self.gamma * (self.alpha_target - err_t)
                self._alpha_t = np.clip(self._alpha_t, 0.001, 0.5)
                self._alpha_history.append(float(self._alpha_t))

        # Update score windows
        for ntype in predictions:
            if ntype not in self._score_windows:
                self._score_windows[ntype] = deque(maxlen=self.window_size)

            residuals = np.abs(predictions[ntype] - labels[ntype])
            if sigma is not None and ntype in sigma:
                scores = residuals / np.maximum(sigma[ntype], 1e-8)
            else:
                scores = residuals

            for s in scores:
                self._score_windows[ntype].append(float(s))

            window = np.array(self._score_windows[ntype])
            n = len(window)
            level = min(np.ceil((n + 1) * (1 - self._alpha_t)) / n, 1.0)
            self._quantiles[ntype] = float(np.quantile(window, level))

        return dict(self._quantiles)

    def predict(
        self,
        predictions: Dict[str, np.ndarray],
        sigma: Optional[Dict[str, np.ndarray]] = None,
    ) -> ConformalResult:
        """Produce prediction intervals using adaptive quantiles."""
        if not self._quantiles:
            raise RuntimeError("Must call update() before predict()")

        lower, upper, point = {}, {}, {}
        for ntype in predictions:
            pred = predictions[ntype]
            q = self._quantiles.get(ntype, float("inf"))
            if sigma is not None and ntype in sigma:
                width = q * sigma[ntype]
            else:
                width = q
            lower[ntype] = pred - width
            upper[ntype] = pred + width
            point[ntype] = pred

        return ConformalResult(
            lower=lower, upper=upper, point_pred=point,
            alpha=self._alpha_t, quantiles=dict(self._quantiles),
        )

    @property
    def current_alpha(self) -> float:
        return self._alpha_t

    @property
    def alpha_history(self) -> list[float]:
        return list(self._alpha_history)
