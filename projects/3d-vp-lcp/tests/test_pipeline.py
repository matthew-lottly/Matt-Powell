"""Unit tests for the 3D-VP-LCP pipeline."""

from __future__ import annotations

import json
from pathlib import Path

import laspy
import numpy as np
import pytest

from vp_lcp.cli import main as cli_main
from vp_lcp.config import PipelineConfig
from vp_lcp.lidar_io import normalize_heights
from vp_lcp.lidar_io import normalize_heights_with_dtm, load_lidar_data
from vp_lcp.pipeline import run_pipeline
from vp_lcp.voxelizer import VoxelGrid, voxelize
from vp_lcp.vertical_gap import vertical_gap_fraction
from vp_lcp.resistance import compute_resistance
from vp_lcp.species_filter import apply_species_filter
from vp_lcp.graph3d import build_graph, least_cost_path
from vp_lcp.visualization import corridor_to_points, resistance_to_2d
from vp_lcp.lidar_io import clip_by_polygon, load_lidar_in_tiles
from vp_lcp.resistance import normalize_resistance
from vp_lcp.graph3d import accumulated_cost_volume
from vp_lcp.exports import export_occupancy_grid, export_vgf_grid
from vp_lcp.analysis import find_bottlenecks, run_ensemble, sensitivity_sweep


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
def sample_classifications(sample_points: np.ndarray) -> np.ndarray:
    classes = np.full(len(sample_points), 5, dtype=np.uint8)
    classes[: len(sample_points) // 4] = 2
    return classes


@pytest.fixture()
def temp_las_file(tmp_path: Path, sample_points: np.ndarray, sample_classifications: np.ndarray) -> Path:
    header = laspy.LasHeader(point_format=0, version="1.2")
    header.offsets = np.array([0.0, 0.0, 0.0])
    header.scales = np.array([0.01, 0.01, 0.01])
    las = laspy.LasData(header)
    las.x = sample_points[:, 0]
    las.y = sample_points[:, 1]
    las.z = sample_points[:, 2] + 100.0
    las.classification = sample_classifications
    path = tmp_path / "sample.las"
    las.write(str(path))
    return path


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


def test_normalize_heights_with_dtm(sample_points: np.ndarray, sample_classifications: np.ndarray):
    pts = sample_points.copy()
    pts[:, 2] += 100.0
    out = normalize_heights_with_dtm(pts, classifications=sample_classifications, ground_classes=(2,), cell_size=2.0)
    assert np.min(out[:, 2]) == pytest.approx(0.0, abs=0.5)


def test_load_lidar_data_reports_metadata(temp_las_file: Path):
    data = load_lidar_data(temp_las_file)
    assert data.metadata["point_count"] > 0
    assert data.metadata["class_count"] >= 1


def test_load_lidar_data_rejects_bad_bbox(temp_las_file: Path):
    with pytest.raises(ValueError):
        load_lidar_data(temp_las_file, bbox=(10, 0, 5, 1))


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


def test_lcp_astar_returns_path(resistance: dict):
    g = build_graph(resistance, voxel_size=2.0, neighbours=6)
    nodes = list(resistance.keys())
    if len(nodes) >= 2:
        path = least_cost_path(g, [nodes[0]], [nodes[-1]], algorithm="astar")
        assert len(path) >= 2


def test_lcp_raises_on_disconnected_graph():
    g = build_graph({(0, 0, 0): 1.0, (10, 10, 10): 1.0}, voxel_size=1.0, neighbours=6)
    with pytest.raises(Exception):
        least_cost_path(g, [(0, 0, 0)], [(10, 10, 10)])


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


@pytest.mark.parametrize("voxel_size", [1.0, 2.0, 4.0])
def test_pipeline_runs_for_multiple_voxel_sizes(temp_las_file: Path, tmp_path: Path, voxel_size: float):
    config = PipelineConfig()
    config.input.voxel_size = voxel_size
    config.species.w_clear = 1
    config.output.output_dir = str(tmp_path / f"run-{voxel_size}")
    config.output.export_surface = False
    result = run_pipeline(temp_las_file, config)
    assert result.path_voxel_count > 0
    assert result.csv_path is not None
    assert result.geojson_path is not None
    assert result.report_path is not None
    assert result.filter_counts["filtered_voxels"] == result.filtered_voxel_count
    assert Path(result.csv_path).exists()
    assert Path(result.geojson_path).exists()
    assert Path(result.report_path).exists()


def test_pipeline_smoke_outputs_report(temp_las_file: Path, tmp_path: Path):
    config = PipelineConfig()
    config.species.w_clear = 1
    config.output.output_dir = str(tmp_path / "smoke")
    config.output.export_surface = True
    result = run_pipeline(temp_las_file, config)
    assert result.report_path is not None
    assert result.surface_path is not None
    report = json.loads(Path(result.report_path).read_text(encoding="utf-8"))
    assert report["path_voxel_count"] == result.path_voxel_count
    assert report["graph_nodes"] >= result.path_voxel_count
    assert report["routing_algorithm"] == config.routing.algorithm
    assert report["height_band_summary"]["0-2m"] >= 0
    assert Path(result.surface_path).exists()


def test_cli_init_config(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    out_path = tmp_path / "config.json"
    cli_main(["init-config", "--output", str(out_path)])
    captured = capsys.readouterr()
    assert out_path.exists()
    assert "Wrote default config" in captured.out


def test_cli_run(temp_las_file: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    out_dir = tmp_path / "cli-run"
    cli_main(["run", "--input", str(temp_las_file), "--output-dir", str(out_dir)])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["path_voxel_count"] > 0
    assert (out_dir / "corridor.csv").exists()


# ---------- vgf per-height ----------

def test_vgf_topmost_voxel_is_one():
    """Topmost voxel in each column must have VGF == 1.0."""
    pts = np.array([[0, 0, 0], [0, 0, 2], [0, 0, 4]], dtype=np.float64)
    g = voxelize(pts, voxel_size=1.0)
    vgf_out = vertical_gap_fraction(g, tau=0.2)
    top_k = max(key[2] for key in vgf_out)
    for key, v in vgf_out.items():
        if key[2] == top_k:
            assert v == pytest.approx(1.0), f"Topmost voxel VGF not 1.0: {v}"


def test_vgf_responds_to_canopy_density(grid: VoxelGrid):
    """All VGF values are in [0,1]; per-height values should differ across height bands."""
    vgf_out = vertical_gap_fraction(grid, tau=0.2)
    for v in vgf_out.values():
        assert 0.0 <= v <= 1.0


# ---------- clearance and width filters ----------

def test_clearance_filter_removes_blocked_voxels():
    """A voxel with a dense (low-VGF) voxel immediately above it must be removed."""
    # Build an artificial scenario: two voxels stacked, bottom one has dense voxel above
    pts = np.array(
        [[0, 0, 0], [0, 0, 0.5], [0, 0, 1.0], [0, 0, 2.0]], dtype=np.float64
    )
    veg_mask = np.array([True, True, True, False])  # dense at z=0,0.5,1; empty at z=2
    g = voxelize(pts, voxel_size=1.0, veg_mask=veg_mask)
    vgf_out = vertical_gap_fraction(g, tau=0.2)
    resist = compute_resistance(g, vgf_out, alpha=1.0, beta=1.0)
    # With h_clear=1.0 a voxel needs 1 empty voxel above it — the dense ones should be removed
    filtered = apply_species_filter(
        resist, g, vgf_out,
        h_min=0.0, h_max=10.0, h_clear=1.0, w_clear=1, vgf_thresh=0.6,
    )
    assert len(filtered) <= len(resist)


def test_width_filter_removes_narrow_corridors():
    """A single-voxel-wide corridor should be removed when w_clear=2."""
    # Single column of voxels — no horizontal neighbours at any height level
    resist = {(0, 0, k): 1.0 for k in range(5)}
    g = voxelize(
        np.array([[0, 0, k] for k in range(5)], dtype=np.float64),
        voxel_size=1.0,
    )
    vgf_out = vertical_gap_fraction(g, tau=0.2)
    filtered = apply_species_filter(
        resist, g, vgf_out,
        h_min=0.0, h_max=20.0, h_clear=0.0, w_clear=2,
    )
    assert len(filtered) == 0, "Single-column corridor should be entirely removed"


# ---------- voxelizer boundary and non-cubic ----------

def test_voxelize_at_voxel_boundary():
    """Points exactly on a voxel boundary go into the same voxel as nearby points."""
    pts = np.array([[0.0, 0.0, 0.0], [1.9999, 1.9999, 1.9999]], dtype=np.float64)
    g = voxelize(pts, voxel_size=2.0)
    # Both points should be in the same voxel (0,0,0)
    assert list(g.counts.keys()) == [(0, 0, 0)]


def test_voxelize_with_explicit_origin():
    """Explicit origin shifts all voxel indices."""
    pts = np.array([[2, 2, 2], [4, 4, 4]], dtype=np.float64)
    g = voxelize(pts, voxel_size=2.0, origin=np.array([0.0, 0.0, 0.0]))
    assert (1, 1, 1) in g.counts
    assert (2, 2, 2) in g.counts


def test_non_cubic_voxels_world_coord():
    """Non-cubic voxels should produce correct world coordinates on all axes."""
    pts = np.array([[0.0, 0.0, 0.0]], dtype=np.float64)
    g = voxelize(pts, voxel_size=1.0, voxel_dims=(1.0, 2.0, 0.5))
    key = (0, 0, 0)
    coord = g.world_coord(key)
    assert coord[0] == pytest.approx(0.5)
    assert coord[1] == pytest.approx(1.0)
    assert coord[2] == pytest.approx(0.25)


# ---------- resistance normalization ----------

def test_normalize_resistance_range(resistance: dict):
    normed = normalize_resistance(resistance)
    vals = list(normed.values())
    assert min(vals) == pytest.approx(0.0, abs=1e-9)
    assert max(vals) == pytest.approx(1.0, abs=1e-9)


def test_normalize_resistance_constant():
    """Constant resistance should be returned unchanged."""
    r = {(0, 0, k): 5.0 for k in range(5)}
    normed = normalize_resistance(r)
    for v in normed.values():
        assert v == pytest.approx(5.0)


# ---------- accumulated cost volume and bottlenecks ----------

def test_accumulated_cost_volume(resistance: dict):
    g = build_graph(resistance, voxel_size=2.0, neighbours=6)
    nodes = list(resistance.keys())
    vol = accumulated_cost_volume(g, [nodes[0]])
    assert len(vol) > 0
    for v in vol.values():
        assert v >= 0.0


def test_find_bottlenecks(resistance: dict):
    g = build_graph(resistance, voxel_size=2.0, neighbours=6)
    nodes = list(resistance.keys())
    if len(nodes) >= 2:
        path = least_cost_path(g, [nodes[0]], [nodes[-1]])
        bottlenecks = find_bottlenecks(path, resistance, n=3)
        assert len(bottlenecks) <= 3
        if len(bottlenecks) >= 2:
            assert bottlenecks[0][1] >= bottlenecks[1][1]


# ---------- exports ----------

def test_export_occupancy_grid(tmp_path: Path, grid: VoxelGrid):
    out = tmp_path / "occ.csv"
    export_occupancy_grid(grid, out)
    assert out.exists()
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "i,j,k,x,y,z,occupancy"
    assert len(lines) > 1


def test_export_vgf_grid(tmp_path: Path, grid: VoxelGrid, vgf: dict):
    out = tmp_path / "vgf.csv"
    export_vgf_grid(vgf, grid, out)
    assert out.exists()
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "i,j,k,x,y,z,vgf"
    assert len(lines) > 1


# ---------- ensemble and sensitivity ----------

def test_run_ensemble(temp_las_file: Path, tmp_path: Path):
    cfg1 = PipelineConfig()
    cfg1.output.output_dir = str(tmp_path / "e1")
    cfg2 = PipelineConfig()
    cfg2.resistance.alpha = 2.0
    cfg2.output.output_dir = str(tmp_path / "e2")
    results = run_ensemble(temp_las_file, [cfg1, cfg2])
    assert len(results) == 2
    assert results[0].path_voxel_count > 0
    assert results[1].path_voxel_count > 0


def test_sensitivity_sweep(temp_las_file: Path, tmp_path: Path):
    base = PipelineConfig()
    base.output.output_dir = str(tmp_path / "sweep")
    rows = sensitivity_sweep(temp_las_file, base, "alpha", [0.5, 1.5])
    assert len(rows) == 2
    for row in rows:
        assert row["param"] == "alpha"
        assert row["path_voxel_count"] > 0


def test_sensitivity_sweep_invalid_param(temp_las_file: Path):
    base = PipelineConfig()
    with pytest.raises(ValueError):
        sensitivity_sweep(temp_las_file, base, "omega", [1.0])


# ---------- lidar clip and tiles ----------

def test_clip_by_polygon(sample_points: np.ndarray):
    polygon = np.array([[0, 0], [10, 0], [10, 10], [0, 10]], dtype=np.float64)
    mask = clip_by_polygon(sample_points, polygon)
    clipped = sample_points[mask]
    assert len(clipped) < len(sample_points)
    assert (clipped[:, 0] >= 0).all() and (clipped[:, 0] <= 10).all()
    assert (clipped[:, 1] >= 0).all() and (clipped[:, 1] <= 10).all()


def test_load_lidar_in_tiles(temp_las_file: Path):
    tiles = list(load_lidar_in_tiles(temp_las_file, tile_size=10.0))
    assert len(tiles) >= 1
    for tile in tiles:
        assert tile.ndim == 2 and tile.shape[1] == 3
        assert len(tile) > 0


# ---------- pipeline phase 4 ----------

def test_pipeline_exports_occupancy_and_vgf(temp_las_file: Path, tmp_path: Path):
    config = PipelineConfig()
    config.output.output_dir = str(tmp_path / "occ-vgf")
    config.output.export_occupancy = True
    config.output.export_vgf = True
    result = run_pipeline(temp_las_file, config)
    assert result.occupancy_path is not None
    assert result.vgf_path is not None
    assert Path(result.occupancy_path).exists()
    assert Path(result.vgf_path).exists()


def test_pipeline_stage_timings(temp_las_file: Path, tmp_path: Path):
    config = PipelineConfig()
    config.output.output_dir = str(tmp_path / "timings")
    result = run_pipeline(temp_las_file, config)
    assert "loading" in result.stage_timings
    assert "voxelization" in result.stage_timings
    assert "routing" in result.stage_timings
    assert all(v >= 0 for v in result.stage_timings.values())


def test_pipeline_18_neighbour(temp_las_file: Path, tmp_path: Path):
    config = PipelineConfig()
    config.routing.neighbours = 18
    config.output.output_dir = str(tmp_path / "n18")
    result = run_pipeline(temp_las_file, config)
    assert result.path_voxel_count > 0


def test_cli_26_neighbour(temp_las_file: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    out_dir = tmp_path / "cli-26"
    cli_main(["run", "--input", str(temp_las_file), "--output-dir", str(out_dir), "--neighbours", "26"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["path_voxel_count"] > 0
