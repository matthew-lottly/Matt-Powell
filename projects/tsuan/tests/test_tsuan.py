"""Tests for TSUAN model components."""

from __future__ import annotations

import pytest
import torch

from tsuan.config import TSUANConfig, EncoderConfig, AttentionConfig
from tsuan.encoder import DualStreamEncoder
from tsuan.attention import (
    UncertaintyEncoder,
    DynamicTemperature,
    IntraModalAttention,
    CrossModalAttention,
    TSUANAttentionBlock,
)
from tsuan.uncertainty import HierarchicalUncertainty
from tsuan.decoder import Decoder
from tsuan.model import TSUAN, EMAModel
from tsuan.losses import (
    ReconstructionLoss,
    UncertaintyCalibrationLoss,
    PhysicalConsistencyLoss,
    TemporalSmoothnessLoss,
    TSUANLoss,
)


# Small config for fast tests
def _test_cfg() -> TSUANConfig:
    from tsuan.config import UncertaintyConfig, DecoderConfig
    return TSUANConfig(
        encoder=EncoderConfig(
            optical_in_channels=4,
            sar_in_channels=2,
            embed_dim=16,
            num_cnn_blocks=2,
        ),
        attention=AttentionConfig(embed_dim=16, num_heads=4, dropout=0.0),
        uncertainty=UncertaintyConfig(embed_dim=16),
        decoder=DecoderConfig(embed_dim=16, out_channels=4, num_upsample_blocks=2),
    )


B, T, H, W = 2, 3, 32, 32
C_OPT, C_SAR, D = 4, 2, 16


class TestEncoder:
    def test_output_shape(self):
        enc = DualStreamEncoder(C_OPT, C_SAR, D, num_blocks=2)
        x_opt = torch.randn(B, T, C_OPT, H, W)
        x_sar = torch.randn(B, T, C_SAR, H, W)
        h_opt, h_sar = enc(x_opt, x_sar)

        assert h_opt.shape[0] == B
        assert h_opt.shape[1] == T
        assert h_opt.shape[2] == D
        assert h_sar.shape == h_opt.shape

    def test_spatial_downsampling(self):
        enc = DualStreamEncoder(C_OPT, C_SAR, D, num_blocks=2)
        x_opt = torch.randn(B, T, C_OPT, H, W)
        x_sar = torch.randn(B, T, C_SAR, H, W)
        h_opt, _ = enc(x_opt, x_sar)

        # 2 blocks with stride 2 → H/4, W/4
        assert h_opt.shape[-2] == H // 4
        assert h_opt.shape[-1] == W // 4


