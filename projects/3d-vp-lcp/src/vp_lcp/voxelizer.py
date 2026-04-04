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
        Edge length in metres — the x-axis dimension (for backward compat).
    voxel_dims : tuple[float, float, float]
        Per-axis voxel dimensions ``(dx, dy, dz)`` in metres.  Equal to
        ``(voxel_size, voxel_size, voxel_size)`` for cubic grids.
    """

    def __init__(
        self,
        counts: dict[tuple[int, int, int], int],
        veg: dict[tuple[int, int, int], int],
        origin: NDArray[np.float64],
        voxel_size: float,
        voxel_dims: tuple[float, float, float] | None = None,
    ) -> None:
        self.counts = counts
        self.veg = veg
        self.origin = origin
        self.voxel_dims: tuple[float, float, float] = (
            voxel_dims if voxel_dims is not None else (voxel_size, voxel_size, voxel_size)
        )
        self.voxel_size = self.voxel_dims[0]

    def occupancy(self, key: tuple[int, int, int]) -> float:
        total = self.counts.get(key, 0)
        if total == 0:
            return 0.0
        return self.veg.get(key, 0) / total

    def world_coord(self, key: tuple[int, int, int]) -> NDArray[np.float64]:
        i, j, k = key
        dx, dy, dz = self.voxel_dims
        return self.origin + np.array([(i + 0.5) * dx, (j + 0.5) * dy, (k + 0.5) * dz])


def voxelize(
    points: NDArray[np.float64],
    voxel_size: float = 2.0,
    origin: NDArray[np.float64] | None = None,
    veg_mask: NDArray[np.bool_] | None = None,
    voxel_dims: tuple[float, float, float] | None = None,
) -> VoxelGrid:
    """Convert an (N, 3) point array into a sparse voxel grid.

    Parameters
    ----------
    points:
        (N, 3) array of [x, y, z] coordinates (height-normalised).
    voxel_size:
        Edge length of each cubic voxel in metres.  Ignored when
        *voxel_dims* is provided.
    origin:
        Optional explicit grid origin (3,).  Defaults to ``points.min(axis=0)``.
    veg_mask:
        Boolean array of length N.  True marks vegetation returns.
        If *None*, all points are treated as vegetation.
    voxel_dims:
        Optional ``(dx, dy, dz)`` for non-cubic voxels.  When set, overrides
        *voxel_size*.
    """
    if voxel_dims is not None:
        dims = voxel_dims
    else:
        dims = (voxel_size, voxel_size, voxel_size)

    grid_origin: NDArray[np.float64] = points.min(axis=0) if origin is None else origin

    dx, dy, dz = dims
    ix = np.floor((points[:, 0] - grid_origin[0]) / dx).astype(np.int64)
    iy = np.floor((points[:, 1] - grid_origin[1]) / dy).astype(np.int64)
    iz = np.floor((points[:, 2] - grid_origin[2]) / dz).astype(np.int64)
    indices = np.column_stack([ix, iy, iz])

    counts: dict[tuple[int, int, int], int] = defaultdict(int)
    veg: dict[tuple[int, int, int], int] = defaultdict(int)

    if veg_mask is None:
        veg_mask = np.ones(len(points), dtype=bool)

    for row_idx in range(len(indices)):
        key = (int(indices[row_idx, 0]), int(indices[row_idx, 1]), int(indices[row_idx, 2]))
        counts[key] += 1
        if veg_mask[row_idx]:
            veg[key] += 1

    return VoxelGrid(dict(counts), dict(veg), grid_origin.copy(), voxel_size=dims[0], voxel_dims=dims)
