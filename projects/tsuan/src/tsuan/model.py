"""Full TSUAN model composing encoder, attention, uncertainty, and decoder."""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F

from .attention import TSUANAttentionBlock
from .config import TSUANConfig
from .decoder import Decoder
from .encoder import DualStreamEncoder
from .sovd import SOVDAnalyzer
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
        # Ensure decoder / uncertainty / cloud head use the attention embedding
        # dimension so channel sizes match the attention output `z`.
        att_dim = cfg.attention.embed_dim

        # Decoder
        self.decoder = Decoder(
            embed_dim=att_dim,
            out_channels=cfg.decoder.out_channels,
            num_blocks=cfg.decoder.num_upsample_blocks,
        )

        # Hierarchical uncertainty
        self.uncertainty = HierarchicalUncertainty(
            embed_dim=att_dim,
            patch_kernel=cfg.uncertainty.patch_kernel,
        )

        # Auxiliary cloud segmentation head (optional)
        self.cloud_head = nn.Conv2d(att_dim, 1, kernel_size=1)

        # SOVD — Structural Observational Void Detection
        self.sovd = SOVDAnalyzer(
            embed_dim=att_dim,
            void_threshold=cfg.sovd.void_threshold,
            temperature=cfg.sovd.temperature,
            refine=cfg.sovd.refine,
        )

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
            knowability : Tensor (B, 1, H, W) — soft knowability map [0, 1]
            void_mask : Tensor (B, 1, H, W) — binary persistent void mask
            cloud_freq : Tensor (B, 1, H, W) — temporal cloud frequency
        """
        # 0. SOVD — compute knowability from raw cloud masks
        sovd_out = self.sovd(u_mask)

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
            "knowability": sovd_out["knowability"],
            "void_mask": sovd_out["void_mask"],
            "cloud_freq": sovd_out["cloud_freq"],
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

    def state_dict(self) -> dict[str, torch.Tensor]:
        return {k: v.clone() for k, v in self.shadow.items()}

    def load_state_dict(self, state: dict[str, torch.Tensor]) -> None:
        for k, v in state.items():
            if k in self.shadow:
                self.shadow[k].copy_(v)
