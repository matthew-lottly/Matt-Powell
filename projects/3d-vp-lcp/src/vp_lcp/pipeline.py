"""High-level pipeline execution for 3D-VP-LCP."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from time import perf_counter

import networkx as nx
import numpy as np

from .config import PipelineConfig
from .exports import (
    export_corridor_csv,
    export_corridor_geojson,
    export_occupancy_grid,
    export_run_report,
    export_vgf_grid,
)
from .graph3d import VoxelKey, accumulated_cost_volume, build_graph, least_cost_path
from .lidar_io import (
    LidarData,
    clip_by_polygon,
    load_lidar_data,
    normalize_heights,
    normalize_heights_with_dtm,
)
from .resistance import compute_resistance, normalize_resistance
from .species_filter import apply_species_filter
from .vertical_gap import vertical_gap_fraction
from .visualization import plot_2d_surface, resistance_to_2d
from .voxelizer import VoxelGrid, voxelize


@dataclass(slots=True)
class PipelineResult:
    lidar_path: str
    metadata: dict
    voxel_count: int
    filtered_voxel_count: int
    graph_nodes: int
    graph_edges: int
    path_voxel_count: int
    path_cost: float
    mean_corridor_height: float | None
    runtime_seconds: float
    output_dir: str
    routing_algorithm: str
    filter_counts: dict[str, int]
    height_band_summary: dict[str, int]
    stage_timings: dict[str, float] = field(default_factory=dict)
    csv_path: str | None = None
    geojson_path: str | None = None
    report_path: str | None = None
    surface_path: str | None = None
    occupancy_path: str | None = None
    vgf_path: str | None = None
    cost_volume_path: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _select_patch_nodes(
    graph: nx.Graph,
    source_margin: int,
    target_margin: int,
) -> tuple[list[VoxelKey], list[VoxelKey]]:
    voxel_nodes = [node for node in graph.nodes if isinstance(node, tuple) and len(node) == 3]
    if not voxel_nodes:
        raise ValueError("No passable voxels remain after species filtering.")

    components = [list(component) for component in nx.connected_components(graph)]
    voxel_components = [
        [node for node in component if isinstance(node, tuple) and len(node) == 3]
        for component in components
    ]
    voxel_components = [component for component in voxel_components if component]
    if not voxel_components:
        raise ValueError("No connected voxel components are available for routing.")

    def component_score(component: list[VoxelKey]) -> tuple[int, int, int]:
        xs = [node[0] for node in component]
        ys = [node[1] for node in component]
        return (max(max(xs) - min(xs), max(ys) - min(ys)), len(component), max(xs) - min(xs))

    chosen = max(voxel_components, key=component_score)
    xs = [key[0] for key in chosen]
    ys = [key[1] for key in chosen]
    x_span = max(xs) - min(xs)
    y_span = max(ys) - min(ys)
    axis = 0 if x_span >= y_span else 1

    axis_vals = [key[axis] for key in chosen]
    min_val = min(axis_vals)
    max_val = max(axis_vals)
    source_nodes = [key for key in chosen if key[axis] <= min_val + source_margin]
    target_nodes = [key for key in chosen if key[axis] >= max_val - target_margin]

    if not source_nodes or not target_nodes:
        min_key = min(chosen, key=lambda key: key[axis])
        max_key = max(chosen, key=lambda key: key[axis])
        if min_key == max_key and len(chosen) > 1:
            min_key = chosen[0]
            max_key = max(
                chosen,
                key=lambda key: abs(key[0] - min_key[0]) + abs(key[1] - min_key[1]) + abs(key[2] - min_key[2]),
            )
        source_nodes = [min_key]
        target_nodes = [max_key]

    return source_nodes, target_nodes


def _path_cost(path: list[VoxelKey], resistance: dict[VoxelKey, float]) -> float:
    if not path:
        return 0.0
    return float(sum(resistance[key] for key in path))


def _mean_corridor_height(path: list[VoxelKey], grid: VoxelGrid) -> float | None:
    if not path:
        return None
    heights = [float(grid.world_coord(key)[2]) for key in path]
    return float(np.mean(heights))


def _summarize_height_bands(grid: VoxelGrid) -> dict[str, int]:
    bands = {"0-2m": 0, "2-5m": 0, "5-10m": 0, "10m+": 0}
    for key in grid.counts:
        z_val = float(grid.world_coord(key)[2])
        if z_val < 2.0:
            bands["0-2m"] += 1
        elif z_val < 5.0:
            bands["2-5m"] += 1
        elif z_val < 10.0:
            bands["5-10m"] += 1
        else:
            bands["10m+"] += 1
    return bands


def run_pipeline(lidar_path: str | Path, config: PipelineConfig) -> PipelineResult:
    """Execute the full 3D-VP-LCP pipeline from a LAS/LAZ file to corridor artifacts."""
    timings: dict[str, float] = {}
    start = perf_counter()
    lidar_path = str(lidar_path)
    output_dir = Path(config.output.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # --- Loading ---
    t0 = perf_counter()
    data: LidarData = load_lidar_data(lidar_path, bbox=config.input.bbox)
    if data.points.size == 0:
        raise ValueError("Input point cloud is empty after loading and clipping.")
    timings["loading"] = perf_counter() - t0

    # Optional polygon clip
    points = data.points
    if config.input.polygon_clip_path is not None:
        import json as _json
        poly_raw = _json.loads(Path(config.input.polygon_clip_path).read_text(encoding="utf-8"))
        poly_coords = np.asarray(poly_raw if isinstance(poly_raw, list) else poly_raw["coordinates"])
        mask = clip_by_polygon(points, poly_coords)
        points = points[mask]
        data = LidarData(points=points, classifications=data.classifications[mask], metadata=data.metadata)

    # --- Normalization ---
    t0 = perf_counter()
    if config.input.normalization == "dtm-grid":
        points = normalize_heights_with_dtm(
            data.points,
            classifications=data.classifications,
            ground_classes=config.input.ground_classes,
            cell_size=config.input.dtm_cell_size,
        )
    else:
        points = normalize_heights(data.points, ground_percentile=config.input.ground_percentile)
    timings["normalization"] = perf_counter() - t0

    keep_mask = points[:, 2] >= config.input.min_height
    points = points[keep_mask]
    classifications = data.classifications[keep_mask]
    vegetation_mask = np.isin(classifications, np.asarray(config.input.vegetation_classes))

    if len(points) == 0:
        raise ValueError("No above-ground points remain after normalization and height filtering.")

    # Load optional external raster arrays (must be pre-aligned to voxel grid space as .npy)
    slope_array = None
    landcover_array = None
    if config.input.slope_raster_path is not None:
        slope_array = np.load(config.input.slope_raster_path)
    if config.input.landcover_raster_path is not None:
        landcover_array = np.load(config.input.landcover_raster_path)

    # --- Voxelization ---
    t0 = perf_counter()
    grid = voxelize(points, voxel_size=config.input.voxel_size, veg_mask=vegetation_mask)
    timings["voxelization"] = perf_counter() - t0

    # --- VGF ---
    t0 = perf_counter()
    vgf = vertical_gap_fraction(grid, tau=0.2)
    timings["vgf"] = perf_counter() - t0

    # --- Resistance ---
    t0 = perf_counter()
    resistance = compute_resistance(
        grid,
        vgf,
        alpha=config.resistance.alpha,
        beta=config.resistance.beta,
        gamma=config.resistance.gamma,
        delta=config.resistance.delta,
        slope_array=slope_array,
        landcover_array=landcover_array,
    )
    if config.resistance.normalize:
        resistance = normalize_resistance(resistance)
    timings["resistance"] = perf_counter() - t0

    # --- Species filter ---
    t0 = perf_counter()
    filtered = apply_species_filter(
        resistance,
        grid,
        vgf,
        h_min=config.species.h_min,
        h_max=config.species.h_max,
        h_clear=config.species.h_clear,
        w_clear=config.species.w_clear,
        vgf_thresh=config.species.vgf_thresh,
        stratum_weights=config.species.stratum_weights,
    )
    timings["species_filter"] = perf_counter() - t0

    filter_counts = {
        "loaded_points": int(data.metadata.get("point_count", 0)),
        "above_ground_points": int(len(points)),
        "occupied_voxels": len(grid.counts),
        "resistance_voxels": len(resistance),
        "filtered_voxels": len(filtered),
    }

    # --- Graph construction ---
    t0 = perf_counter()
    graph = build_graph(filtered, voxel_size=grid.voxel_size, neighbours=config.routing.neighbours)
    timings["graph"] = perf_counter() - t0

    source_nodes, target_nodes = _select_patch_nodes(
        graph,
        config.routing.source_margin,
        config.routing.target_margin,
    )

    # --- Routing ---
    t0 = perf_counter()
    try:
        path = least_cost_path(
            graph,
            source_nodes,
            target_nodes,
            algorithm=config.routing.algorithm,
        )
    except nx.NetworkXNoPath as exc:
        raise ValueError("No least-cost path could be found between source and target patches.") from exc
    timings["routing"] = perf_counter() - t0

    if not path:
        raise ValueError("No least-cost path could be found between source and target patches.")

    # --- Exports ---
    csv_path = None
    geojson_path = None
    report_path = None
    surface_path = None
    occupancy_path = None
    vgf_path = None
    cost_volume_path = None

    if config.output.export_csv:
        csv_path = str(export_corridor_csv(path, grid, output_dir / "corridor.csv"))
    if config.output.export_geojson:
        geojson_path = str(export_corridor_geojson(path, grid, output_dir / "corridor.geojson"))
    if config.output.export_surface:
        surface = resistance_to_2d(filtered, grid)
        surface_path = str(output_dir / "cost_surface.png")
        plot_2d_surface(surface, out_path=surface_path)
    if config.output.export_occupancy:
        occupancy_path = str(export_occupancy_grid(grid, output_dir / "occupancy_grid.csv"))
    if config.output.export_vgf:
        vgf_path = str(export_vgf_grid(vgf, grid, output_dir / "vgf_grid.csv"))
    if config.output.export_cost_volume:
        cost_vol = accumulated_cost_volume(graph, source_nodes)
        # Serialise as JSON: list of [[i,j,k], cost] pairs
        import json as _json
        cv_path = output_dir / "cost_volume.json"
        payload = [[list(k), v] for k, v in cost_vol.items()]
        cv_path.write_text(_json.dumps(payload), encoding="utf-8")
        cost_volume_path = str(cv_path)

    runtime_seconds = perf_counter() - start
    result = PipelineResult(
        lidar_path=lidar_path,
        metadata=data.metadata,
        voxel_count=len(grid.counts),
        filtered_voxel_count=len(filtered),
        graph_nodes=graph.number_of_nodes(),
        graph_edges=graph.number_of_edges(),
        path_voxel_count=len(path),
        path_cost=_path_cost(path, filtered),
        mean_corridor_height=_mean_corridor_height(path, grid),
        runtime_seconds=runtime_seconds,
        output_dir=str(output_dir),
        routing_algorithm=config.routing.algorithm,
        filter_counts=filter_counts,
        height_band_summary=_summarize_height_bands(grid),
        stage_timings=timings,
        csv_path=csv_path,
        geojson_path=geojson_path,
        report_path=None,
        surface_path=surface_path,
        occupancy_path=occupancy_path,
        vgf_path=vgf_path,
        cost_volume_path=cost_volume_path,
    )
    if config.output.export_report:
        report_path = str(export_run_report(result.to_dict(), output_dir / "run_report.json"))
        result.report_path = report_path
    return result
