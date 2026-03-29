"""Hierarchical uncertainty estimation heads (Eq 7).

Three-level uncertainty:
- Pixel-level:  σ²_pixel = Conv1x1(z)
- Patch-level:  σ²_patch = AvgPool(Conv3x3(z))
- Region-level: σ²_region = GlobalAvgPool(z) → Linear
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class PixelUncertaintyHead(nn.Module):
    """1×1 conv → Softplus for per-pixel uncertainty."""

    def __init__(self, embed_dim: int, out_channels: int = 1):
        super().__init__()
        self.conv = nn.Conv2d(embed_dim, out_channels, kernel_size=1)
        self.activation = nn.Softplus()

    def forward(self, z: torch.Tensor) -> torch.Tensor:
        """
        Parameters
        ----------
        z : Tensor (B*T, D, H', W')

        Returns
        -------
        sigma_pixel : Tensor (B*T, out_channels, H', W')
        """
        return self.activation(self.conv(z))


class PatchUncertaintyHead(nn.Module):
    """3×3 conv → AvgPool → Softplus for patch-level uncertainty."""

    def __init__(self, embed_dim: int, kernel_size: int = 3, pool_size: int = 4):
        super().__init__()
        self.conv = nn.Conv2d(embed_dim, 1, kernel_size=kernel_size, padding=kernel_size // 2)
        self.pool_size = pool_size
        self.pool = None
        self.activation = nn.Softplus()

    def forward(self, z: torch.Tensor) -> torch.Tensor:
        """
        Parameters
        ----------
        z : Tensor (B*T, D, H', W')

        Returns
        -------
        sigma_patch : Tensor (B*T, 1, H'//pool, W'//pool)
        """
        conv_out = self.conv(z)
        H, W = conv_out.shape[-2:]
        k = min(self.pool_size, H, W)
        if k <= 1:
            pooled = F.adaptive_avg_pool2d(conv_out, 1)
        else:
            pooled = F.avg_pool2d(conv_out, kernel_size=k)
        return self.activation(pooled)


class RegionUncertaintyHead(nn.Module):
    """Global average pool → Linear → Softplus for region-level uncertainty."""

    def __init__(self, embed_dim: int):
        super().__init__()
        self.fc = nn.Linear(embed_dim, 1)
        self.activation = nn.Softplus()

    def forward(self, z: torch.Tensor) -> torch.Tensor:
        """
        Parameters
        ----------
        z : Tensor (B*T, D, H', W')

        Returns
        -------
        sigma_region : Tensor (B*T, 1)
        """
        pooled = F.adaptive_avg_pool2d(z, 1).squeeze(-1).squeeze(-1)
        return self.activation(self.fc(pooled))


class HierarchicalUncertainty(nn.Module):
    """Combine pixel, patch, and region uncertainty heads."""

    def __init__(self, embed_dim: int, patch_kernel: int = 3):
        super().__init__()
        self.pixel_head = PixelUncertaintyHead(embed_dim)
        self.patch_head = PatchUncertaintyHead(embed_dim, kernel_size=patch_kernel)
        self.region_head = RegionUncertaintyHead(embed_dim)

    def forward(
        self, z: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Compute hierarchical uncertainty estimates.

        Parameters
        ----------
        z : Tensor (B, T, D, H', W')

        Returns
        -------
        sigma_pixel : Tensor (B, T, 1, H', W')
        sigma_patch : Tensor (B, T, 1, H'//pool, W'//pool)
        sigma_region : Tensor (B, T, 1)
        """
        B, T, D, Hp, Wp = z.shape
        z_flat = z.reshape(B * T, D, Hp, Wp)

        sigma_pixel = self.pixel_head(z_flat).reshape(B, T, 1, Hp, Wp)
        sigma_patch = self.patch_head(z_flat)
        _, _, Ph, Pw = sigma_patch.shape
        sigma_patch = sigma_patch.reshape(B, T, 1, Ph, Pw)
        sigma_region = self.region_head(z_flat).reshape(B, T, 1)

        return sigma_pixel, sigma_patch, sigma_region
