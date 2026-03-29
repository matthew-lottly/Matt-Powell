"""Full TSUAN model composing encoder, attention, uncertainty, and decoder."""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F

from .attention import TSUANAttentionBlock
from .config import TSUANConfig
from .decoder import Decoder
from .encoder import DualStreamEncoder
from .uncertainty import HierarchicalUncertainty


class TSUAN(nn.Module):
    """Temporal-Spatial Uncertainty-Aware Attention Network.

    Architecture:
        1. Dual-stream encoder: optical + SAR → h_opt, h_sar
        2. Uncertainty-weighted attention block (intra + cross-modal)
        3. Symmetric CNN decoder → reconstructed image
        4. Hierarchical uncertainty heads (pixel/patch/region)
        5. Optional auxiliary cloud segmentation head
    """

    def __init__(self, cfg: TSUANConfig | None = None):
        super().__init__()
        if cfg is None:
            cfg = TSUANConfig()
        self.cfg = cfg

        # Encoder
        self.encoder = DualStreamEncoder(
            optical_in_channels=cfg.encoder.optical_in_channels,
            sar_in_channels=cfg.encoder.sar_in_channels,
            embed_dim=cfg.encoder.embed_dim,
            num_blocks=cfg.encoder.num_cnn_blocks,
        )

        # Attention
        self.attention = TSUANAttentionBlock(
            embed_dim=cfg.attention.embed_dim,
            num_heads=cfg.attention.num_heads,
            dropout=cfg.attention.dropout,
            gamma=cfg.attention.physical_penalty_weight,
        )

        # Decoder
        self.decoder = Decoder(
            embed_dim=cfg.decoder.embed_dim,
            out_channels=cfg.decoder.out_channels,
            num_blocks=cfg.decoder.num_upsample_blocks,
        )

        # Hierarchical uncertainty
        self.uncertainty = HierarchicalUncertainty(
            embed_dim=cfg.uncertainty.embed_dim,
            patch_kernel=cfg.uncertainty.patch_kernel,
        )

        # Auxiliary cloud segmentation head (optional)
        self.cloud_head = nn.Conv2d(cfg.encoder.embed_dim, 1, kernel_size=1)

    def forward(
        self,
        x_opt: torch.Tensor,
        x_sar: torch.Tensor,
        u_mask: torch.Tensor,
    ) -> dict[str, torch.Tensor]:
        """Forward pass.

        Parameters
        ----------
        x_opt : Tensor (B, T, C_opt, H, W) — Sentinel-2 optical
        x_sar : Tensor (B, T, C_sar, H, W) — Sentinel-1 SAR
        u_mask : Tensor (B, T, 1, H, W) — cloud probability mask

        Returns
        -------
        Dict with keys:
            x_hat : Tensor (B, T, C_opt, H, W) — reconstructed optical
            sigma_pixel : Tensor (B, T, 1, H', W')
            sigma_patch : Tensor (B, T, 1, ...)
            sigma_region : Tensor (B, T, 1)
            cloud_logits : Tensor (B, T, 1, H', W')
        """
        # 1. Encode
        h_opt, h_sar = self.encoder(x_opt, x_sar)

        # Downsample cloud mask to match encoder spatial output
        B, T, _, H, W = u_mask.shape
        _, _, _, Hp, Wp = h_opt.shape
        u_mask_ds = F.interpolate(
            u_mask.reshape(B * T, 1, H, W),
            size=(Hp, Wp),
            mode="bilinear",
            align_corners=False,
        ).reshape(B, T, 1, Hp, Wp)

        # 2. Attention
        z = self.attention(h_opt, h_sar, u_mask_ds)

        # 3. Decode
        x_hat = self.decoder(z)

        # 4. Uncertainty
        sigma_pixel, sigma_patch, sigma_region = self.uncertainty(z)

        # 5. Auxiliary cloud logits
        z_flat = z.reshape(B * T, *z.shape[2:])
        cloud_logits = self.cloud_head(z_flat).reshape(B, T, 1, Hp, Wp)

        return {
            "x_hat": x_hat,
            "sigma_pixel": sigma_pixel,
            "sigma_patch": sigma_patch,
            "sigma_region": sigma_region,
            "cloud_logits": cloud_logits,
        }


class EMAModel:
    """Exponential Moving Average of model parameters for stable inference."""

    def __init__(self, model: nn.Module, decay: float = 0.999):
        self.decay = decay
        self.shadow: dict[str, torch.Tensor] = {}
        for name, param in model.named_parameters():
            if param.requires_grad:
                self.shadow[name] = param.data.clone()

    @torch.no_grad()
    def update(self, model: nn.Module) -> None:
        for name, param in model.named_parameters():
            if name in self.shadow:
                self.shadow[name].mul_(self.decay).add_(param.data, alpha=1 - self.decay)

    def apply(self, model: nn.Module) -> None:
        for name, param in model.named_parameters():
            if name in self.shadow:
                param.data.copy_(self.shadow[name])
