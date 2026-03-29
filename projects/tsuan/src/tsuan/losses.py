"""Loss functions for TSUAN training.

Total loss (Section II):
    L = L_recon + α₁·L_unc + α₂·L_phys + α₃·L_smooth + α₄·L_aux

Components:
- L_recon: L1 reconstruction loss on clear pixels
- L_unc: Negative log-likelihood uncertainty calibration
- L_phys: Physical consistency (NDVI/EVI range constraints)
- L_smooth: Temporal smoothness regularization
- L_aux: Auxiliary multi-task loss (cloud segmentation)
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class ReconstructionLoss(nn.Module):
    """L1 reconstruction loss on clear (non-cloudy) pixels."""

    def forward(
        self,
        x_hat: torch.Tensor,
        x_target: torch.Tensor,
        clear_mask: torch.Tensor,
    ) -> torch.Tensor:
        """
        Parameters
        ----------
        x_hat : Tensor (B, T, C, H, W) — predicted
        x_target : Tensor (B, T, C, H, W) — ground truth
        clear_mask : Tensor (B, T, 1, H, W) — 1 where clear, 0 where cloudy

        Returns
        -------
        Scalar loss.
        """
        diff = torch.abs(x_hat - x_target) * clear_mask
        n_clear = clear_mask.sum().clamp(min=1.0)
        return diff.sum() / n_clear


class UncertaintyCalibrationLoss(nn.Module):
    """NLL-based uncertainty calibration loss.

    L_unc = 0.5 * (log(σ²) + (x - x̂)² / σ²)
    Encourages the model to output calibrated uncertainty.
    """

    def forward(
        self,
        x_hat: torch.Tensor,
        x_target: torch.Tensor,
        sigma_sq: torch.Tensor,
        clear_mask: torch.Tensor,
    ) -> torch.Tensor:
        """
        Parameters
        ----------
        x_hat : Tensor (B, T, C, H, W)
        x_target : Tensor (B, T, C, H, W)
        sigma_sq : Tensor (B, T, 1, H, W) — pixel-level variance
        clear_mask : Tensor (B, T, 1, H, W)
        """
        sigma_sq = sigma_sq.clamp(min=1e-6)
        residual_sq = (x_hat - x_target) ** 2
        # Average over channels for comparison with single-channel sigma
        residual_sq = residual_sq.mean(dim=2, keepdim=True)
        nll = 0.5 * (torch.log(sigma_sq) + residual_sq / sigma_sq)
        nll = nll * clear_mask
        n_clear = clear_mask.sum().clamp(min=1.0)
        return nll.sum() / n_clear


class PhysicalConsistencyLoss(nn.Module):
    """Physical plausibility constraint via NDVI/EVI bounds.

    Penalizes predictions where derived vegetation indices fall outside
    physically valid ranges: NDVI ∈ [-1, 1], EVI ∈ [-0.2, 1.0].

    Assumes Sentinel-2 band ordering with:
    - Band 3 (index 2): Red (B4)
    - Band 7 (index 6): NIR (B8)
    - Band 1 (index 0): Blue (B2)
    """

    def __init__(
        self,
        red_idx: int = 3,
        nir_idx: int = 7,
        blue_idx: int = 1,
    ):
        super().__init__()
        self.red_idx = red_idx
        self.nir_idx = nir_idx
        self.blue_idx = blue_idx

    def _compute_ndvi(self, x: torch.Tensor) -> torch.Tensor:
        red = x[:, :, self.red_idx : self.red_idx + 1]
        nir = x[:, :, self.nir_idx : self.nir_idx + 1]
        denom = (nir + red).clamp(min=1e-6)
        return (nir - red) / denom

    def _compute_evi(self, x: torch.Tensor) -> torch.Tensor:
        red = x[:, :, self.red_idx : self.red_idx + 1]
        nir = x[:, :, self.nir_idx : self.nir_idx + 1]
        blue = x[:, :, self.blue_idx : self.blue_idx + 1]
        denom = (nir + 6.0 * red - 7.5 * blue + 1.0).clamp(min=1e-6)
        return 2.5 * (nir - red) / denom

    def forward(self, x_hat: torch.Tensor) -> torch.Tensor:
        """Penalize physically implausible predictions.

        Parameters
        ----------
        x_hat : Tensor (B, T, C, H, W)
        """
        ndvi = self._compute_ndvi(x_hat)
        evi = self._compute_evi(x_hat)

        # Penalty for NDVI outside [-1, 1]
        ndvi_penalty = F.relu(-ndvi - 1) + F.relu(ndvi - 1)
        # Penalty for EVI outside [-0.2, 1.0]
        evi_penalty = F.relu(-evi - 0.2) + F.relu(evi - 1.0)

        return (ndvi_penalty.mean() + evi_penalty.mean()) / 2.0


class TemporalSmoothnessLoss(nn.Module):
    """Penalize large temporal jumps in reconstructed time series."""

    def forward(self, x_hat: torch.Tensor) -> torch.Tensor:
        """
        Parameters
        ----------
        x_hat : Tensor (B, T, C, H, W)
        """
        if x_hat.shape[1] < 2:
            return torch.tensor(0.0, device=x_hat.device)
        diff = x_hat[:, 1:] - x_hat[:, :-1]
        return diff.pow(2).mean()


class AuxiliaryCloudLoss(nn.Module):
    """Auxiliary binary cross-entropy loss for cloud segmentation head."""

    def forward(
        self,
        cloud_logits: torch.Tensor,
        cloud_target: torch.Tensor,
    ) -> torch.Tensor:
        """
        Parameters
        ----------
        cloud_logits : Tensor (B, T, 1, H', W') — raw logits
        cloud_target : Tensor (B, T, 1, H', W') — binary cloud mask
        """
        return F.binary_cross_entropy_with_logits(cloud_logits, cloud_target)


class TSUANLoss(nn.Module):
    """Combined TSUAN loss with curriculum scheduling."""

    def __init__(
        self,
        alpha_unc: float = 0.1,
        alpha_phys: float = 0.05,
        alpha_smooth: float = 0.01,
        alpha_aux: float = 0.01,
        curriculum_start_epoch: int = 0,
        curriculum_ramp_epochs: int = 10,
    ):
        super().__init__()
        self.recon_loss = ReconstructionLoss()
        self.unc_loss = UncertaintyCalibrationLoss()
        self.phys_loss = PhysicalConsistencyLoss()
        self.smooth_loss = TemporalSmoothnessLoss()
        self.aux_loss = AuxiliaryCloudLoss()

        self.alpha_unc = alpha_unc
        self.alpha_phys = alpha_phys
        self.alpha_smooth = alpha_smooth
        self.alpha_aux = alpha_aux
        self.curriculum_start = curriculum_start_epoch
        self.curriculum_ramp = curriculum_ramp_epochs

    def _curriculum_weight(self, epoch: int) -> float:
        """Linear ramp from 0 to 1 over curriculum period."""
        if epoch < self.curriculum_start:
            return 0.0
        progress = (epoch - self.curriculum_start) / max(self.curriculum_ramp, 1)
        return min(1.0, progress)

    def forward(
        self,
        x_hat: torch.Tensor,
        x_target: torch.Tensor,
        sigma_sq: torch.Tensor,
        clear_mask: torch.Tensor,
        cloud_logits: torch.Tensor | None = None,
        cloud_target: torch.Tensor | None = None,
        epoch: int = 0,
    ) -> dict[str, torch.Tensor]:
        """Compute total loss with all components.

        Returns dict with 'total' and individual component losses.
        """
        w = self._curriculum_weight(epoch)

        l_recon = self.recon_loss(x_hat, x_target, clear_mask)
        l_unc = self.unc_loss(x_hat, x_target, sigma_sq, clear_mask)
        l_phys = self.phys_loss(x_hat)
        l_smooth = self.smooth_loss(x_hat)

        total = (
            l_recon
            + w * self.alpha_unc * l_unc
            + w * self.alpha_phys * l_phys
            + w * self.alpha_smooth * l_smooth
        )

        losses = {
            "total": total,
            "recon": l_recon,
            "unc": l_unc,
            "phys": l_phys,
            "smooth": l_smooth,
        }

        if cloud_logits is not None and cloud_target is not None:
            l_aux = self.aux_loss(cloud_logits, cloud_target)
            total = total + w * self.alpha_aux * l_aux
            losses["aux"] = l_aux
            losses["total"] = total

        return losses
