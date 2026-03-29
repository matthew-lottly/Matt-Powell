"""Experiment and model configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
import logging


@dataclass
class EncoderConfig:
    optical_in_channels: int = 13  # Sentinel-2 L2A bands
    sar_in_channels: int = 2  # Sentinel-1 VV+VH
    embed_dim: int = 128
    backbone: Literal["cnn", "prithvi"] = "cnn"
    pretrained_weights: str | None = None
    num_cnn_blocks: int = 4


@dataclass
class AttentionConfig:
    embed_dim: int = 128
    num_heads: int = 8
    dropout: float = 0.1
    lambda_init: float = 1.0  # dynamic temperature initial value
    physical_penalty_weight: float = 0.1  # P_viol weight in cross-modal attention


@dataclass
class UncertaintyConfig:
    embed_dim: int = 128
    pixel_out_channels: int = 1  # 1×1 conv head
    patch_kernel: int = 3  # 3×3 conv head
    eta: float = 0.5  # TTA variance scaling


@dataclass
class DecoderConfig:
    embed_dim: int = 128
    out_channels: int = 13  # reconstruct optical bands
    num_upsample_blocks: int = 4


@dataclass
class LossConfig:
    alpha_unc: float = 0.1  # alpha_1: NLL uncertainty calibration
    alpha_phys: float = 0.05  # alpha_2: physical consistency (NDVI/EVI)
    alpha_smooth: float = 0.01  # alpha_3: temporal smoothness
    alpha_aux: float = 0.01  # alpha_4: auxiliary multi-task
    curriculum_start_epoch: int = 0
    curriculum_ramp_epochs: int = 10  # linear ramp for loss weights


@dataclass
class TrainConfig:
    batch_size: int = 8
    lr: float = 1e-4
    weight_decay: float = 1e-5
    max_epochs: int = 100
    warmup_epochs: int = 5
    grad_clip_norm: float = 1.0
    mixed_precision: bool = True
    ema_decay: float = 0.999
    seed: int = 42
    checkpoint_dir: str = "checkpoints"
    log_dir: str = "logs"


@dataclass
class DataConfig:
    data_root: str = "data"
    dataset: Literal["rice1", "rice2", "sen12ms", "custom"] = "sen12ms"
    patch_size: int = 256
    temporal_length: int = 12  # number of time steps
    cloud_threshold: float = 0.3  # minimum cloud cover to qualify as cloudy
    train_split: float = 0.8
    val_split: float = 0.1
    num_workers: int = 4
    augment: bool = True


@dataclass
class InferenceConfig:
    tta_transforms: int = 8  # number of TTA augmentations
    batch_size: int = 1
    device: str = "cpu"
    onnx_export: bool = False
    onnx_path: str = "tsuan.onnx"
    quantize_int8: bool = False


@dataclass
class TSUANConfig:
    encoder: EncoderConfig = field(default_factory=EncoderConfig)
    attention: AttentionConfig = field(default_factory=AttentionConfig)
    uncertainty: UncertaintyConfig = field(default_factory=UncertaintyConfig)
    decoder: DecoderConfig = field(default_factory=DecoderConfig)
    loss: LossConfig = field(default_factory=LossConfig)
    train: TrainConfig = field(default_factory=TrainConfig)
    data: DataConfig = field(default_factory=DataConfig)
    inference: InferenceConfig = field(default_factory=InferenceConfig)

    @classmethod
    def from_dict(cls, d: dict) -> TSUANConfig:
        cfg = cls()
        for section_name, section_cls in [
            ("encoder", EncoderConfig),
            ("attention", AttentionConfig),
            ("uncertainty", UncertaintyConfig),
            ("decoder", DecoderConfig),
            ("loss", LossConfig),
            ("train", TrainConfig),
            ("data", DataConfig),
            ("inference", InferenceConfig),
        ]:
            if section_name in d:
                setattr(cfg, section_name, section_cls(**d[section_name]))
        return cfg

    def __post_init__(self) -> None:
        """Validate and align embedding dimensions.

        Rules:
        - The encoder's `embed_dim` is the canonical latent dimensionality produced by
          the encoder. Align `attention.embed_dim`, `decoder.embed_dim`, and
          `uncertainty.embed_dim` to this value to avoid downstream channel mismatches.
        """
        logger = logging.getLogger(__name__)
        enc_dim = getattr(self.encoder, "embed_dim", None)
        att_dim = getattr(self.attention, "embed_dim", None)

        if enc_dim is None:
            return

        if att_dim != enc_dim:
            logger.warning(
                "TSUANConfig: aligning attention.embed_dim (%s) to encoder.embed_dim (%s)",
                att_dim,
                enc_dim,
            )
            self.attention.embed_dim = enc_dim

        # Propagate canonical dimension to decoder and uncertainty
        self.decoder.embed_dim = enc_dim
        self.uncertainty.embed_dim = enc_dim
