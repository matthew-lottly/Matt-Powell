"""Resistance-surface computation from VGF and auxiliary layers."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from .voxelizer import VoxelGrid


def compute_resistance(
    grid: VoxelGrid,
    vgf: dict[tuple[int, int, int], float],
    alpha: float = 1.0,
    beta: float = 1.0,
    gamma: float = 0.0,
    delta: float = 0.0,
    slope_array: NDArray[np.float64] | None = None,
    landcover_array: NDArray[np.float64] | None = None,
) -> dict[tuple[int, int, int], float]:
    """Build a per-voxel resistance dictionary.

    R(i,j,k) = alpha * (1 - VGF) + beta * occupancy + gamma * slope + delta * landcover

    Parameters
    ----------
    grid:
        The sparse voxel grid.
    vgf:
        Vertical gap fraction per voxel.
    alpha, beta, gamma, delta:
        Weight coefficients for each resistance component.
    slope_array:
        Optional 2-D array indexed by (i, j) giving terrain slope values.
    landcover_array:
        Optional 2-D array indexed by (i, j) giving land-cover cost penalties.
    """
    resistance: dict[tuple[int, int, int], float] = {}

    for key, gap in vgf.items():
        i, j, _k = key
        occ = grid.occupancy(key)
        slope = float(slope_array[i, j]) if slope_array is not None else 0.0
        lc = float(landcover_array[i, j]) if landcover_array is not None else 0.0
        resistance[key] = alpha * (1.0 - gap) + beta * occ + gamma * slope + delta * lc

    return resistance
