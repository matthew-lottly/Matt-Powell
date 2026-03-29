"""Training loop with curriculum learning, mixed precision, gradient clipping."""

from __future__ import annotations

import logging
import time
from pathlib import Path

import torch
import torch.nn as nn
from torch.cuda.amp import GradScaler, autocast
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR, LinearLR, SequentialLR

from .config import TSUANConfig
from .data import build_dataloaders
from .losses import TSUANLoss
from .model import EMAModel, TSUAN

logger = logging.getLogger(__name__)


class Trainer:
    """TSUAN training loop with curriculum scheduling."""

    def __init__(self, cfg: TSUANConfig | None = None):
        if cfg is None:
            cfg = TSUANConfig()
        self.cfg = cfg
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Model
        self.model = TSUAN(cfg).to(self.device)
        self.ema = EMAModel(self.model, decay=cfg.train.ema_decay)

        # Loss
        self.criterion = TSUANLoss(
            alpha_unc=cfg.loss.alpha_unc,
            alpha_phys=cfg.loss.alpha_phys,
            alpha_smooth=cfg.loss.alpha_smooth,
            alpha_aux=cfg.loss.alpha_aux,
            curriculum_start_epoch=cfg.loss.curriculum_start_epoch,
            curriculum_ramp_epochs=cfg.loss.curriculum_ramp_epochs,
        )

        # Optimizer
        self.optimizer = AdamW(
            self.model.parameters(),
            lr=cfg.train.lr,
            weight_decay=cfg.train.weight_decay,
        )

        # LR scheduler: warmup + cosine annealing
        warmup_scheduler = LinearLR(
            self.optimizer,
            start_factor=0.01,
            end_factor=1.0,
            total_iters=cfg.train.warmup_epochs,
        )
        cosine_scheduler = CosineAnnealingLR(
            self.optimizer,
            T_max=cfg.train.max_epochs - cfg.train.warmup_epochs,
        )
        self.scheduler = SequentialLR(
            self.optimizer,
            schedulers=[warmup_scheduler, cosine_scheduler],
            milestones=[cfg.train.warmup_epochs],
        )

        # Mixed precision
        self.scaler = GradScaler(enabled=cfg.train.mixed_precision)

        # Data
        self.loaders = build_dataloaders(
            data_root=cfg.data.data_root,
            batch_size=cfg.train.batch_size,
            temporal_length=cfg.data.temporal_length,
            patch_size=cfg.data.patch_size,
            num_workers=cfg.data.num_workers,
            augment=cfg.data.augment,
        )

        # Checkpointing
        self.checkpoint_dir = Path(cfg.train.checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def _train_epoch(self, epoch: int) -> dict[str, float]:
        self.model.train()
        meter: dict[str, float] = {}
        count = 0

        train_loader = self.loaders.get("train")
        if train_loader is None:
            logger.warning("No training data found.")
            return meter

        for batch in train_loader:
            x_opt = batch["optical"].to(self.device)
            x_sar = batch["sar"].to(self.device)
            u_mask = batch["cloud_mask"].to(self.device)
            clear_mask = batch["clear_mask"].to(self.device)

            self.optimizer.zero_grad(set_to_none=True)

            with autocast(enabled=self.cfg.train.mixed_precision):
                outputs = self.model(x_opt, x_sar, u_mask)
                losses = self.criterion(
                    x_hat=outputs["x_hat"],
                    x_target=x_opt,
                    sigma_sq=outputs["sigma_pixel"],
                    clear_mask=clear_mask,
                    cloud_logits=outputs["cloud_logits"],
                    cloud_target=u_mask[..., : outputs["cloud_logits"].shape[-2], : outputs["cloud_logits"].shape[-1]],
                    epoch=epoch,
                )

            self.scaler.scale(losses["total"]).backward()
            self.scaler.unscale_(self.optimizer)
            nn.utils.clip_grad_norm_(
                self.model.parameters(), self.cfg.train.grad_clip_norm
            )
            self.scaler.step(self.optimizer)
            self.scaler.update()

            self.ema.update(self.model)

            for k, v in losses.items():
                meter[k] = meter.get(k, 0.0) + v.item()
            count += 1

        return {k: v / max(count, 1) for k, v in meter.items()}

    @torch.no_grad()
    def _val_epoch(self) -> dict[str, float]:
        self.model.eval()
        meter: dict[str, float] = {}
        count = 0

        val_loader = self.loaders.get("val")
        if val_loader is None:
            return meter

        for batch in val_loader:
            x_opt = batch["optical"].to(self.device)
            x_sar = batch["sar"].to(self.device)
            u_mask = batch["cloud_mask"].to(self.device)
            clear_mask = batch["clear_mask"].to(self.device)

            outputs = self.model(x_opt, x_sar, u_mask)
            losses = self.criterion(
                x_hat=outputs["x_hat"],
                x_target=x_opt,
                sigma_sq=outputs["sigma_pixel"],
                clear_mask=clear_mask,
                epoch=0,
            )

            for k, v in losses.items():
                meter[k] = meter.get(k, 0.0) + v.item()
            count += 1

        return {k: v / max(count, 1) for k, v in meter.items()}

    def save_checkpoint(self, epoch: int, val_loss: float) -> None:
        path = self.checkpoint_dir / f"checkpoint_epoch{epoch:04d}.pt"
        torch.save(
            {
                "epoch": epoch,
                "model_state_dict": self.model.state_dict(),
                "optimizer_state_dict": self.optimizer.state_dict(),
                "scheduler_state_dict": self.scheduler.state_dict(),
                "val_loss": val_loss,
                "config": self.cfg,
            },
            path,
        )
        logger.info("Saved checkpoint: %s", path)

    def train(self) -> None:
        """Run full training loop."""
        logger.info("Starting training on %s", self.device)
        best_val = float("inf")

        for epoch in range(self.cfg.train.max_epochs):
            t0 = time.time()

            train_losses = self._train_epoch(epoch)
            val_losses = self._val_epoch()

            self.scheduler.step()

            elapsed = time.time() - t0
            val_total = val_losses.get("total", float("inf"))

            logger.info(
                "Epoch %d/%d  train_loss=%.4f  val_loss=%.4f  lr=%.2e  time=%.1fs",
                epoch + 1,
                self.cfg.train.max_epochs,
                train_losses.get("total", 0.0),
                val_total,
                self.optimizer.param_groups[0]["lr"],
                elapsed,
            )

            if val_total < best_val:
                best_val = val_total
                self.save_checkpoint(epoch, val_total)

        # Save final EMA model
        self.ema.apply(self.model)
        self.save_checkpoint(self.cfg.train.max_epochs, best_val)
        logger.info("Training complete. Best val loss: %.4f", best_val)
