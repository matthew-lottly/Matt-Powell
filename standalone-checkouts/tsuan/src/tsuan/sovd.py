"""Structural Observational Void Detection (SOVD).

Detects per-pixel regions where cloud-free observations are structurally
insufficient for reliable reconstruction.  Outputs a *knowability map*
that gates the model's reconstruction confidence.

Key concepts
------------
- **Temporal cloud frequency** :math:`f(i,j) = \\frac{1}{T}\\sum_t u_{t,i,j}` — the
  fraction of time steps where pixel (i,j) is cloud-covered.
- **Persistent void mask** :math:`V_{hard}` — binary mask of pixels where
  :math:`f > \\tau_{void}` (e.g. 0.95).
- **Soft knowability** :math:`K(i,j) \\in [0,1]` — sigmoid-scaled inverse of f,
  optionally refined by a small CNN that also ingests SAR observation
  counts and spatial context.

The knowability map enters the loss as a per-pixel weighting mask and is
exposed as a first-class model output, letting downstream consumers
**suppress** reconstructions in structurally irrecoverable regions rather
than hallucinating.
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class SOVDAnalyzer(nn.Module):
    """Lightweight module that turns temporal cloud masks into knowability maps.

    Parameters
    ----------
    embed_dim : int
        Channel dimension of the encoder feature maps (used for the learned
        refinement head).
    void_threshold : float
        Cloud-frequency threshold above which a pixel is flagged as a
        persistent void (default 0.90).
    temperature : float
        Controls steepness of the soft knowability sigmoid (default 10.0).
    refine : bool
        If True, a small 3-layer CNN refines the analytic knowability
        estimate using spatial context from SAR availability.
    """

    def __init__(
        self,
        embed_dim: int = 128,
        void_threshold: float = 0.90,
        temperature: float = 10.0,
        refine: bool = True,
    ):
        super().__init__()
        self.void_threshold = void_threshold
        self.temperature = temperature
        self.refine = refine

        if refine:
            # Input: 3 channels — cloud_freq, clear_count_norm, sar_availability
            self.refine_net = nn.Sequential(
                nn.Conv2d(3, 16, 3, padding=1),
                nn.ReLU(inplace=True),
                nn.Conv2d(16, 16, 3, padding=1),
                nn.ReLU(inplace=True),
                nn.Conv2d(16, 1, 1),
            )

    def compute_cloud_frequency(self, u_mask: torch.Tensor) -> torch.Tensor:
        """Compute per-pixel temporal cloud frequency.

        Parameters
        ----------
        u_mask : Tensor (B, T, 1, H, W) — cloud probability mask ∈ [0, 1]

        Returns
        -------
        cloud_freq : Tensor (B, 1, H, W) — mean cloud probability across T
        """
        return u_mask.mean(dim=1)  # (B, 1, H, W)

    def compute_hard_void_mask(self, cloud_freq: torch.Tensor) -> torch.Tensor:
        """Binary mask of persistently clouded pixels.

        Parameters
        ----------
        cloud_freq : Tensor (B, 1, H, W)

        Returns
        -------
        void_mask : Tensor (B, 1, H, W) — 1 where void, 0 where observable
        """
        return (cloud_freq > self.void_threshold).float()

    def compute_soft_knowability(
        self,
        cloud_freq: torch.Tensor,
        sar_availability: torch.Tensor | None = None,
    ) -> torch.Tensor:
        """Smooth knowability score ∈ [0, 1].

        K(i,j) = σ( temperature * (τ - f(i,j)) )

        High when cloud frequency is low (pixel is well-observed),
        low when cloud frequency exceeds the void threshold.

        Parameters
        ----------
        cloud_freq : Tensor (B, 1, H, W)
        sar_availability : Tensor (B, 1, H, W) or None
            Fraction of time steps with valid SAR data (1.0 = always available).

        Returns
        -------
        knowability : Tensor (B, 1, H, W)
        """
        # Analytic sigmoid knowability
        k = torch.sigmoid(self.temperature * (self.void_threshold - cloud_freq))

        if self.refine and hasattr(self, "refine_net"):
            # Clear-observation count (normalized)
            clear_count = 1.0 - cloud_freq
            if sar_availability is None:
                sar_availability = torch.ones_like(cloud_freq)
            features = torch.cat([cloud_freq, clear_count, sar_availability], dim=1)
            k = k + self.refine_net(features)
            k = torch.clamp(k, 0.0, 1.0)

        return k

    def forward(
        self,
        u_mask: torch.Tensor,
        sar_availability: torch.Tensor | None = None,
    ) -> dict[str, torch.Tensor]:
        """Compute SOVD outputs.

        Parameters
        ----------
        u_mask : Tensor (B, T, 1, H, W) — cloud probability mask
        sar_availability : Tensor (B, 1, H, W) or None

        Returns
        -------
        Dict with:
            cloud_freq : Tensor (B, 1, H, W) — temporal cloud frequency
            void_mask : Tensor (B, 1, H, W) — binary persistent void mask
            knowability : Tensor (B, 1, H, W) — soft knowability map [0, 1]
        """
        cloud_freq = self.compute_cloud_frequency(u_mask)
        void_mask = self.compute_hard_void_mask(cloud_freq)
        knowability = self.compute_soft_knowability(cloud_freq, sar_availability)

        return {
            "cloud_freq": cloud_freq,
            "void_mask": void_mask,
            "knowability": knowability,
        }
