"""Data loading for Sentinel-2/Sentinel-1 time series with cloud masks.

Supports:
- Sentinel-2 L2A multispectral (13 bands)
- Sentinel-1 SAR (VV + VH)
- Cloud probability masks (SCL-derived or external)
- Temporal stacking with configurable sequence length
- Data augmentation (flips, rotations, random crop)
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader


class SatelliteTimeSeriesDataset(Dataset):
    """Dataset for paired optical/SAR time series with cloud masks.

    Expected directory structure::

        data_root/
        ├── optical/     # Sentinel-2 patches as .npy (T, C, H, W)
        ├── sar/         # Sentinel-1 patches as .npy (T, 2, H, W)
        ├── cloud_mask/  # cloud probability masks as .npy (T, 1, H, W)
        └── splits/
            ├── train.txt
            ├── val.txt
            └── test.txt

    Each .txt file lists patch IDs (filenames without extension), one per line.
    """

    def __init__(
        self,
        data_root: str | Path,
        split: str = "train",
        temporal_length: int = 12,
        patch_size: int = 256,
        augment: bool = True,
    ):
        self.data_root = Path(data_root)
        self.temporal_length = temporal_length
        self.patch_size = patch_size
        self.augment = augment and split == "train"

        split_file = self.data_root / "splits" / f"{split}.txt"
        if split_file.exists():
            self.patch_ids = split_file.read_text().strip().splitlines()
        else:
            # Fallback: list all .npy in optical/
            optical_dir = self.data_root / "optical"
            if optical_dir.exists():
                self.patch_ids = [p.stem for p in sorted(optical_dir.glob("*.npy"))]
            else:
                self.patch_ids = []

    def __len__(self) -> int:
        return len(self.patch_ids)

    def _load_array(self, subdir: str, patch_id: str) -> np.ndarray:
        path = self.data_root / subdir / f"{patch_id}.npy"
        return np.load(path)

    def _temporal_sample(self, arr: np.ndarray) -> np.ndarray:
        """Sample or pad to fixed temporal length."""
        T = arr.shape[0]
        if T >= self.temporal_length:
            # Random contiguous window
            start = random.randint(0, T - self.temporal_length) if self.augment else 0
            return arr[start : start + self.temporal_length]
        # Pad with zeros if too short
        pad_shape = (self.temporal_length - T, *arr.shape[1:])
        return np.concatenate([arr, np.zeros(pad_shape, dtype=arr.dtype)], axis=0)

    def _spatial_crop(self, *arrays: np.ndarray) -> tuple[np.ndarray, ...]:
        """Random spatial crop to patch_size × patch_size."""
        H, W = arrays[0].shape[-2:]
        if H <= self.patch_size and W <= self.patch_size:
            return arrays
        top = random.randint(0, H - self.patch_size) if self.augment else 0
        left = random.randint(0, W - self.patch_size) if self.augment else 0
        return tuple(a[..., top : top + self.patch_size, left : left + self.patch_size] for a in arrays)

    def _augment(self, *arrays: np.ndarray) -> tuple[np.ndarray, ...]:
        """Random flip and 90-degree rotation."""
        if not self.augment:
            return arrays
        if random.random() > 0.5:
            arrays = tuple(np.flip(a, axis=-1).copy() for a in arrays)
        if random.random() > 0.5:
            arrays = tuple(np.flip(a, axis=-2).copy() for a in arrays)
        k = random.randint(0, 3)
        if k > 0:
            arrays = tuple(np.rot90(a, k, axes=(-2, -1)).copy() for a in arrays)
        return arrays

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        pid = self.patch_ids[idx]

        optical = self._load_array("optical", pid).astype(np.float32)
        sar = self._load_array("sar", pid).astype(np.float32)
        cloud_mask = self._load_array("cloud_mask", pid).astype(np.float32)

        # Temporal sampling
        optical = self._temporal_sample(optical)
        sar = self._temporal_sample(sar)
        cloud_mask = self._temporal_sample(cloud_mask)

        # Spatial crop
        optical, sar, cloud_mask = self._spatial_crop(optical, sar, cloud_mask)

        # Augmentation
        optical, sar, cloud_mask = self._augment(optical, sar, cloud_mask)

        # Clear mask: inverse of cloud mask (1 = clear)
        clear_mask = 1.0 - cloud_mask

        return {
            "optical": torch.from_numpy(optical.copy()),
            "sar": torch.from_numpy(sar.copy()),
            "cloud_mask": torch.from_numpy(cloud_mask.copy()),
            "clear_mask": torch.from_numpy(clear_mask.copy()),
            "patch_id": pid,
        }


def build_dataloaders(
    data_root: str | Path,
    batch_size: int = 8,
    temporal_length: int = 12,
    patch_size: int = 256,
    num_workers: int = 4,
    augment: bool = True,
) -> dict[str, DataLoader]:
    """Create train/val/test DataLoaders."""
    loaders = {}
    for split in ("train", "val", "test"):
        ds = SatelliteTimeSeriesDataset(
            data_root=data_root,
            split=split,
            temporal_length=temporal_length,
            patch_size=patch_size,
            augment=augment and split == "train",
        )
        if len(ds) == 0:
            continue
        loaders[split] = DataLoader(
            ds,
            batch_size=batch_size,
            shuffle=(split == "train"),
            num_workers=num_workers,
            pin_memory=True,
            drop_last=(split == "train"),
        )
    return loaders
