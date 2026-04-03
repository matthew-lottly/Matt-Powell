"""Sparse voxelization of LiDAR point clouds."""

from __future__ import annotations

from collections import defaultdict

import numpy as np
from numpy.typing import NDArray


class VoxelGrid:
    """Sparse voxel grid built from a 3-D point cloud.

    Attributes
    ----------
    counts : dict[tuple[int,int,int], int]
        Number of returns per voxel.
    veg : dict[tuple[int,int,int], int]
        Number of vegetation-classified returns per voxel.
    origin : NDArray
        (3,) world-coordinate origin of the grid.
    voxel_size : float
        Edge length of each cubic voxel in metres.
    """

    def __init__(
        self,
        counts: dict[tuple[int, int, int], int],
        veg: dict[tuple[int, int, int], int],
        origin: NDArray[np.float64],
        voxel_size: float,
    ) -> None:
        self.counts = counts
        self.veg = veg
        self.origin = origin
        self.voxel_size = voxel_size

    def occupancy(self, key: tuple[int, int, int]) -> float:
        total = self.counts.get(key, 0)
        if total == 0:
            return 0.0
        return self.veg.get(key, 0) / total

    def world_coord(self, key: tuple[int, int, int]) -> NDArray[np.float64]:
        i, j, k = key
        return self.origin + np.array(
            [(i + 0.5) * self.voxel_size, (j + 0.5) * self.voxel_size, (k + 0.5) * self.voxel_size]
        )


def voxelize(
    points: NDArray[np.float64],
    voxel_size: float,
    origin: NDArray[np.float64] | None = None,
    veg_mask: NDArray[np.bool_] | None = None,
) -> VoxelGrid:
    """Convert an (N, 3) point array into a sparse voxel grid.

    Parameters
    ----------
    points:
        (N, 3) array of [x, y, z] coordinates (height-normalised).
    voxel_size:
        Edge length of each cubic voxel in metres.
    origin:
        Optional explicit origin; defaults to the point-cloud minimum.
    veg_mask:
        Boolean array of length N.  True marks vegetation returns.
        If *None*, all points are treated as vegetation.
    """
    if origin is None:
        origin = points.min(axis=0)

    indices = np.floor((points - origin) / voxel_size).astype(np.int64)

    counts: dict[tuple[int, int, int], int] = defaultdict(int)
    veg: dict[tuple[int, int, int], int] = defaultdict(int)

    if veg_mask is None:
        veg_mask = np.ones(len(points), dtype=bool)

    for row_idx in range(len(indices)):
        key = (int(indices[row_idx, 0]), int(indices[row_idx, 1]), int(indices[row_idx, 2]))
        counts[key] += 1
        if veg_mask[row_idx]:
            veg[key] += 1

    return VoxelGrid(dict(counts), dict(veg), origin.copy(), voxel_size)
