"""Unit tests for the 3D-VP-LCP pipeline."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from vp_lcp.lidar_io import normalize_heights
from vp_lcp.voxelizer import VoxelGrid, voxelize
from vp_lcp.vertical_gap import vertical_gap_fraction
from vp_lcp.resistance import compute_resistance
from vp_lcp.species_filter import apply_species_filter
from vp_lcp.graph3d import build_graph, least_cost_path
from vp_lcp.visualization import corridor_to_points, resistance_to_2d


# ---------- fixtures ----------

@pytest.fixture()
def sample_points() -> np.ndarray:
    """Small deterministic point cloud: ground + understory + canopy."""
    rng = np.random.default_rng(0)
    n = 200
    x = rng.uniform(0, 20, n)
    y = rng.uniform(0, 20, n)
    z = np.concatenate([
        rng.uniform(0, 0.5, n // 4),        # ground
        rng.uniform(2, 6, n // 4),           # understory
        rng.uniform(8, 15, n // 4),          # canopy
        rng.uniform(0, 15, n - 3 * (n // 4)),  # mixed
    ])
    return np.column_stack([x, y, z])


@pytest.fixture()
def grid(sample_points: np.ndarray) -> VoxelGrid:
    return voxelize(sample_points, voxel_size=2.0)


@pytest.fixture()
def vgf(grid: VoxelGrid) -> dict:
    return vertical_gap_fraction(grid, tau=0.2)


@pytest.fixture()
def resistance(grid: VoxelGrid, vgf: dict) -> dict:
    return compute_resistance(grid, vgf, alpha=1.0, beta=1.0)


# ---------- lidar_io ----------

def test_normalize_heights_shifts_z():
    pts = np.array([[0, 0, 100], [1, 1, 105], [2, 2, 102]], dtype=np.float64)
    out = normalize_heights(pts, ground_percentile=0)
    assert out[:, 2].min() == pytest.approx(0.0, abs=0.01)


# ---------- voxelizer ----------

def test_voxelize_creates_occupied_voxels(grid: VoxelGrid):
    assert len(grid.counts) > 0


def test_occupancy_range(grid: VoxelGrid):
    for key in grid.counts:
        occ = grid.occupancy(key)
        assert 0.0 <= occ <= 1.0


def test_world_coord_roundtrip(grid: VoxelGrid):
    key = next(iter(grid.counts))
    coord = grid.world_coord(key)
    assert coord.shape == (3,)
    # rebuilding the index from the coordinate should give us back the same key
    idx = tuple(np.floor((coord - grid.origin) / grid.voxel_size).astype(int))
    assert idx == key


# ---------- vertical gap ----------

def test_vgf_range(vgf: dict):
    for v in vgf.values():
        assert 0.0 <= v <= 1.0


# ---------- resistance ----------

def test_resistance_positive(resistance: dict):
    for r in resistance.values():
        assert r >= 0.0


def test_resistance_keys_match_vgf(vgf: dict, resistance: dict):
    assert set(resistance.keys()) == set(vgf.keys())


# ---------- species filter ----------

def test_species_filter_reduces_voxels(resistance: dict, grid: VoxelGrid, vgf: dict):
    filtered = apply_species_filter(
        resistance, grid, vgf,
        h_min=2.0, h_max=8.0, h_clear=1.0, w_clear=1,
    )
    assert len(filtered) <= len(resistance)


# ---------- graph ----------

def test_build_graph_nodes_match(resistance: dict):
    g = build_graph(resistance, voxel_size=2.0, neighbours=6)
    assert g.number_of_nodes() == len(resistance)


def test_lcp_returns_path(resistance: dict):
    g = build_graph(resistance, voxel_size=2.0, neighbours=6)
    nodes = list(resistance.keys())
    if len(nodes) >= 2:
        path = least_cost_path(g, [nodes[0]], [nodes[-1]])
        assert len(path) >= 2
        assert path[0] == nodes[0]
        assert path[-1] == nodes[-1]


# ---------- visualization helpers ----------

def test_corridor_to_points(grid: VoxelGrid, resistance: dict):
    keys = list(resistance.keys())[:5]
    pts = corridor_to_points(keys, grid)
    assert pts.shape == (len(keys), 3)


def test_resistance_to_2d(grid: VoxelGrid, resistance: dict):
    surface = resistance_to_2d(resistance, grid)
    assert surface.ndim == 2
    # at least one finite value
    assert np.any(np.isfinite(surface))
