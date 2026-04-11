"""Organism-specific morphology filtering."""

from __future__ import annotations

import numpy as np

from .voxelizer import VoxelGrid

_STRATUM_BANDS = [
    ("0-2m", 0.0, 2.0),
    ("2-5m", 2.0, 5.0),
    ("5-10m", 5.0, 10.0),
    ("10m+", 10.0, float("inf")),
]


def _stratum_weight(z_centre: float, stratum_weights: dict[str, float]) -> float:
    for label, lo, hi in _STRATUM_BANDS:
        if lo <= z_centre < hi:
            return stratum_weights.get(label, 1.0)
    return 1.0


def apply_species_filter(
    resistance: dict[tuple[int, int, int], float],
    grid: VoxelGrid,
    vgf: dict[tuple[int, int, int], float],
    h_min: float,
    h_max: float,
    h_clear: float = 2.0,
    w_clear: int = 2,
    vgf_thresh: float = 0.6,
    stratum_weights: dict[str, float] | None = None,
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
        least ``h_clear / voxel_size`` consecutive low-density voxels.
    w_clear:
        Minimum horizontal corridor width (in voxels).  Isolated voxels in a
        3-D connected component smaller than ``w_clear * w_clear`` are removed;
        an additional erosion step requires at least ``w_clear - 1`` horizontal
        neighbours at the same height level.
    vgf_thresh:
        VGF threshold above which a voxel is considered passable for the
        clearance check.
    stratum_weights:
        Optional dict mapping stratum labels (``"0-2m"``, ``"2-5m"``,
        ``"5-10m"``, ``"10m+"``) to resistance multipliers applied before
        filtering.  Values > 1.0 make that band harder to traverse.
    """
    vs = grid.voxel_size
    origin_z = float(grid.origin[2])

    # Step 1: height-band filter (with optional stratum weighting)
    filtered: dict[tuple[int, int, int], float] = {}
    for key, r in resistance.items():
        _i, _j, k = key
        z_centre = origin_z + (k + 0.5) * vs
        if h_min <= z_centre <= h_max:
            if stratum_weights is not None:
                r = r * _stratum_weight(z_centre, stratum_weights)
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

    # Step 3: flood-fill component filter (removes isolated small clusters)
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

    # Step 4: erosion pass — each voxel must have at least (w_clear - 1)
    # horizontal neighbours at the same height level (stronger local width check)
    if w_clear > 1:
        min_xy_neighbours = w_clear - 1
        remaining_keys = set(filtered)
        to_erode: list[tuple[int, int, int]] = []
        for key in list(filtered):
            i, j, k = key
            count = 0
            for di, dj in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                if (i + di, j + dj, k) in remaining_keys:
                    count += 1
            if count < min_xy_neighbours:
                to_erode.append(key)
        for key in to_erode:
            filtered.pop(key, None)

    return filtered
