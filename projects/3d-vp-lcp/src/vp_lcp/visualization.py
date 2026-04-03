"""Visualization helpers for voxel corridors."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from .voxelizer import VoxelGrid


def corridor_to_points(
    path: list[tuple[int, int, int]],
    grid: VoxelGrid,
) -> NDArray[np.float64]:
    """Convert a voxel-key path into an (N, 3) array of world coordinates."""
    pts = np.array([grid.world_coord(k) for k in path])
    return pts


def resistance_to_2d(
    resistance: dict[tuple[int, int, int], float],
    grid: VoxelGrid,
) -> NDArray[np.float64]:
    """Project 3-D resistance to a 2-D minimum-cost surface.

    For each (i, j) column, the exported value is the minimum resistance
    across all height levels.
    """
    cols: dict[tuple[int, int], float] = {}
    for (i, j, _k), r in resistance.items():
        prev = cols.get((i, j))
        if prev is None or r < prev:
            cols[(i, j)] = r

    if not cols:
        return np.empty((0, 0))

    ij = np.array(list(cols.keys()))
    i_max = int(ij[:, 0].max()) + 1
    j_max = int(ij[:, 1].max()) + 1
    surface = np.full((i_max, j_max), np.nan)
    for (i, j), r in cols.items():
        surface[i, j] = r
    return surface


def plot_2d_surface(surface: NDArray[np.float64], out_path: str | None = None) -> None:
    """Render a 2-D cost surface with Matplotlib."""
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(surface.T, origin="lower", cmap="viridis_r")
    fig.colorbar(im, ax=ax, label="Minimum resistance")
    ax.set_xlabel("X voxel index")
    ax.set_ylabel("Y voxel index")
    ax.set_title("2-D Cost Surface (min across height)")
    if out_path:
        fig.savefig(out_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
    else:
        plt.show()
