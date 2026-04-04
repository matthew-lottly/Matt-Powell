"""Vertical gap fraction computation."""

from __future__ import annotations

from collections import defaultdict

from .voxelizer import VoxelGrid


def vertical_gap_fraction(
    grid: VoxelGrid,
    tau: float = 0.2,
) -> dict[tuple[int, int, int], float]:
        """Compute per-height vertical gap fraction for each voxel.

        For voxel (i, j, k), VGF is the fraction of voxels at heights k' > k in
        the same column (i, j) whose occupancy is below *tau* (apparent sky gaps
        when looking upward).  At the topmost occupied voxel of a column VGF = 1.0
        because there are no voxels above to block the sky.

        Returns a dict mapping voxel key -> VGF value in [0, 1].
        """
        col_ks: dict[tuple[int, int], list[int]] = defaultdict(list)
        col_empty: dict[tuple[int, int], set[int]] = defaultdict(set)

        for key in grid.counts:
            i, j, k = key
            col_ks[(i, j)].append(k)
            if grid.occupancy(key) < tau:
                col_empty[(i, j)].add(k)

        vgf: dict[tuple[int, int, int], float] = {}
        for key in grid.counts:
            i, j, k = key
            ks_above = [k2 for k2 in col_ks[(i, j)] if k2 > k]
            if not ks_above:
                vgf[key] = 1.0
            else:
                empty_above = sum(1 for k2 in ks_above if k2 in col_empty[(i, j)])
                vgf[key] = empty_above / len(ks_above)

        return vgf
