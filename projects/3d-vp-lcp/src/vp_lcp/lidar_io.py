"""LiDAR point-cloud I/O utilities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Sequence

import laspy
import numpy as np
from numpy.typing import NDArray


@dataclass(slots=True)
class LidarData:
    """Loaded LiDAR point cloud and metadata."""

    points: NDArray[np.float64]
    classifications: NDArray[np.int_]
    metadata: dict[str, float | int]


def _summarize_points(
    points: NDArray[np.float64],
    classifications: NDArray[np.int_],
) -> dict[str, float | int]:
    if len(points) == 0:
        return {
            "point_count": 0,
            "xmin": 0.0,
            "ymin": 0.0,
            "zmin": 0.0,
            "xmax": 0.0,
            "ymax": 0.0,
            "zmax": 0.0,
            "class_count": 0,
        }
    return {
        "point_count": int(len(points)),
        "xmin": float(points[:, 0].min()),
        "ymin": float(points[:, 1].min()),
        "zmin": float(points[:, 2].min()),
        "xmax": float(points[:, 0].max()),
        "ymax": float(points[:, 1].max()),
        "zmax": float(points[:, 2].max()),
        "class_count": int(len(np.unique(classifications))),
    }


def load_lidar_data(
    filepath: str | Path,
    bbox: tuple[float, float, float, float] | None = None,
) -> LidarData:
    """Load LAS/LAZ data with classifications and metadata."""
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"LiDAR file not found: {filepath}")

    las = laspy.read(str(filepath))
    points: NDArray[np.float64] = np.column_stack(
        [np.asarray(las.x), np.asarray(las.y), np.asarray(las.z)]
    )
    classifications = np.asarray(las.classification, dtype=int)

    if bbox is not None:
        xmin, ymin, xmax, ymax = bbox
        if xmin >= xmax or ymin >= ymax:
            raise ValueError("Bounding box must satisfy xmin < xmax and ymin < ymax.")
        mask = (
            (points[:, 0] >= xmin)
            & (points[:, 0] <= xmax)
            & (points[:, 1] >= ymin)
            & (points[:, 1] <= ymax)
        )
        points = points[mask]
        classifications = classifications[mask]

    return LidarData(
        points=points,
        classifications=classifications,
        metadata=_summarize_points(points, classifications),
    )


def load_laz(
    filepath: str | Path,
    bbox: tuple[float, float, float, float] | None = None,
    classifications: Sequence[int] | None = None,
) -> NDArray[np.float64]:
    """Load a LAS/LAZ file and return an (N, 3) array of [x, y, z].

    Parameters
    ----------
    filepath:
        Path to the LAS or LAZ file.
    bbox:
        Optional (xmin, ymin, xmax, ymax) bounding box to clip the points.
    classifications:
        Optional list of point classification codes to keep.  If *None*, all
        points are kept.
    """
    data = load_lidar_data(filepath, bbox=bbox)
    pts = data.points
    cls_arr = data.classifications

    if classifications is not None:
        mask = np.isin(cls_arr, classifications)
        pts = pts[mask]

    return pts


def normalize_heights(
    pts: NDArray[np.float64],
    ground_percentile: float = 2.0,
) -> NDArray[np.float64]:
    """Subtract a simple ground estimate so heights are above ground level."""
    z_ground = np.percentile(pts[:, 2], ground_percentile)
    out = pts.copy()
    out[:, 2] -= z_ground
    return out


def normalize_heights_with_dtm(
    pts: NDArray[np.float64],
    classifications: NDArray[np.int_] | None = None,
    ground_classes: Sequence[int] = (2,),
    cell_size: float = 2.0,
) -> NDArray[np.float64]:
    """Normalize point heights using a gridded DTM estimate.

    Ground elevation is estimated per XY cell from ground-classified points when
    available, otherwise from the minimum z in the cell.
    """
    if len(pts) == 0:
        raise ValueError("Cannot normalize an empty point cloud.")

    origin_xy = pts[:, :2].min(axis=0)
    xy_index = np.floor((pts[:, :2] - origin_xy) / cell_size).astype(np.int64)

    ground_lookup: dict[tuple[int, int], float] = {}
    if classifications is not None:
        ground_mask = np.isin(classifications, np.asarray(tuple(ground_classes)))
    else:
        ground_mask = np.zeros(len(pts), dtype=bool)

    for idx, key_arr in enumerate(xy_index):
        key = (int(key_arr[0]), int(key_arr[1]))
        z_val = float(pts[idx, 2])
        if ground_mask[idx]:
            prev = ground_lookup.get(key)
            if prev is None or z_val < prev:
                ground_lookup[key] = z_val

    all_cell_min: dict[tuple[int, int], float] = {}
    for idx, key_arr in enumerate(xy_index):
        key = (int(key_arr[0]), int(key_arr[1]))
        z_val = float(pts[idx, 2])
        prev = all_cell_min.get(key)
        if prev is None or z_val < prev:
            all_cell_min[key] = z_val

    if not ground_lookup:
        ground_lookup = all_cell_min.copy()
    else:
        for key, z_val in all_cell_min.items():
            ground_lookup.setdefault(key, z_val)

    out = pts.copy()
    for idx, key_arr in enumerate(xy_index):
        key = (int(key_arr[0]), int(key_arr[1]))
        out[idx, 2] -= ground_lookup[key]

    return out


def clip_by_polygon(
    points: NDArray[np.float64],
    polygon_xy: NDArray[np.float64],
) -> NDArray[np.bool_]:
    """Return a boolean mask selecting points inside a 2-D polygon.

    Uses a vectorised ray-casting algorithm that handles arbitrary simple
    (possibly non-convex) polygons.

    Parameters
    ----------
    points:
        (N, 3) point array.  Only the XY columns are used.
    polygon_xy:
        (M, 2) array of polygon boundary vertices.  The polygon is closed
        automatically (the last vertex connects back to the first).
    """
    poly = np.asarray(polygon_xy, dtype=np.float64)
    n_verts = len(poly)
    px = points[:, 0]
    py = points[:, 1]
    inside = np.zeros(len(points), dtype=bool)
    j = n_verts - 1
    for i in range(n_verts):
        xi, yi = poly[i, 0], poly[i, 1]
        xj, yj = poly[j, 0], poly[j, 1]
        cond = ((yi > py) != (yj > py)) & (
            px < (xj - xi) * (py - yi) / (yj - yi + 1e-12) + xi
        )
        inside ^= cond
        j = i
    return inside


def load_lidar_in_tiles(
    filepath: str | Path,
    tile_size: float,
    bbox: tuple[float, float, float, float] | None = None,
    classifications: Sequence[int] | None = None,
) -> Iterator[NDArray[np.float64]]:
    """Load a LAS/LAZ file in square XY tiles to limit per-chunk memory use.

    Reads the full file once, then yields one (N, 3) point array per
    non-empty tile.

    Parameters
    ----------
    filepath:
        Path to the LAS/LAZ file.
    tile_size:
        Side length of each square tile in the same units as the point cloud.
    bbox:
        Optional (xmin, ymin, xmax, ymax) bounding box applied before tiling.
    classifications:
        Optional whitelist of LAS classification codes to keep.
    """
    data = load_lidar_data(filepath, bbox=bbox)
    pts = data.points
    if classifications is not None:
        mask = np.isin(data.classifications, np.asarray(list(classifications)))
        pts = pts[mask]
    if len(pts) == 0:
        return

    xmin = float(pts[:, 0].min())
    ymin = float(pts[:, 1].min())
    xmax = float(pts[:, 0].max())
    ymax = float(pts[:, 1].max())

    n_x = int(np.floor((xmax - xmin) / tile_size)) + 1
    n_y = int(np.floor((ymax - ymin) / tile_size)) + 1

    for tx in range(n_x):
        for ty in range(n_y):
            tx_lo = xmin + tx * tile_size
            tx_hi = tx_lo + tile_size
            ty_lo = ymin + ty * tile_size
            ty_hi = ty_lo + tile_size
            mask = (
                (pts[:, 0] >= tx_lo)
                & (pts[:, 0] < tx_hi)
                & (pts[:, 1] >= ty_lo)
                & (pts[:, 1] < ty_hi)
            )
            tile_pts = pts[mask]
            if len(tile_pts) > 0:
                yield tile_pts
