"""Vertical gap fraction computation."""

from __future__ import annotations

from collections import defaultdict

from .voxelizer import VoxelGrid


def vertical_gap_fraction(
    grid: VoxelGrid,
    tau: float = 0.2,
) -> dict[tuple[int, int, int], float]:
    """Compute vertical gap fraction for every voxel in the grid.

    A voxel is considered *empty* when its occupancy (vegetation density) falls
    below *tau*.  VGF is the proportion of empty voxels in the same (x, y)
    column at each height level.

    Returns a dict mapping voxel key → VGF value in [0, 1].
    """
    col_total: dict[tuple[int, int], int] = defaultdict(int)
    col_empty: dict[tuple[int, int], int] = defaultdict(int)

    for key in grid.counts:
        i, j, _k = key
        col_total[(i, j)] += 1
        if grid.occupancy(key) < tau:
            col_empty[(i, j)] += 1

    vgf: dict[tuple[int, int, int], float] = {}
    for key in grid.counts:
        i, j, _k = key
        total = col_total[(i, j)]
        vgf[key] = col_empty[(i, j)] / total if total > 0 else 0.0

    return vgf
