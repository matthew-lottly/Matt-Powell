"""Symmetric CNN decoder for spatial upsampling and band reconstruction."""

from __future__ import annotations

import torch
import torch.nn as nn


class UpsampleBlock(nn.Module):
    """ConvTranspose2d → BatchNorm → GELU for 2× upsampling."""

    def __init__(self, in_ch: int, out_ch: int):
        super().__init__()
        self.block = nn.Sequential(
            nn.ConvTranspose2d(
                in_ch, out_ch, kernel_size=4, stride=2, padding=1, bias=False
            ),
            nn.BatchNorm2d(out_ch),
            nn.GELU(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.block(x)


class Decoder(nn.Module):
    """Symmetric upsampling decoder.

    Progressively upsamples from (D, H', W') back to (C_out, H, W)
    where H = H' × 2^num_blocks, W = W' × 2^num_blocks.
    """

    def __init__(self, embed_dim: int = 128, out_channels: int = 13, num_blocks: int = 4):
        super().__init__()
        channels = []
        ch = embed_dim
        for _ in range(num_blocks - 1):
            next_ch = max(ch // 2, out_channels)
            channels.append((ch, next_ch))
            ch = next_ch
        channels.append((ch, out_channels))

        self.blocks = nn.ModuleList(
            [UpsampleBlock(in_ch, out_ch) for in_ch, out_ch in channels[:-1]]
        )
        # Final block without activation (raw reconstruction)
        in_ch, out_ch = channels[-1]
        self.final = nn.ConvTranspose2d(
            in_ch, out_ch, kernel_size=4, stride=2, padding=1
        )

    def forward(self, z: torch.Tensor) -> torch.Tensor:
        """Decode latent features to reconstructed image.

        Parameters
        ----------
        z : Tensor (B, T, D, H', W')

        Returns
        -------
        x_hat : Tensor (B, T, C_out, H, W)
        """
        B, T, D, Hp, Wp = z.shape
        z_flat = z.reshape(B * T, D, Hp, Wp)

        for block in self.blocks:
            z_flat = block(z_flat)
        x_hat = self.final(z_flat)

        _, C, H, W = x_hat.shape
        return x_hat.reshape(B, T, C, H, W)
