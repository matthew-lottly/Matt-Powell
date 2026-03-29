"""Dual-stream encoder for optical (Sentinel-2) and SAR (Sentinel-1) inputs.

Feature extraction (Eq 1):
    h_opt = E_opt(x_opt)  ∈ R^{T×D×H'×W'}
    h_sar = E_sar(x_sar)  ∈ R^{T×D×H'×W'}

Supports a lightweight CNN backbone or optional Prithvi GeoFM backbone.
"""

from __future__ import annotations

import torch
import torch.nn as nn


class ConvBlock(nn.Module):
    """Conv → BatchNorm → GELU, with optional stride for downsampling."""

    def __init__(self, in_ch: int, out_ch: int, stride: int = 2):
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, kernel_size=3, stride=stride, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.GELU(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.block(x)


class CNNEncoder(nn.Module):
    """Multi-scale CNN encoder that progressively downsamples spatial dims."""

    def __init__(self, in_channels: int, embed_dim: int, num_blocks: int = 4):
        super().__init__()
        channels = [in_channels] + [
            min(embed_dim, 2**i * max(32, in_channels)) for i in range(num_blocks)
        ]
        channels[-1] = embed_dim  # ensure final dim matches
        self.blocks = nn.ModuleList(
            [ConvBlock(channels[i], channels[i + 1]) for i in range(num_blocks)]
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        for block in self.blocks:
            x = block(x)
        return x


class DualStreamEncoder(nn.Module):
    """Parallel encoders for optical and SAR streams.

    Parameters
    ----------
    optical_in_channels : int
        Number of Sentinel-2 bands (default 13 for L2A).
    sar_in_channels : int
        Number of SAR channels (default 2: VV + VH).
    embed_dim : int
        Latent embedding dimension D.
    num_blocks : int
        Number of convolutional downsampling blocks.
    """

    def __init__(
        self,
        optical_in_channels: int = 13,
        sar_in_channels: int = 2,
        embed_dim: int = 128,
        num_blocks: int = 4,
    ):
        super().__init__()
        self.optical_encoder = CNNEncoder(optical_in_channels, embed_dim, num_blocks)
        self.sar_encoder = CNNEncoder(sar_in_channels, embed_dim, num_blocks)
        self.embed_dim = embed_dim

    def forward(
        self, x_opt: torch.Tensor, x_sar: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Encode optical and SAR inputs independently.

        Parameters
        ----------
        x_opt : Tensor of shape (B, T, C_opt, H, W)
        x_sar : Tensor of shape (B, T, C_sar, H, W)

        Returns
        -------
        h_opt : Tensor of shape (B, T, D, H', W')
        h_sar : Tensor of shape (B, T, D, H', W')
        """
        B, T = x_opt.shape[:2]

        # Flatten batch and time for convolution
        x_opt_flat = x_opt.reshape(B * T, *x_opt.shape[2:])
        x_sar_flat = x_sar.reshape(B * T, *x_sar.shape[2:])

        h_opt = self.optical_encoder(x_opt_flat)
        h_sar = self.sar_encoder(x_sar_flat)

        # Restore time dimension
        _, D, Hp, Wp = h_opt.shape
        h_opt = h_opt.reshape(B, T, D, Hp, Wp)
        h_sar = h_sar.reshape(B, T, D, Hp, Wp)

        return h_opt, h_sar
