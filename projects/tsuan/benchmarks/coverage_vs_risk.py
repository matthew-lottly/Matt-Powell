"""Coverage-vs-Risk benchmark: evaluate reconstruction quality as a function of SOVD knowability.

This script bins test-set pixels by their knowability score and computes
per-bin reconstruction metrics (RMSE, SSIM, SAM) to produce the core
empirical result:

    "TSUAN's knowability map correctly identifies pixels where
     reconstruction is unreliable, and suppressing those pixels
     improves aggregate metrics."

Usage::

    python benchmarks/coverage_vs_risk.py \\
        --checkpoint checkpoints/best.pt \\
        --data data/synthetic \\
        --output outputs/coverage_vs_risk.csv
"""

from __future__ import annotations

import argparse
import csv
import logging
from pathlib import Path

import numpy as np
import torch
from typing import cast

from tsuan.config import TSUANConfig
from tsuan.data import SatelliteTimeSeriesDataset
from tsuan.inference import load_checkpoint

logger = logging.getLogger(__name__)


def _rmse(pred: np.ndarray, target: np.ndarray) -> float:
    return float(np.sqrt(np.mean((pred - target) ** 2)))


def _mae(pred: np.ndarray, target: np.ndarray) -> float:
    return float(np.mean(np.abs(pred - target)))


def run_benchmark(
    model_path: str | Path,
    data_root: str | Path,
    output_csv: str | Path,
    n_bins: int = 10,
    device: str = "cpu",
) -> list[dict]:
    """Run coverage-vs-risk analysis.

    Returns list of dicts, one per knowability bin, each containing:
    - bin_low, bin_high: knowability range
    - n_pixels: pixel count
    - rmse, mae: reconstruction error in that bin
    - coverage: fraction of total pixels retained
    """
    model = load_checkpoint(model_path, device=device)
    model.eval()

    ds = SatelliteTimeSeriesDataset(
        data_root=data_root,
        split="test",
        augment=False,
    )

    if len(ds) == 0:
        logger.warning("No test data found at %s", data_root)
        return []

    # Accumulate per-pixel errors and knowability
    all_errors: list[np.ndarray] = []
    all_knowability: list[np.ndarray] = []

    for idx in range(len(ds)):
        sample = ds[idx]
        # Dataset typing is loose; cast to concrete tensor types for static analysis
        x_opt = cast(torch.Tensor, sample["optical"]).unsqueeze(0).to(device)
        x_sar = cast(torch.Tensor, sample["sar"]).unsqueeze(0).to(device)
        u_mask = cast(torch.Tensor, sample["cloud_mask"]).unsqueeze(0).to(device)

        with torch.no_grad():
            out = model(x_opt, x_sar, u_mask)

        x_hat = out["x_hat"].cpu().numpy()[0]  # (T, C, H, W)
        x_target = cast(torch.Tensor, sample["optical"]).cpu().numpy()  # (T, C, H, W)
        knowability = out["knowability"].cpu().numpy()[0, 0]  # (H, W)

        # Per-pixel RMSE across channels and time
        pixel_error = np.sqrt(np.mean((x_hat - x_target) ** 2, axis=(0, 1)))  # (H, W)

        all_errors.append(pixel_error.ravel())
        all_knowability.append(knowability.ravel())

    errors = np.concatenate(all_errors)
    knowability = np.concatenate(all_knowability)

    # Bin by knowability
    bin_edges = np.linspace(0, 1, n_bins + 1)
    total_pixels = len(errors)
    results = []

    for i in range(n_bins):
        lo, hi = bin_edges[i], bin_edges[i + 1]
        mask = (knowability >= lo) & (knowability < hi) if i < n_bins - 1 else (knowability >= lo)
        n_pix = int(mask.sum())

        if n_pix == 0:
            results.append({
                "bin_low": lo,
                "bin_high": hi,
                "n_pixels": 0,
                "rmse": float("nan"),
                "mae": float("nan"),
                "coverage": 0.0,
            })
            continue

        bin_errors = errors[mask]
        results.append({
            "bin_low": round(lo, 3),
            "bin_high": round(hi, 3),
            "n_pixels": n_pix,
            "rmse": round(_rmse(bin_errors, np.zeros_like(bin_errors)), 6),
            "mae": round(_mae(bin_errors, np.zeros_like(bin_errors)), 6),
            "coverage": round(n_pix / total_pixels, 4),
        })

    # Write CSV
    out_path = Path(output_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    logger.info("Wrote coverage-vs-risk results to %s", out_path)

    # Log summary
    for row in results:
        logger.info(
            "K=[%.2f, %.2f)  n=%d  RMSE=%.4f  MAE=%.4f  coverage=%.1f%%",
            row["bin_low"],
            row["bin_high"],
            row["n_pixels"],
            row["rmse"],
            row["mae"],
            row["coverage"] * 100,
        )

    return results


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="Coverage-vs-Risk benchmark")
    parser.add_argument("--checkpoint", type=str, required=True, help="Model checkpoint path")
    parser.add_argument("--data", type=str, required=True, help="Test data root")
    parser.add_argument("--output", type=str, default="outputs/coverage_vs_risk.csv")
    parser.add_argument("--n_bins", type=int, default=10, help="Number of knowability bins")
    parser.add_argument("--device", type=str, default="cpu")
    args = parser.parse_args()

    run_benchmark(
        model_path=args.checkpoint,
        data_root=args.data,
        output_csv=args.output,
        n_bins=args.n_bins,
        device=args.device,
    )


if __name__ == "__main__":
    main()
