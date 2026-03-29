"""Meta-calibrator: learned per-node normalization for conformal prediction.

Trains a lightweight MLP on training-set residuals to predict node-level
uncertainty scaling factors σ_i.  Preserves conformal validity because σ_i
depends only on node features (fixed inputs), not calibration/test labels.

This is the key novelty of STRATA: data-driven, adaptive calibration that
replaces hand-tuned propagation weights with a learned function.

Theory:
    σ_i is frozen after training (deterministic constant per node).
    Normalized scores s_i = |y_i - ŷ_i| / σ_i remain exchangeable
    over the calibration + test split (Barber et al., 2022).

References:
    - Papadopoulos et al. (2008) — Normalized nonconformity measures
    - Romano et al. (2019) — Conformalized heteroscedastic regression
    - Lei & Wasserman (2014) — Distribution-free predictive inference
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn

from .conformal import ConformalResult


class MetaCalibratorNet(nn.Module):
    """MLP that predicts per-node normalization factor σ_i > 0.

    Input:  concatenation of [node_features, prediction, neighbor_stats]
    Output: σ_i ≥ 1 (via softplus + 1)
    """

    def __init__(self, input_dim: int, hidden_dim: int = 32):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 1),
            nn.Softplus(),  # ensures positivity
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x).squeeze(-1) + 1.0  # σ ≥ 1


class MetaCalibrator:
    """Learned per-node normalization for conformal prediction.

    Pipeline:
        1. Compute neighbor difficulty features from TRAINING residuals only
        2. Train a small MLP on training nodes to predict |residual| from
           [features, prediction, neighbor_stats]
        3. Apply trained MLP to ALL nodes → σ_i (frozen constants)
        4. Calibrate on cal set: s_i = |y_i - ŷ_i| / σ_i
        5. Predict: C_i = [ŷ_i − q̂ · σ_i, ŷ_i + q̂ · σ_i]

    The MLP training loss is heteroscedastic Gaussian NLL:
        L(σ) = (y - ŷ)² / (2σ²) + log(σ)
    This naturally learns σ proportional to expected |residual|.
    """

    def __init__(
        self,
        alpha: float = 0.1,
        hidden_dim: int = 32,
        lr: float = 1e-3,
        meta_epochs: int = 200,
    ):
        self.alpha = alpha
        self.hidden_dim = hidden_dim
        self.lr = lr
        self.meta_epochs = meta_epochs
        self.nets: Dict[str, MetaCalibratorNet] = {}
        self.quantiles: Dict[str, float] = {}
        self._sigma: Dict[str, np.ndarray] = {}
        self._calibrated = False

    def _compute_neighbor_stats(
        self,
        predictions: Dict[str, np.ndarray],
        labels: Dict[str, np.ndarray],
        train_masks: Dict[str, np.ndarray],
        edge_index: Dict[Tuple[str, str, str], np.ndarray],
        num_nodes: Dict[str, int],
    ) -> Dict[str, np.ndarray]:
        """Compute per-node neighbor difficulty features using TRAINING residuals.

        Returns dict of (N_t, 4) arrays: [mean_resid, std_resid, max_resid, degree].
        """
        # Frozen training-set residuals
        train_resid: Dict[str, np.ndarray] = {}
        for ntype in predictions:
            r = np.abs(predictions[ntype] - labels[ntype])
            frozen = np.zeros_like(r)
            frozen[train_masks[ntype]] = r[train_masks[ntype]]
            train_resid[ntype] = frozen

        stats: Dict[str, np.ndarray] = {}
        for ntype in predictions:
            n = num_nodes[ntype]
            # Collect neighbor residuals per node
            neighbor_lists: list[list[float]] = [[] for _ in range(n)]
            for (src_type, rel, dst_type), ei in edge_index.items():
                if dst_type != ntype or ei.shape[1] == 0:
                    continue
                src_idx, dst_idx = ei[0], ei[1]
                train_mask_src = train_masks[src_type][src_idx]
                valid_src = src_idx[train_mask_src]
                valid_dst = dst_idx[train_mask_src]
                valid_resid = train_resid[src_type][valid_src]
                for e in range(len(valid_dst)):
                    neighbor_lists[int(valid_dst[e])].append(float(valid_resid[e]))

            # Aggregate to fixed-size features
            feat = np.zeros((n, 4), dtype=np.float32)
            for i in range(n):
                vals = neighbor_lists[i]
                if vals:
                    arr = np.array(vals)
                    feat[i, 0] = np.mean(arr)
                    feat[i, 1] = np.std(arr) if len(arr) > 1 else 0.0
                    feat[i, 2] = np.max(arr)
                    feat[i, 3] = len(arr)
            stats[ntype] = feat
        return stats

    def _build_meta_features(
        self,
        node_features: Dict[str, np.ndarray],
        predictions: Dict[str, np.ndarray],
        neighbor_stats: Dict[str, np.ndarray],
        ntype: str,
    ) -> np.ndarray:
        """Concatenate [node_features, prediction, neighbor_stats] → (N, D+5)."""
        feat = node_features[ntype]
        pred = predictions[ntype].reshape(-1, 1)
        nstats = neighbor_stats[ntype]  # (N, 4)
        return np.column_stack([feat, pred, nstats]).astype(np.float32)

    def calibrate(
        self,
        node_features: Dict[str, np.ndarray],
        predictions: Dict[str, np.ndarray],
        labels: Dict[str, np.ndarray],
        cal_masks: Dict[str, np.ndarray],
        train_masks: Dict[str, np.ndarray],
        edge_index: Dict[Tuple[str, str, str], np.ndarray],
        num_nodes: Dict[str, int],
    ) -> Dict[str, float]:
        """Train meta-calibrator and compute normalized quantiles.

        Steps:
            1. Compute neighbor stats from training residuals
            2. Train MLP on training nodes (heteroscedastic NLL)
            3. Apply to all nodes → σ_i
            4. Calibrate on cal set with normalized scores
        """
        neighbor_stats = self._compute_neighbor_stats(
            predictions, labels, train_masks, edge_index, num_nodes,
        )

        for ntype in cal_masks:
            meta_feat = self._build_meta_features(
                node_features, predictions, neighbor_stats, ntype,
            )
            input_dim = meta_feat.shape[1]
            net = MetaCalibratorNet(input_dim, self.hidden_dim)
            optimizer = torch.optim.Adam(net.parameters(), lr=self.lr)

            # Train on TRAINING nodes only
            train_mask = train_masks[ntype]
            train_feat = torch.tensor(meta_feat[train_mask], dtype=torch.float32)
            train_resid = torch.tensor(
                np.abs(labels[ntype][train_mask] - predictions[ntype][train_mask]),
                dtype=torch.float32,
            )

            net.train()
            for _ in range(self.meta_epochs):
                sigma = net(train_feat)
                # Heteroscedastic Gaussian NLL: (r²)/(2σ²) + log(σ)
                loss = (train_resid ** 2) / (2 * sigma ** 2) + torch.log(sigma + 1e-8)
                loss = loss.mean()
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

            # Apply trained net to ALL nodes → σ_i (frozen constants)
            net.eval()
            self.nets[ntype] = net
            with torch.no_grad():
                all_feat = torch.tensor(meta_feat, dtype=torch.float32)
                self._sigma[ntype] = net(all_feat).numpy()

            # Calibrate: normalized scores on cal set
            cal_mask = cal_masks[ntype]
            cal_resid = np.abs(labels[ntype][cal_mask] - predictions[ntype][cal_mask])
            sigma_cal = self._sigma[ntype][cal_mask]
            normalized = cal_resid / sigma_cal

            n_cal = len(normalized)
            if n_cal == 0:
                self.quantiles[ntype] = float("inf")
                continue
            level = np.ceil((n_cal + 1) * (1 - self.alpha)) / n_cal
            level = min(level, 1.0)
            self.quantiles[ntype] = float(np.quantile(normalized, level))

        self._calibrated = True
        return dict(self.quantiles)

    def predict(
        self,
        predictions: Dict[str, np.ndarray],
        test_masks: Optional[Dict[str, np.ndarray]] = None,
    ) -> ConformalResult:
        """Produce adaptive prediction intervals using learned σ_i."""
        if not self._calibrated:
            raise RuntimeError("Must call calibrate() before predict()")

        lower, upper, point = {}, {}, {}
        for ntype in predictions:
            pred = predictions[ntype]
            q = self.quantiles[ntype]
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
            lower=lower, upper=upper, point_pred=point,
            alpha=self.alpha, quantiles=dict(self.quantiles),
        )
