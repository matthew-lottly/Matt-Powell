"""Export helpers for corridor and run artifacts."""

from __future__ import annotations

from pathlib import Path
import csv
import json

from .graph3d import VoxelKey
from .voxelizer import VoxelGrid


def export_corridor_csv(path: list[VoxelKey], grid: VoxelGrid, output_path: str | Path) -> Path:
    """Write corridor voxel centres as a CSV (columns: i, j, k, x, y, z)."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["i", "j", "k", "x", "y", "z"])
        for key in path:
            x, y, z = grid.world_coord(key)
            writer.writerow([key[0], key[1], key[2], float(x), float(y), float(z)])
    return output_path


def export_corridor_geojson(path: list[VoxelKey], grid: VoxelGrid, output_path: str | Path) -> Path:
    """Write corridor voxel centres as a GeoJSON FeatureCollection of Points."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    features = []
    for order, key in enumerate(path):
        x, y, z = grid.world_coord(key)
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [float(x), float(y), float(z)]},
                "properties": {"order": order, "i": key[0], "j": key[1], "k": key[2]},
            }
        )
    payload = {"type": "FeatureCollection", "features": features}
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output_path


def export_run_report(report: dict, output_path: str | Path) -> Path:
    """Write a JSON run report."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return output_path


def export_occupancy_grid(grid: VoxelGrid, output_path: str | Path) -> Path:
    """Write per-voxel occupancy as a CSV file (columns: i, j, k, x, y, z, occupancy)."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["i", "j", "k", "x", "y", "z", "occupancy"])
        for key in sorted(grid.counts):
            x, y, z = grid.world_coord(key)
            writer.writerow([key[0], key[1], key[2], float(x), float(y), float(z), round(grid.occupancy(key), 6)])
    return output_path


def export_vgf_grid(
    vgf: dict[tuple[int, int, int], float],
    grid: VoxelGrid,
    output_path: str | Path,
) -> Path:
    """Write per-voxel vertical gap fraction as a CSV file (columns: i, j, k, x, y, z, vgf)."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["i", "j", "k", "x", "y", "z", "vgf"])
        for key in sorted(vgf):
            x, y, z = grid.world_coord(key)
            writer.writerow([key[0], key[1], key[2], float(x), float(y), float(z), round(vgf[key], 6)])
    return output_path
