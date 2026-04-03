"""LiDAR point-cloud I/O utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import laspy
import numpy as np
from numpy.typing import NDArray


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
        Optional list of point classification codes to keep (e.g. [1, 3, 4, 5]
        for unclassified + vegetation).  If *None*, all points are kept.
    """
    filepath = Path(filepath)
    las = laspy.read(str(filepath))
    pts: NDArray[np.float64] = np.column_stack([las.x, las.y, las.z])

    if classifications is not None:
        cls_arr = np.asarray(las.classification)
        mask = np.isin(cls_arr, classifications)
        pts = pts[mask]

    if bbox is not None:
        xmin, ymin, xmax, ymax = bbox
        mask = (
            (pts[:, 0] >= xmin)
            & (pts[:, 0] <= xmax)
            & (pts[:, 1] >= ymin)
            & (pts[:, 1] <= ymax)
        )
        pts = pts[mask]

    return pts


def normalize_heights(
    pts: NDArray[np.float64],
    ground_percentile: float = 2.0,
) -> NDArray[np.float64]:
    """Subtract a simple ground estimate so heights are above ground level.

    For production work, replace this with a proper DTM-based normalization.
    """
    z_ground = np.percentile(pts[:, 2], ground_percentile)
    out = pts.copy()
    out[:, 2] -= z_ground
    return out
