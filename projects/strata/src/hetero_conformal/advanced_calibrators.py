"""Advanced conformal calibrators for heterogeneous graphs.

Provides three novel calibration strategies beyond the base PropagationAwareCalibrator:

1. LearnableLambdaCalibrator — per-type λ optimized on calibration set
2. AttentionCalibrator — attention-weighted neighbor difficulty aggregation
3. CQRCalibrator — Conformalized Quantile Regression with propagation

All preserve conformal validity: σ_i depends only on features (fixed inputs)
or frozen training-set residuals, not calibration/test labels.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from .conformal import ConformalResult, PropagationAwareCalibrator, HeteroConformalCalibrator


# ─────────────────────────────────────────────────────────────────────────────
# 1. Learnable Lambda Calibrator
# ─────────────────────────────────────────────────────────────────────────────

class LearnableLambdaCalibrator:
    """Per-type λ optimized on a calibration-tune split.

    Instead of a single hand-tuned λ, this calibrator:
        1. Splits calibration set into tune (50%) and eval (50%)
        2. Grid-searches λ per node type on tune split
        3. Picks λ that achieves valid coverage with smallest width
        4. Recalibrates on the full cal set using optimal per-type λ

    This is a principled alternative to sweeping λ post-hoc.
    """

    def __init__(
        self,
        alpha: float = 0.1,
        lambda_grid: Optional[list[float]] = None,
        neighbor_agg: str = "mean",
    ):
        self.alpha = alpha
        self.lambda_grid = lambda_grid or [0.0, 0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0]
        self.neighbor_agg = neighbor_agg
        self.optimal_lambdas: Dict[str, float] = {}
        self.quantiles: Dict[str, float] = {}
        self._sigma: Dict[str, np.ndarray] = {}
        self._calibrated = False

    def _compute_frozen_neighbor_avg(
        self,
        predictions: Dict[str, np.ndarray],
        labels: Dict[str, np.ndarray],
        train_masks: Dict[str, np.ndarray],
        edge_index: Dict[Tuple[str, str, str], np.ndarray],
        num_nodes: Dict[str, int],
    ) -> Dict[str, np.ndarray]:
        """Compute frozen neighbor difficulty (same as PropagationAwareCalibrator)."""
        train_resid: Dict[str, np.ndarray] = {}
        for ntype in predictions:
            r = np.abs(predictions[ntype] - labels[ntype])
            frozen = np.zeros_like(r)
            frozen[train_masks[ntype]] = r[train_masks[ntype]]
            train_resid[ntype] = frozen

        frozen_avg: Dict[str, np.ndarray] = {}
        for ntype in predictions:
            n = num_nodes[ntype]
            neighbor_sum = np.zeros(n, dtype=np.float64)
            neighbor_count = np.zeros(n, dtype=np.float64)
            for (src_type, rel, dst_type), ei in edge_index.items():
                if dst_type != ntype or ei.shape[1] == 0:
                    continue
                src_idx, dst_idx = ei[0], ei[1]
                train_mask_src = train_masks[src_type][src_idx]
                valid_src = src_idx[train_mask_src]
                valid_dst = dst_idx[train_mask_src]
                np.add.at(neighbor_sum, valid_dst, train_resid[src_type][valid_src])
                np.add.at(neighbor_count, valid_dst, 1.0)
            safe_count = np.maximum(neighbor_count, 1.0)
            frozen_avg[ntype] = (neighbor_sum / safe_count).astype(np.float32)
        return frozen_avg

    def calibrate(
        self,
        predictions: Dict[str, np.ndarray],
        labels: Dict[str, np.ndarray],
        cal_masks: Dict[str, np.ndarray],
        train_masks: Dict[str, np.ndarray],
        edge_index: Dict[Tuple[str, str, str], np.ndarray],
        num_nodes: Dict[str, int],
    ) -> Dict[str, float]:
        """Find optimal per-type λ and calibrate."""
        frozen_avg = self._compute_frozen_neighbor_avg(
            predictions, labels, train_masks, edge_index, num_nodes,
        )

        for ntype in cal_masks:
            cal_mask = cal_masks[ntype]
            cal_indices = np.where(cal_mask)[0]
            n_cal = len(cal_indices)
            if n_cal == 0:
                self.optimal_lambdas[ntype] = 0.0
                self.quantiles[ntype] = float("inf")
                continue

            # Split cal into tune/eval (50/50)
            # Skip lambda search if calibration set too small for reliable tuning
            rng = np.random.default_rng(42)
            perm = rng.permutation(n_cal)
            n_tune = n_cal // 2
            cal_resid = np.abs(labels[ntype] - predictions[ntype])

            if n_tune < 10:
                # Too few samples for reliable lambda tuning; default to λ=0
                best_lam = 0.0
                self.optimal_lambdas[ntype] = best_lam
                sigma = 1.0 + best_lam * frozen_avg[ntype]
                self._sigma[ntype] = sigma
                normalized = cal_resid[cal_mask] / sigma[cal_mask]
                level = min(np.ceil((n_cal + 1) * (1 - self.alpha)) / n_cal, 1.0)
                self.quantiles[ntype] = float(np.quantile(normalized, level))
                continue

            tune_idx = cal_indices[perm[:n_tune]]
            eval_idx = cal_indices[perm[n_tune:]]

            best_lam = 0.0
            best_width = float("inf")

            for lam in self.lambda_grid:
                sigma = 1.0 + lam * frozen_avg[ntype]

                # Calibrate on tune split
                tune_scores = cal_resid[tune_idx] / sigma[tune_idx]
                n_t = len(tune_scores)
                level = min(np.ceil((n_t + 1) * (1 - self.alpha)) / n_t, 1.0)
                q = float(np.quantile(tune_scores, level))

                # Evaluate on eval split
                eval_width = q * sigma[eval_idx]
                eval_lo = predictions[ntype][eval_idx] - eval_width
                eval_hi = predictions[ntype][eval_idx] + eval_width
                eval_true = labels[ntype][eval_idx]
                eval_cov = np.mean((eval_true >= eval_lo) & (eval_true <= eval_hi))

                # Accept if coverage valid, prefer smallest width
                if eval_cov >= (1 - self.alpha) - 0.02:
                    mean_w = float(np.mean(eval_width))
                    if mean_w < best_width:
                        best_width = mean_w
                        best_lam = lam

            self.optimal_lambdas[ntype] = best_lam

            # Recalibrate on FULL cal set with optimal λ
            sigma = 1.0 + best_lam * frozen_avg[ntype]
            self._sigma[ntype] = sigma
            normalized = cal_resid[cal_mask] / sigma[cal_mask]
            level = min(np.ceil((n_cal + 1) * (1 - self.alpha)) / n_cal, 1.0)
            self.quantiles[ntype] = float(np.quantile(normalized, level))

        self._calibrated = True
        return dict(self.quantiles)

    def predict(
        self,
        predictions: Dict[str, np.ndarray],
        test_masks: Optional[Dict[str, np.ndarray]] = None,
    ) -> ConformalResult:
        if not self._calibrated:
            raise RuntimeError("Must call calibrate() first")
        lower, upper, point = {}, {}, {}
        for ntype in predictions:
            pred = predictions[ntype]
            q = self.quantiles[ntype]
            sigma = self._sigma[ntype]
            width = q * sigma
            lo, hi = pred - width, pred + width
            if test_masks is not None and ntype in test_masks:
                mask = test_masks[ntype]
                lower[ntype], upper[ntype], point[ntype] = lo[mask], hi[mask], pred[mask]
            else:
                lower[ntype], upper[ntype], point[ntype] = lo, hi, pred
        return ConformalResult(lower, upper, point, self.alpha, dict(self.quantiles))


# ─────────────────────────────────────────────────────────────────────────────
# 2. Attention-based Neighbor Difficulty Calibrator
# ─────────────────────────────────────────────────────────────────────────────

class AttentionDifficultyNet(nn.Module):
    """Computes attention weights over neighbors for difficulty aggregation.

    For each edge (u → v), computes:
        a_{uv} = softmax( MLP([f_v, f_u, |r_u|]) )
    where r_u is the frozen training residual of source node u.
    """

    def __init__(self, feature_dim: int, hidden_dim: int = 16):
        super().__init__()
        # Input: [dst_feat, src_feat, src_residual] → 2*feature_dim + 1
        self.attn = nn.Sequential(
            nn.Linear(2 * feature_dim + 1, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
        )

    def forward(
        self,
        dst_feat: torch.Tensor,
        src_feat: torch.Tensor,
        src_resid: torch.Tensor,
    ) -> torch.Tensor:
        """Compute raw attention scores (pre-softmax)."""
        combined = torch.cat([dst_feat, src_feat, src_resid.unsqueeze(-1)], dim=-1)
        return self.attn(combined).squeeze(-1)


class AttentionCalibrator:
    """Attention-weighted neighbor difficulty for conformal calibration.

    Instead of mean/median aggregation of neighbor residuals, learns
    attention weights that determine which neighbors are most informative
    for calibration difficulty estimation.

    Training: on training-set nodes, minimize heteroscedastic NLL
    using attention-aggregated σ_i.
    """

    def __init__(
        self,
        alpha: float = 0.1,
        neighborhood_weight: float = 0.3,
        hidden_dim: int = 16,
        lr: float = 1e-3,
        attn_epochs: int = 100,
    ):
        self.alpha = alpha
        self.neighborhood_weight = neighborhood_weight
        self.hidden_dim = hidden_dim
        self.lr = lr
        self.attn_epochs = attn_epochs
        self.quantiles: Dict[str, float] = {}
        self._sigma: Dict[str, np.ndarray] = {}
        self._calibrated = False

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
        """Train attention weights and calibrate."""
        # Frozen training residuals
        train_resid: Dict[str, np.ndarray] = {}
        for ntype in predictions:
            r = np.abs(predictions[ntype] - labels[ntype])
            frozen = np.zeros_like(r)
            frozen[train_masks[ntype]] = r[train_masks[ntype]]
            train_resid[ntype] = frozen

        for ntype in cal_masks:
            n = num_nodes[ntype]
            feat_dim = node_features[ntype].shape[1]

            # Collect edges targeting this ntype
            edges: list[tuple[str, int, int]] = []
            for (src_type, rel, dst_type), ei in edge_index.items():
                if dst_type != ntype or ei.shape[1] == 0:
                    continue
                for e in range(ei.shape[1]):
                    s, d = int(ei[0, e]), int(ei[1, e])
                    if train_masks[src_type][s]:
                        edges.append((src_type, s, d))

            if not edges:
                # Fallback: uniform σ = 1
                self._sigma[ntype] = np.ones(n, dtype=np.float32)
                cal_mask = cal_masks[ntype]
                cal_resid = np.abs(labels[ntype][cal_mask] - predictions[ntype][cal_mask])
                n_cal = len(cal_resid)
                level = min(np.ceil((n_cal + 1) * (1 - self.alpha)) / n_cal, 1.0)
                self.quantiles[ntype] = float(np.quantile(cal_resid, level))
                continue

            # Build edge tensors
            # For simplicity, project all source features to same dim
            src_feats_list = []
            dst_feats_list = []
            src_resid_list = []
            dst_indices = []
            for src_type, s, d in edges:
                src_f = node_features[src_type][s]
                dst_f = node_features[ntype][d]
                # Pad/truncate to match feature_dim
                if len(src_f) < feat_dim:
                    src_f = np.pad(src_f, (0, feat_dim - len(src_f)))
                elif len(src_f) > feat_dim:
                    src_f = src_f[:feat_dim]
                src_feats_list.append(src_f)
                dst_feats_list.append(dst_f)
                src_resid_list.append(train_resid[src_type][s])
                dst_indices.append(d)

            src_feats_t = torch.tensor(np.array(src_feats_list), dtype=torch.float32)
            dst_feats_t = torch.tensor(np.array(dst_feats_list), dtype=torch.float32)
            src_resid_t = torch.tensor(np.array(src_resid_list), dtype=torch.float32)
            dst_idx_t = torch.tensor(dst_indices, dtype=torch.long)

            # Train attention network
            attn_net = AttentionDifficultyNet(feat_dim, self.hidden_dim)
            optimizer = torch.optim.Adam(attn_net.parameters(), lr=self.lr)

            # Training target: σ should predict |residual| on training nodes
            train_mask = train_masks[ntype]
            train_idx = np.where(train_mask)[0]
            train_true_resid = torch.tensor(
                np.abs(labels[ntype][train_idx] - predictions[ntype][train_idx]),
                dtype=torch.float32,
            )

            attn_net.train()
            for _ in range(self.attn_epochs):
                # Compute attention scores
                raw_scores = attn_net(dst_feats_t, src_feats_t, src_resid_t)

                # Softmax per destination node
                # Compute weighted neighbor residual per node
                weighted_resid = torch.zeros(n, dtype=torch.float32)
                weight_sum = torch.zeros(n, dtype=torch.float32)
                exp_scores = torch.exp(raw_scores - raw_scores.max())
                for e_idx in range(len(edges)):
                    d = dst_indices[e_idx]
                    weighted_resid[d] += exp_scores[e_idx] * src_resid_t[e_idx]
                    weight_sum[d] += exp_scores[e_idx]

                safe_sum = torch.clamp(weight_sum, min=1e-8)
                neighbor_diff = weighted_resid / safe_sum
                sigma = 1.0 + self.neighborhood_weight * neighbor_diff

                # Heteroscedastic NLL on training nodes
                sigma_train = sigma[train_idx]
                loss = (train_true_resid ** 2) / (2 * sigma_train ** 2) + torch.log(sigma_train)
                loss = loss.mean()

                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

            # Apply to get σ for all nodes
            attn_net.eval()
            with torch.no_grad():
                raw_scores = attn_net(dst_feats_t, src_feats_t, src_resid_t)
                exp_scores = torch.exp(raw_scores - raw_scores.max())
                weighted_resid = torch.zeros(n, dtype=torch.float32)
                weight_sum = torch.zeros(n, dtype=torch.float32)
                for e_idx in range(len(edges)):
                    d = dst_indices[e_idx]
                    weighted_resid[d] += exp_scores[e_idx] * src_resid_t[e_idx]
                    weight_sum[d] += exp_scores[e_idx]
                safe_sum = torch.clamp(weight_sum, min=1e-8)
                neighbor_diff = weighted_resid / safe_sum
                sigma = (1.0 + self.neighborhood_weight * neighbor_diff).numpy()

            self._sigma[ntype] = sigma

            # Calibrate on cal set
            cal_mask = cal_masks[ntype]
            cal_resid = np.abs(labels[ntype][cal_mask] - predictions[ntype][cal_mask])
            normalized = cal_resid / sigma[cal_mask]
            n_cal = len(normalized)
            level = min(np.ceil((n_cal + 1) * (1 - self.alpha)) / n_cal, 1.0)
            self.quantiles[ntype] = float(np.quantile(normalized, level))

        self._calibrated = True
        return dict(self.quantiles)

    def predict(
        self,
        predictions: Dict[str, np.ndarray],
        test_masks: Optional[Dict[str, np.ndarray]] = None,
    ) -> ConformalResult:
        if not self._calibrated:
            raise RuntimeError("Must call calibrate() first")
        lower, upper, point = {}, {}, {}
        for ntype in predictions:
            pred = predictions[ntype]
            q = self.quantiles[ntype]
            sigma = self._sigma[ntype]
            width = q * sigma
            lo, hi = pred - width, pred + width
            if test_masks is not None and ntype in test_masks:
                mask = test_masks[ntype]
                lower[ntype], upper[ntype], point[ntype] = lo[mask], hi[mask], pred[mask]
            else:
                lower[ntype], upper[ntype], point[ntype] = lo, hi, pred
        return ConformalResult(lower, upper, point, self.alpha, dict(self.quantiles))


# ─────────────────────────────────────────────────────────────────────────────
# 3. Conformalized Quantile Regression (CQR) + Propagation
# ─────────────────────────────────────────────────────────────────────────────

class QuantileHead(nn.Module):
    """Output head that predicts lower and upper quantiles."""

    def __init__(self, hidden_dim: int):
        super().__init__()
        self.lower_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 1),
        )
        # Parameterize upper quantile as lo + softplus(delta) to ensure hi >= lo
        self.delta_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 1),
        )

    def forward(self, h: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        lo = self.lower_head(h).squeeze(-1)
        delta = self.delta_head(h).squeeze(-1)
        hi = lo + F.softplus(delta)
        return lo, hi


def pinball_loss(pred: torch.Tensor, target: torch.Tensor, tau: float) -> torch.Tensor:
    """Pinball (quantile) loss for quantile regression."""
    diff = target - pred
    return torch.mean(torch.max(tau * diff, (tau - 1) * diff))


class CQRCalibrator:
    """Conformalized Quantile Regression with optional propagation scaling.

    Steps:
        1. Train quantile output heads on the existing GNN backbone
           (predict lower α/2 and upper 1-α/2 quantiles)
        2. CQR calibration: compute nonconformity scores
           s_i = max(q_lo_i - y_i, y_i - q_hi_i)
        3. With propagation: normalize by σ_i from neighbor difficulty
        4. Produce asymmetric intervals: [q_lo - q̂·σ, q_hi + q̂·σ]

    Reference: Romano et al. (2019), "Conformalized Quantile Regression"
    """

    def __init__(
        self,
        alpha: float = 0.1,
        use_propagation: bool = True,
        neighborhood_weight: float = 0.3,
        quantile_epochs: int = 100,
        lr: float = 1e-3,
        verbose: bool = False,
    ):
        self.alpha = alpha
        self.use_propagation = use_propagation
        self.neighborhood_weight = neighborhood_weight
        self.quantile_epochs = quantile_epochs
        self.lr = lr
        self.quantile_heads: Dict[str, QuantileHead] = {}
        self.quantiles: Dict[str, float] = {}
        self._sigma: Dict[str, np.ndarray] = {}
        self._q_lo: Dict[str, np.ndarray] = {}
        self._q_hi: Dict[str, np.ndarray] = {}
        self._quantile_losses: Dict[str, list] = {}
        self.verbose = verbose
        self._calibrated = False

    def train_quantile_heads(
        self,
        model_hidden: Dict[str, torch.Tensor],
        labels: Dict[str, np.ndarray],
        train_masks: Dict[str, np.ndarray],
        hidden_dim: int,
    ) -> None:
        """Train quantile output heads on GNN hidden representations.

        Parameters
        ----------
        model_hidden : dict
            Hidden representations from the GNN (before output head).
        labels : dict
            Ground truth labels.
        train_masks : dict
            Training masks.
        hidden_dim : int
            Dimension of hidden representations.
        """
        tau_lo = self.alpha / 2
        tau_hi = 1 - self.alpha / 2

        for ntype in model_hidden:
            head = QuantileHead(hidden_dim)
            optimizer = torch.optim.Adam(head.parameters(), lr=self.lr)

            train_mask = train_masks[ntype]
            h_train = model_hidden[ntype][train_mask]
            y_train = torch.tensor(labels[ntype][train_mask], dtype=torch.float32)

            head.train()
            losses = []
            n_train = int(train_mask.sum())
            if self.verbose:
                print(f"CQR: training quantile head for ntype={ntype}, n_train={n_train}")
            for ep in range(self.quantile_epochs):
                lo, hi = head(h_train)
                loss = pinball_loss(lo, y_train, tau_lo) + pinball_loss(hi, y_train, tau_hi)
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                losses.append(float(loss.detach().cpu().numpy()))
                if self.verbose and (ep == 0 or (ep + 1) % max(1, self.quantile_epochs // 5) == 0):
                    print(f"  ntype={ntype} epoch={ep+1}/{self.quantile_epochs} loss={losses[-1]:.4f}")

            head.eval()
            self.quantile_heads[ntype] = head

            # store per-epoch loss trace
            self._quantile_losses[ntype] = losses

            # Get quantile predictions for ALL nodes
            with torch.no_grad():
                lo_all, hi_all = head(model_hidden[ntype])
                lo_np = lo_all.numpy()
                hi_np = hi_all.numpy()
                # Enforce ordering: lower quantile should not exceed upper quantile.
                # If inversions exist, fix them by swapping; log a small warning.
                inversions = (hi_np < lo_np)
                n_inv = int(inversions.sum())
                if n_inv > 0:
                    print(f"WARN: QuantileHead inversions for ntype={ntype}: {n_inv} values; fixing by ordering.")
                lo_fixed = np.minimum(lo_np, hi_np)
                hi_fixed = np.maximum(lo_np, hi_np)
                self._q_lo[ntype] = lo_fixed
                self._q_hi[ntype] = hi_fixed

    def calibrate(
        self,
        predictions: Dict[str, np.ndarray],
        labels: Dict[str, np.ndarray],
        cal_masks: Dict[str, np.ndarray],
        train_masks: Dict[str, np.ndarray],
        edge_index: Dict[Tuple[str, str, str], np.ndarray],
        num_nodes: Dict[str, int],
    ) -> Dict[str, float]:
        """CQR calibration with optional propagation normalization."""
        # Compute propagation sigma if enabled
        if self.use_propagation:
            train_resid: Dict[str, np.ndarray] = {}
            for ntype in predictions:
                r = np.abs(predictions[ntype] - labels[ntype])
                frozen = np.zeros_like(r)
                frozen[train_masks[ntype]] = r[train_masks[ntype]]
                train_resid[ntype] = frozen

            for ntype in predictions:
                n = num_nodes[ntype]
                ns, nc = np.zeros(n), np.zeros(n)
                for (st, rel, dt), ei in edge_index.items():
                    if dt != ntype or ei.shape[1] == 0:
                        continue
                    src_idx, dst_idx = ei[0], ei[1]
                    train_mask_src = train_masks[st][src_idx]
                    valid_src = src_idx[train_mask_src]
                    valid_dst = dst_idx[train_mask_src]
                    np.add.at(ns, valid_dst, train_resid[st][valid_src])
                    np.add.at(nc, valid_dst, 1.0)
                avg = ns / np.maximum(nc, 1)
                self._sigma[ntype] = (1.0 + self.neighborhood_weight * avg).astype(np.float32)
        else:
            for ntype in predictions:
                self._sigma[ntype] = np.ones(num_nodes[ntype], dtype=np.float32)

        # CQR scores: s_i = max(q_lo - y, y - q_hi) / σ_i
        for ntype in cal_masks:
            cal_mask = cal_masks[ntype]
            y_cal = labels[ntype][cal_mask]
            lo_cal = self._q_lo[ntype][cal_mask]
            hi_cal = self._q_hi[ntype][cal_mask]
            sigma_cal = self._sigma[ntype][cal_mask]

            scores = np.maximum(lo_cal - y_cal, y_cal - hi_cal) / sigma_cal
            n_cal = len(scores)
            if n_cal == 0:
                self.quantiles[ntype] = float("inf")
                continue
            level = min(np.ceil((n_cal + 1) * (1 - self.alpha)) / n_cal, 1.0)
            self.quantiles[ntype] = float(np.quantile(scores, level))

        self._calibrated = True
        return dict(self.quantiles)

    def predict(
        self,
        predictions: Dict[str, np.ndarray],
        test_masks: Optional[Dict[str, np.ndarray]] = None,
    ) -> ConformalResult:
        """Produce asymmetric CQR prediction intervals."""
        if not self._calibrated:
            raise RuntimeError("Must call calibrate() first")
        lower, upper, point = {}, {}, {}
        for ntype in predictions:
            q = self.quantiles[ntype]
            sigma = self._sigma[ntype]
            correction = q * sigma
            lo = self._q_lo[ntype] - correction
            hi = self._q_hi[ntype] + correction
            pred = predictions[ntype]
            if test_masks is not None and ntype in test_masks:
                mask = test_masks[ntype]
                lower[ntype] = lo[mask]
                upper[ntype] = hi[mask]
                point[ntype] = pred[mask]
            else:
                lower[ntype], upper[ntype], point[ntype] = lo, hi, pred
        return ConformalResult(lower, upper, point, self.alpha, dict(self.quantiles))
