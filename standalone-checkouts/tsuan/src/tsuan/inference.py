"""Inference with test-time augmentation (TTA) and ONNX export (Eq 8).

TTA procedure:
    μ = mean(f(aug_k(x)))  for k = 1..K
    σ² = σ²_model + η · var(f(aug_k(x)))
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

from .config import TSUANConfig
from .model import TSUAN

logger = logging.getLogger(__name__)

# Geometric TTA transforms (flips + 90-degree rotations)
TTA_TRANSFORMS = [
    lambda x: x,
    lambda x: torch.flip(x, [-1]),
    lambda x: torch.flip(x, [-2]),
    lambda x: torch.flip(x, [-1, -2]),
    lambda x: torch.rot90(x, 1, [-2, -1]),
    lambda x: torch.rot90(x, 2, [-2, -1]),
    lambda x: torch.rot90(x, 3, [-2, -1]),
    lambda x: torch.flip(torch.rot90(x, 1, [-2, -1]), [-1]),
]

TTA_INVERSE = [
    lambda x: x,
    lambda x: torch.flip(x, [-1]),
    lambda x: torch.flip(x, [-2]),
    lambda x: torch.flip(x, [-1, -2]),
    lambda x: torch.rot90(x, -1, [-2, -1]),
    lambda x: torch.rot90(x, -2, [-2, -1]),
    lambda x: torch.rot90(x, -3, [-2, -1]),
    lambda x: torch.rot90(torch.flip(x, [-1]), -1, [-2, -1]),
]


@torch.no_grad()
def predict_with_tta(
    model: TSUAN,
    x_opt: torch.Tensor,
    x_sar: torch.Tensor,
    u_mask: torch.Tensor,
    n_augments: int = 8,
    eta: float = 0.5,
) -> dict[str, torch.Tensor]:
    """Run inference with TTA for improved predictions and uncertainty.

    Parameters
    ----------
    model : TSUAN model (eval mode)
    x_opt : Tensor (B, T, C_opt, H, W)
    x_sar : Tensor (B, T, C_sar, H, W)
    u_mask : Tensor (B, T, 1, H, W)
    n_augments : Number of TTA augmentations (max 8)
    eta : Variance scaling factor

    Returns
    -------
    Dict with:
        x_hat : mean prediction (B, T, C_opt, H, W)
        sigma_pixel : combined uncertainty (B, T, 1, H', W')
    """
    model.eval()
    n_augments = min(n_augments, len(TTA_TRANSFORMS))

    predictions = []
    uncertainties = []

    for k in range(n_augments):
        aug_fn = TTA_TRANSFORMS[k]
        inv_fn = TTA_INVERSE[k]

        # Apply augmentation to each tensor
        # Reshape to apply spatial transforms: merge B,T dims
        B, T = x_opt.shape[:2]
        x_opt_aug = aug_fn(x_opt.reshape(-1, *x_opt.shape[2:])).reshape(B, T, *x_opt.shape[2:])
        x_sar_aug = aug_fn(x_sar.reshape(-1, *x_sar.shape[2:])).reshape(B, T, *x_sar.shape[2:])
        u_mask_aug = aug_fn(u_mask.reshape(-1, *u_mask.shape[2:])).reshape(B, T, *u_mask.shape[2:])

        out = model(x_opt_aug, x_sar_aug, u_mask_aug)

        # Inverse-transform predictions AND uncertainty back
        x_hat_k = inv_fn(out["x_hat"].reshape(-1, *out["x_hat"].shape[2:])).reshape(B, T, *out["x_hat"].shape[2:])
        sigma_k = inv_fn(out["sigma_pixel"].reshape(-1, *out["sigma_pixel"].shape[2:])).reshape(B, T, *out["sigma_pixel"].shape[2:])
        predictions.append(x_hat_k)
        uncertainties.append(sigma_k)

    # Stack and compute statistics (Eq 8)
    preds = torch.stack(predictions, dim=0)  # (K, B, T, C, H, W)
    x_hat_mean = preds.mean(dim=0)
    pred_var = preds.var(dim=0).mean(dim=2, keepdim=True)  # average over channels

    sigma_model = torch.stack(uncertainties, dim=0).mean(dim=0)
    sigma_combined = sigma_model + eta * pred_var[..., : sigma_model.shape[-2], : sigma_model.shape[-1]]

    return {
        "x_hat": x_hat_mean,
        "sigma_pixel": sigma_combined,
    }


def load_checkpoint(
    checkpoint_path: str | Path,
    device: str = "cpu",
    cfg: TSUANConfig | None = None,
) -> TSUAN:
    """Load model from checkpoint."""
    ckpt = torch.load(checkpoint_path, map_location=device, weights_only=True)
    if cfg is None:
        raw = ckpt.get("config")
        if raw is not None and isinstance(raw, dict):
            cfg = TSUANConfig(**{
                k: v for k, v in raw.items()
                if k in {f.name for f in __import__("dataclasses").fields(TSUANConfig)}
            })
        else:
            cfg = TSUANConfig()
    model = TSUAN(cfg)
    model.load_state_dict(ckpt["model_state_dict"])
    model.to(device)
    model.eval()
    logger.info("Loaded checkpoint from %s (epoch %d)", checkpoint_path, ckpt.get("epoch", -1))
    return model


def export_onnx(
    model: TSUAN,
    output_path: str | Path = "tsuan.onnx",
    temporal_length: int = 12,
    patch_size: int = 256,
    opset_version: int = 17,
) -> None:
    """Export model to ONNX format."""
    model.eval()
    B = 1
    T = temporal_length
    H = W = patch_size
    cfg = model.cfg

    dummy_opt = torch.randn(B, T, cfg.encoder.optical_in_channels, H, W)
    dummy_sar = torch.randn(B, T, cfg.encoder.sar_in_channels, H, W)
    dummy_mask = torch.rand(B, T, 1, H, W)

    torch.onnx.export(
        model,
        (dummy_opt, dummy_sar, dummy_mask),
        str(output_path),
        opset_version=opset_version,
        input_names=["optical", "sar", "cloud_mask"],
        output_names=["x_hat", "sigma_pixel", "sigma_patch", "sigma_region", "cloud_logits"],
        dynamic_axes={
            "optical": {0: "batch", 1: "time", 3: "height", 4: "width"},
            "sar": {0: "batch", 1: "time", 3: "height", 4: "width"},
            "cloud_mask": {0: "batch", 1: "time", 3: "height", 4: "width"},
            "x_hat": {0: "batch", 1: "time", 3: "height", 4: "width"},
            "sigma_pixel": {0: "batch", 1: "time"},
            "sigma_patch": {0: "batch", 1: "time"},
            "sigma_region": {0: "batch", 1: "time"},
            "cloud_logits": {0: "batch", 1: "time"},
        },
    )
    logger.info("Exported ONNX model to %s", output_path)
