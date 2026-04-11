"""Derive aligned raster layers from a LiDAR tile for resistance modeling."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from vp_lcp.lidar_io import load_lidar_data, normalize_heights_with_dtm
from vp_lcp.voxelizer import voxelize


def derive_rasters(
    lidar_path: str | Path,
    output_dir: str | Path,
    voxel_size: float,
    min_height: float,
    vegetation_classes: tuple[int, ...],
    bbox: tuple[float, float, float, float] | None,
) -> tuple[Path, Path, tuple[float, float, float, float], tuple[int, int]]:
    raw = load_lidar_data(lidar_path)
    if bbox is None:
        # Public EPT root nodes can be spatially sparse. Use median point
        # location instead of extent center so the default window lands on data.
        cx = float(np.median(raw.points[:, 0]))
        cy = float(np.median(raw.points[:, 1]))
        half = 1000.0
        bbox = (cx - half, cy - half, cx + half, cy + half)

    data = load_lidar_data(lidar_path, bbox=bbox)
    points = normalize_heights_with_dtm(
        data.points,
        classifications=data.classifications,
        ground_classes=(2,),
        cell_size=2.0,
    )
    keep = points[:, 2] >= min_height
    points = points[keep]
    classes = data.classifications[keep]
    veg_mask = np.isin(classes, np.asarray(vegetation_classes))

    grid = voxelize(points, voxel_size=voxel_size, veg_mask=veg_mask)
    if not grid.counts:
        raise ValueError("No occupied voxels found after filtering; cannot derive rasters.")

    max_i = max(k[0] for k in grid.counts) + 1
    max_j = max(k[1] for k in grid.counts) + 1

    occupancy = np.zeros((max_i, max_j), dtype=np.float32)
    mean_height = np.zeros((max_i, max_j), dtype=np.float32)

    cell_height_values: dict[tuple[int, int], list[float]] = {}
    for key in grid.counts:
        i, j, _ = key
        occupancy[i, j] += grid.occupancy(key)
        z = float(grid.world_coord(key)[2])
        cell_height_values.setdefault((i, j), []).append(z)

    for (i, j), zs in cell_height_values.items():
        mean_height[i, j] = float(np.mean(np.asarray(zs, dtype=np.float64)))

    # Use a simple finite-difference slope proxy from mean canopy/voxel height.
    grad_i, grad_j = np.gradient(mean_height)
    slope = np.hypot(grad_i, grad_j)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    slope_path = output_dir / "slope_raster.npy"
    landcover_path = output_dir / "landcover_raster.npy"
    np.save(slope_path, slope)
    np.save(landcover_path, occupancy)
    meta = {
        "bbox": [float(v) for v in bbox],
        "raster_shape": [int(max_i), int(max_j)],
        "voxel_size": float(voxel_size),
        "min_height": float(min_height),
    }
    (output_dir / "raster_metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return slope_path, landcover_path, bbox, (max_i, max_j)


def _parse_ints(raw: str) -> tuple[int, ...]:
    return tuple(int(x.strip()) for x in raw.split(",") if x.strip())


def _parse_bbox(raw: str | None) -> tuple[float, float, float, float] | None:
    if raw is None:
        return None
    vals = [float(x.strip()) for x in raw.split(",") if x.strip()]
    if len(vals) != 4:
        raise ValueError("--bbox must be xmin,ymin,xmax,ymax")
    return (vals[0], vals[1], vals[2], vals[3])


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Derive slope and landcover proxy rasters from a LiDAR tile.",
    )
    parser.add_argument("--lidar", required=True, help="Path to LAS/LAZ tile.")
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory where slope_raster.npy and landcover_raster.npy are saved.",
    )
    parser.add_argument("--voxel-size", type=float, default=3.0, help="Voxel size in meters.")
    parser.add_argument("--min-height", type=float, default=0.0, help="Minimum normalized height.")
    parser.add_argument(
        "--bbox",
        default=None,
        help="Optional bbox xmin,ymin,xmax,ymax. If omitted, uses a centered 2km x 2km window.",
    )
    parser.add_argument(
        "--vegetation-classes",
        default="2,3,4,5",
        help="Comma-separated LAS classes treated as vegetation.",
    )
    args = parser.parse_args(argv)

    slope_path, landcover_path, bbox, shape = derive_rasters(
        lidar_path=args.lidar,
        output_dir=args.output_dir,
        voxel_size=args.voxel_size,
        min_height=args.min_height,
        vegetation_classes=_parse_ints(args.vegetation_classes),
        bbox=_parse_bbox(args.bbox),
    )
    print(slope_path)
    print(landcover_path)
    print(f"bbox={bbox}")
    print(f"shape={shape}")


if __name__ == "__main__":
    main()