class TestAttention:
    def test_uncertainty_encoder(self):
        ue = UncertaintyEncoder(D)
        u_mask = torch.rand(B, T, 1, H // 4, W // 4)
        u_enc = ue(u_mask)
        assert u_enc.shape == (B, T, D, H // 4, W // 4)

    def test_dynamic_temperature(self):
        dt = DynamicTemperature(D)
        h = torch.randn(B, T, D, H // 4, W // 4)
        u_enc = torch.randn(B, T, D, H // 4, W // 4)
        lam = dt(h, u_enc)
        assert lam.shape == (B, T, 1, H // 4, W // 4)
        assert (lam > 0).all()  # Softplus is always positive

    def test_intra_modal_attention(self):
        attn = IntraModalAttention(D, num_heads=4)
        Hp, Wp = H // 4, W // 4
        h = torch.randn(B, T, D, Hp, Wp)
        u_enc = torch.randn(B, T, D, Hp, Wp)
        lam = torch.ones(B, T, 1, Hp, Wp)
        z = attn(h, u_enc, lam)
        assert z.shape == h.shape

    def test_cross_modal_attention(self):
        attn = CrossModalAttention(D, num_heads=4)
        Hp, Wp = H // 4, W // 4
        h_opt = torch.randn(B, T, D, Hp, Wp)
        h_sar = torch.randn(B, T, D, Hp, Wp)
        z = attn(h_opt, h_sar)
        assert z.shape == h_opt.shape

    def test_full_attention_block(self):
        block = TSUANAttentionBlock(D, num_heads=4)
        Hp, Wp = H // 4, W // 4
        h_opt = torch.randn(B, T, D, Hp, Wp)
        h_sar = torch.randn(B, T, D, Hp, Wp)
        u_mask = torch.rand(B, T, 1, Hp, Wp)
        z = block(h_opt, h_sar, u_mask)
        assert z.shape == h_opt.shape


class TestUncertainty:
    def test_hierarchical_output_shapes(self):
        unc = HierarchicalUncertainty(D)
        Hp, Wp = H // 4, W // 4
        z = torch.randn(B, T, D, Hp, Wp)
        s_pixel, s_patch, s_region = unc(z)

        assert s_pixel.shape == (B, T, 1, Hp, Wp)
        assert s_region.shape == (B, T, 1)
        # All uncertainty values should be positive (Softplus)
        assert (s_pixel > 0).all()
        assert (s_region > 0).all()


class TestDecoder:
    def test_output_shape(self):
        dec = Decoder(embed_dim=D, out_channels=C_OPT, num_blocks=2)
        Hp, Wp = H // 4, W // 4
        z = torch.randn(B, T, D, Hp, Wp)
        x_hat = dec(z)
        assert x_hat.shape == (B, T, C_OPT, H, W)


class TestLosses:
    def test_reconstruction_loss(self):
        loss_fn = ReconstructionLoss()
        x_hat = torch.randn(B, T, C_OPT, H, W)
        x_target = torch.randn(B, T, C_OPT, H, W)
        clear_mask = torch.ones(B, T, 1, H, W)
        loss = loss_fn(x_hat, x_target, clear_mask)
        assert loss.ndim == 0
        assert loss > 0

    def test_uncertainty_calibration_loss(self):
        loss_fn = UncertaintyCalibrationLoss()
        x_hat = torch.randn(B, T, C_OPT, H, W)
        x_target = torch.randn(B, T, C_OPT, H, W)
        sigma_sq = torch.ones(B, T, 1, H, W)
        clear_mask = torch.ones(B, T, 1, H, W)
        loss = loss_fn(x_hat, x_target, sigma_sq, clear_mask)
        assert loss.ndim == 0

    def test_physical_consistency_loss(self):
        loss_fn = PhysicalConsistencyLoss(red_idx=2, nir_idx=3, blue_idx=0)
        x_hat = torch.rand(B, T, C_OPT, H, W) * 2 - 0.5  # some values out of range
        loss = loss_fn(x_hat)
        assert loss.ndim == 0
        assert loss >= 0

    def test_temporal_smoothness(self):
        loss_fn = TemporalSmoothnessLoss()
        x_hat = torch.randn(B, T, C_OPT, H, W)
        loss = loss_fn(x_hat)
        assert loss.ndim == 0
        assert loss >= 0

    def test_combined_loss(self):
        loss_fn = TSUANLoss()
        x_hat = torch.randn(B, T, C_OPT, H, W)
        x_target = torch.randn(B, T, C_OPT, H, W)
        sigma_sq = torch.ones(B, T, 1, H, W)
        clear_mask = torch.ones(B, T, 1, H, W)
        losses = loss_fn(x_hat, x_target, sigma_sq, clear_mask, epoch=5)
        assert "total" in losses
        assert "recon" in losses
        assert losses["total"].ndim == 0

    def test_curriculum_weight_ramps(self):
        loss_fn = TSUANLoss(curriculum_start_epoch=5, curriculum_ramp_epochs=10)
        assert loss_fn._curriculum_weight(0) == 0.0
        assert loss_fn._curriculum_weight(5) == 0.0
        assert 0.0 < loss_fn._curriculum_weight(10) < 1.0
        assert loss_fn._curriculum_weight(15) == 1.0


class TestModel:
    def test_full_forward(self):
        cfg = _test_cfg()
        model = TSUAN(cfg)
        x_opt = torch.randn(B, T, C_OPT, H, W)
        x_sar = torch.randn(B, T, C_SAR, H, W)
        u_mask = torch.rand(B, T, 1, H, W)

        out = model(x_opt, x_sar, u_mask)

        assert "x_hat" in out
        assert "sigma_pixel" in out
        assert "sigma_region" in out
        assert "cloud_logits" in out
        assert out["x_hat"].shape == (B, T, C_OPT, H, W)

    def test_ema_update(self):
        cfg = _test_cfg()
        model = TSUAN(cfg)
        ema = EMAModel(model, decay=0.99)

        # Perturb model params
        with torch.no_grad():
            for p in model.parameters():
                p.add_(torch.randn_like(p) * 0.1)

        ema.update(model)

        # EMA shadow should have moved toward new params
        for name, param in model.named_parameters():
            if name in ema.shadow:
                assert not torch.equal(ema.shadow[name], param.data)

    def test_default_config(self):
        cfg = TSUANConfig()
        assert cfg.encoder.optical_in_channels == 13
        assert cfg.encoder.sar_in_channels == 2
        assert cfg.attention.num_heads == 8
