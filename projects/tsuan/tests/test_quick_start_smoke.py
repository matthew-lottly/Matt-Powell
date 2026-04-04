from __future__ import annotations

import torch

from tsuan.config import AttentionConfig, DecoderConfig, EncoderConfig, TSUANConfig, UncertaintyConfig
from tsuan.inference import predict_with_tta
from tsuan.model import TSUAN


def test_quick_start_small_config_runs_end_to_end() -> None:
    cfg = TSUANConfig(
        encoder=EncoderConfig(optical_in_channels=4, sar_in_channels=2, embed_dim=16, num_cnn_blocks=2),
        attention=AttentionConfig(embed_dim=16, num_heads=4, dropout=0.0),
        uncertainty=UncertaintyConfig(embed_dim=16),
        decoder=DecoderConfig(embed_dim=16, out_channels=4, num_upsample_blocks=2),
    )
    model = TSUAN(cfg)
    model.eval()

    x_opt = torch.randn(1, 2, 4, 32, 32)
    x_sar = torch.randn(1, 2, 2, 32, 32)
    u_mask = torch.rand(1, 2, 1, 32, 32)

    result = predict_with_tta(model, x_opt, x_sar, u_mask, n_augments=2, eta=0.5)

    assert result["x_hat"].shape == (1, 2, 4, 32, 32)
    assert result["sigma_pixel"].shape[0] == 1
