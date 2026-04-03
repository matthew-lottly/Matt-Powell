"""Organism-specific morphology filtering."""

from __future__ import annotations

from collections import defaultdict

import numpy as np
from numpy.typing import NDArray

from .voxelizer import VoxelGrid


def apply_species_filter(
    resistance: dict[tuple[int, int, int], float],
    grid: VoxelGrid,
    vgf: dict[tuple[int, int, int], float],
    h_min: float,
    h_max: float,
    h_clear: float = 2.0,
    w_clear: int = 2,
    vgf_thresh: float = 0.6,
) -> dict[tuple[int, int, int], float]:
    """Filter voxels that do not satisfy height, clearance, and width criteria.

    Parameters
    ----------
    resistance:
        Per-voxel resistance values from :func:`compute_resistance`.
    grid:
        The sparse voxel grid (provides origin, voxel size, and counts).
    vgf:
        Vertical gap fraction per voxel.
    h_min, h_max:
        Usable height band above ground (metres).
    h_clear:
        Required vertical clearance (metres).  The voxel must sit beneath at
        least *h_clear / voxel_size* consecutive low-density voxels.
    w_clear:
        Minimum horizontal corridor width (in voxels).  Isolated voxels in a
        connected component smaller than w_clear × w_clear are removed.
    vgf_thresh:
        VGF threshold above which a voxel is considered passable for the
        clearance check.
    """
    vs = grid.voxel_size
    origin_z = float(grid.origin[2])

    # Step 1: height-band filter
    filtered: dict[tuple[int, int, int], float] = {}
    for key, r in resistance.items():
        _i, _j, k = key
        z_centre = origin_z + (k + 0.5) * vs
        if h_min <= z_centre <= h_max:
            filtered[key] = r

    # Step 2: vertical clearance filter
    n_clear = int(np.ceil(h_clear / vs))
    if n_clear > 0:
        to_remove: list[tuple[int, int, int]] = []
        for key in list(filtered):
            i, j, k = key
            passable = True
            for dk in range(1, n_clear + 1):
                above = (i, j, k + dk)
                if vgf.get(above, 0.0) < vgf_thresh:
                    passable = False
                    break
            if not passable:
                to_remove.append(key)
        for key in to_remove:
            del filtered[key]

    # Step 3: horizontal width filter (flood-fill connected components)
    if w_clear > 1:
        min_component = w_clear * w_clear
        remaining = set(filtered)
        visited: set[tuple[int, int, int]] = set()
        to_remove_w: list[tuple[int, int, int]] = []

        for seed in list(remaining):
            if seed in visited:
                continue
            component: list[tuple[int, int, int]] = []
            stack = [seed]
            while stack:
                node = stack.pop()
                if node in visited or node not in remaining:
                    continue
                visited.add(node)
                component.append(node)
                ni, nj, nk = node
                for di, dj in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    neighbour = (ni + di, nj + dj, nk)
                    if neighbour in remaining and neighbour not in visited:
                        stack.append(neighbour)
            if len(component) < min_component:
                to_remove_w.extend(component)

        for key in to_remove_w:
            filtered.pop(key, None)

    return filtered
