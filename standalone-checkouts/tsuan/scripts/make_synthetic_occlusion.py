"""Generate synthetic persistent-occlusion datasets for SOVD evaluation.

Creates controlled test scenarios where specific spatial regions are
persistently clouded across all or most time steps:

1. **Random blobs** — Gaussian-smoothed random patches with tunable
   persistence probability per pixel.
2. **Structured voids** — Rectangular or circular regions that are *always*
   clouded (100 % cloud frequency), simulating mountain-shadow or
   tropical-monsoon zones.
3. **Gradual decay** — Cloud probability increases linearly toward one
   edge, testing the soft-knowability sigmoid boundary.

Outputs are saved in the standard TSUAN data layout::

    output_dir/
    ├── optical/   patch_XXXX.npy  (T, C, H, W)
    ├── sar/       patch_XXXX.npy  (T, 2, H, W)
    ├── cloud_mask/ patch_XXXX.npy (T, 1, H, W)
    └── splits/
        ├── train.txt
        ├── val.txt
        └── test.txt

Usage::

    python scripts/make_synthetic_occlusion.py --output data/synthetic --n_patches 200
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


def _gaussian_blob_mask(
    H: int,
    W: int,
    n_blobs: int = 3,
    min_radius: int = 10,
    max_radius: int = 40,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """Generate a smooth cloud mask with Gaussian blobs.

    Returns binary-ish mask ∈ [0, 1] of shape (H, W).
    """
    if rng is None:
        rng = np.random.default_rng()

    mask = np.zeros((H, W), dtype=np.float32)
    yy, xx = np.mgrid[:H, :W]

    for _ in range(n_blobs):
        cy = rng.integers(0, H)
        cx = rng.integers(0, W)
        r = rng.integers(min_radius, max_radius + 1)
        dist_sq = (yy - cy) ** 2 + (xx - cx) ** 2
        mask += np.exp(-dist_sq / (2 * r**2))

    return np.clip(mask, 0.0, 1.0)


def _structured_void_mask(
    H: int,
    W: int,
    void_type: str = "rect",
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """Generate a binary structured-void mask.

    void_type: 'rect' or 'circle'
    Returns mask of shape (H, W) with 1.0 in void region.
    """
    if rng is None:
        rng = np.random.default_rng()

    mask = np.zeros((H, W), dtype=np.float32)

    if void_type == "rect":
        h = rng.integers(H // 6, H // 3)
        w = rng.integers(W // 6, W // 3)
        y0 = rng.integers(0, H - h)
        x0 = rng.integers(0, W - w)
        mask[y0 : y0 + h, x0 : x0 + w] = 1.0
    else:  # circle
        cy, cx = rng.integers(H // 4, 3 * H // 4), rng.integers(W // 4, 3 * W // 4)
        r = rng.integers(H // 8, H // 4)
        yy, xx = np.mgrid[:H, :W]
        mask[((yy - cy) ** 2 + (xx - cx) ** 2) <= r**2] = 1.0

    return mask


def _gradient_mask(H: int, W: int, axis: int = 1) -> np.ndarray:
    """Linear gradient from 0 to 1 along given axis."""
    if axis == 1:
        return np.tile(np.linspace(0, 1, W, dtype=np.float32), (H, 1))
    return np.tile(np.linspace(0, 1, H, dtype=np.float32)[:, None], (1, W))


def generate_patch(
    T: int = 12,
    C_opt: int = 13,
    C_sar: int = 2,
    H: int = 256,
    W: int = 256,
    mode: str = "blob",
    persistence: float = 0.7,
    rng: np.random.Generator | None = None,
) -> dict[str, np.ndarray]:
    """Generate a single synthetic patch.

    Parameters
    ----------
    T : int — number of time steps
    C_opt, C_sar : int — number of channels
    H, W : int — spatial dimensions
    mode : str — 'blob', 'void_rect', 'void_circle', 'gradient'
    persistence : float — temporal persistence probability for blobs
    rng : Generator

    Returns
    -------
    Dict with 'optical' (T,C_opt,H,W), 'sar' (T,C_sar,H,W),
    'cloud_mask' (T,1,H,W) as float32 NumPy arrays.
    """
    if rng is None:
        rng = np.random.default_rng()

    # Synthetic clean optical (random reflectance)
    optical_clean = rng.uniform(0, 1, (T, C_opt, H, W)).astype(np.float32)
    sar = rng.uniform(-30, 5, (T, C_sar, H, W)).astype(np.float32)

    # Generate spatial cloud pattern
    if mode == "blob":
        spatial = _gaussian_blob_mask(H, W, rng=rng)
    elif mode == "void_rect":
        spatial = _structured_void_mask(H, W, "rect", rng=rng)
    elif mode == "void_circle":
        spatial = _structured_void_mask(H, W, "circle", rng=rng)
    elif mode == "gradient":
        spatial = _gradient_mask(H, W)
    else:
        raise ValueError(f"Unknown mode: {mode}")

    # Generate temporal cloud masks with persistence
    cloud_mask = np.zeros((T, 1, H, W), dtype=np.float32)
    for t in range(T):
        # Each pixel: with prob=persistence, use spatial; else draw fresh noise
        keep = rng.random((H, W)) < persistence
        noise = rng.random((H, W)).astype(np.float32)
        cloud_mask[t, 0] = np.where(keep, spatial, noise * 0.3)

    # For structured voids, force the void region to be clouded in ALL time steps
    if mode.startswith("void_"):
        void_region = spatial > 0.5
        cloud_mask[:, 0, void_region] = 1.0

    # Apply cloud corruption to optical
    optical = optical_clean.copy()
    for t in range(T):
        cloud_expanded = cloud_mask[t]  # (1, H, W)
        optical[t] = optical_clean[t] * (1 - cloud_expanded) + cloud_expanded * 0.95

    return {
        "optical": optical,
        "sar": sar,
        "cloud_mask": cloud_mask,
    }


def generate_dataset(
    output_dir: str | Path,
    n_patches: int = 200,
    T: int = 12,
    C_opt: int = 13,
    C_sar: int = 2,
    H: int = 256,
    W: int = 256,
    seed: int = 42,
    train_frac: float = 0.7,
    val_frac: float = 0.15,
) -> None:
    """Generate a full synthetic dataset with controlled occlusion patterns."""
    output = Path(output_dir)
    for subdir in ("optical", "sar", "cloud_mask", "splits"):
        (output / subdir).mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(seed)
    modes = ["blob", "void_rect", "void_circle", "gradient"]
    patch_ids: list[str] = []

    for i in range(n_patches):
        mode = modes[i % len(modes)]
        pid = f"patch_{i:05d}"
        patch_ids.append(pid)

        patch = generate_patch(
            T=T, C_opt=C_opt, C_sar=C_sar, H=H, W=W,
            mode=mode, rng=rng,
        )

        np.save(output / "optical" / f"{pid}.npy", patch["optical"])
        np.save(output / "sar" / f"{pid}.npy", patch["sar"])
        np.save(output / "cloud_mask" / f"{pid}.npy", patch["cloud_mask"])

        if (i + 1) % 50 == 0:
            logger.info("Generated %d / %d patches", i + 1, n_patches)

    # Split
    rng.shuffle(patch_ids)
    n_train = int(n_patches * train_frac)
    n_val = int(n_patches * val_frac)

    splits = {
        "train": patch_ids[:n_train],
        "val": patch_ids[n_train : n_train + n_val],
        "test": patch_ids[n_train + n_val :],
    }

    for split_name, ids in splits.items():
        (output / "splits" / f"{split_name}.txt").write_text("\n".join(ids) + "\n")

    logger.info(
        "Dataset generated: %d patches (train=%d, val=%d, test=%d) at %s",
        n_patches,
        len(splits["train"]),
        len(splits["val"]),
        len(splits["test"]),
        output,
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="Generate synthetic occlusion dataset")
    parser.add_argument("--output", type=str, default="data/synthetic", help="Output directory")
    parser.add_argument("--n_patches", type=int, default=200, help="Number of patches")
    parser.add_argument("--T", type=int, default=12, help="Temporal length")
    parser.add_argument("--H", type=int, default=256, help="Patch height")
    parser.add_argument("--W", type=int, default=256, help="Patch width")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    generate_dataset(
        output_dir=args.output,
        n_patches=args.n_patches,
        T=args.T,
        H=args.H,
        W=args.W,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
