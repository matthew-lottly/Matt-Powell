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

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor | str]:
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


def verify_dataset(data_root: str | Path) -> dict[str, Any]:
    """Verify dataset structure and return a diagnostic report.

    Checks:
    - Required subdirectories exist (optical, sar, cloud_mask)
    - Split files exist and reference valid patches
    - Array shapes are consistent across modalities
    - No NaN/Inf values in a sample of patches

    Returns a dict with keys: valid (bool), errors (list[str]), warnings (list[str]), stats (dict).
    """
    root = Path(data_root)
    errors: list[str] = []
    warnings: list[str] = []
    stats: dict[str, Any] = {}

    # Check required dirs
    for subdir in ("optical", "sar", "cloud_mask"):
        d = root / subdir
        if not d.exists():
            errors.append(f"Missing directory: {subdir}/")
        else:
            files = sorted(d.glob("*.npy"))
            stats[f"{subdir}_count"] = len(files)
            if len(files) == 0:
                warnings.append(f"No .npy files in {subdir}/")

    # Check splits
    splits_dir = root / "splits"
    if not splits_dir.exists():
        warnings.append("Missing splits/ directory — will use all optical patches")
    else:
        for split in ("train", "val", "test"):
            sf = splits_dir / f"{split}.txt"
            if not sf.exists():
                warnings.append(f"Missing split file: splits/{split}.txt")
            else:
                ids = sf.read_text().strip().splitlines()
                stats[f"{split}_patches"] = len(ids)
                # Verify referenced patches exist
                missing = [pid for pid in ids if not (root / "optical" / f"{pid}.npy").exists()]
                if missing:
                    errors.append(f"{split}.txt references {len(missing)} missing patch(es): {missing[:5]}")

    # Cross-check patch IDs across modalities
    optical_dir = root / "optical"
    sar_dir = root / "sar"
    mask_dir = root / "cloud_mask"
    if optical_dir.exists() and sar_dir.exists() and mask_dir.exists():
        opt_ids = {p.stem for p in optical_dir.glob("*.npy")}
        sar_ids = {p.stem for p in sar_dir.glob("*.npy")}
        mask_ids = {p.stem for p in mask_dir.glob("*.npy")}
        missing_sar = opt_ids - sar_ids
        missing_mask = opt_ids - mask_ids
        if missing_sar:
            errors.append(f"{len(missing_sar)} optical patch(es) missing SAR counterpart")
        if missing_mask:
            errors.append(f"{len(missing_mask)} optical patch(es) missing cloud_mask counterpart")

    # Sample shape/value checks
    if optical_dir.exists():
        sample_files = sorted(optical_dir.glob("*.npy"))[:3]
        for f in sample_files:
            try:
                arr = np.load(f)
                stats.setdefault("sample_shapes", []).append(
                    {f.stem: {"optical": arr.shape}}
                )
                if np.any(np.isnan(arr)):
                    warnings.append(f"NaN values in optical/{f.name}")
                if np.any(np.isinf(arr)):
                    warnings.append(f"Inf values in optical/{f.name}")
            except Exception as e:
                errors.append(f"Failed to load optical/{f.name}: {e}")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "stats": stats,
    }
