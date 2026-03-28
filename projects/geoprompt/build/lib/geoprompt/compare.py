from __future__ import annotations

import argparse
import importlib
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .frame import GeoPromptFrame
from .geometry import geometry_bounds, geometry_centroid, transform_geometry
from .overlay import geometry_from_shapely, geometry_to_shapely
from .io import read_features, write_json


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_PATH = PROJECT_ROOT / "data" / "sample_features.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs"
DEFAULT_BENCHMARK_PATH = PROJECT_ROOT / "data" / "benchmark_features.json"
DEFAULT_JOIN_PATH = PROJECT_ROOT / "data" / "benchmark_regions.json"


@dataclass(frozen=True)
class CorpusCase:
    name: str
    feature_path: Path | None
    crs: str
    query_bounds: tuple[float, float, float, float]
    join_path: Path | None = None
    feature_records: list[dict[str, Any]] | None = None
    join_records: list[dict[str, Any]] | None = None


DEFAULT_CORPUS = [
    CorpusCase(
        name="sample",
        feature_path=DEFAULT_INPUT_PATH,
        crs="EPSG:4326",
        query_bounds=(-111.97, 40.68, -111.84, 40.79),
    ),
    CorpusCase(
        name="benchmark",
        feature_path=DEFAULT_BENCHMARK_PATH,
        crs="EPSG:4326",
        query_bounds=(-112.01, 40.64, -111.84, 40.8),
        join_path=DEFAULT_JOIN_PATH,
    ),
    CorpusCase(
        name="stress",
        feature_path=None,
        crs="EPSG:4326",
        query_bounds=(-111.97, 40.69, -111.87, 40.77),
        feature_records=[],
        join_records=[],
    ),
]


_DATASET_FIXTURE_CACHE: dict[tuple[Any, ...], dict[str, Any]] = {}


def _stress_feature_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    min_x = -112.0
    min_y = 40.64
    point_step_x = 0.02
    point_step_y = 0.02

    def coord(value: float) -> float:
        return round(value, 6)

    for row in range(8):
        for column in range(8):
            x_value = coord(min_x + (column * point_step_x))
            y_value = coord(min_y + (row * point_step_y))
            records.append(
                {
                    "site_id": f"stress-point-{row:02d}-{column:02d}",
                    "name": f"Stress Point {row:02d}-{column:02d}",
                    "geometry": {"type": "Point", "coordinates": [x_value, y_value]},
                    "demand_index": round(0.55 + (row * 0.03) + (column * 0.01), 3),
                    "capacity_index": round(0.65 + (column * 0.02), 3),
                    "priority_index": round(0.8 + (row * 0.025), 3),
                }
            )

    for row in range(6):
        y_value = coord(40.655 + (row * 0.025))
        records.append(
            {
                "site_id": f"stress-horizontal-line-{row:02d}",
                "name": f"Stress Horizontal Line {row:02d}",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [-112.01, y_value],
                        [-111.92, coord(y_value + 0.003)],
                        [-111.83, y_value],
                    ],
                },
                "demand_index": round(0.7 + (row * 0.02), 3),
                "capacity_index": round(0.82 + (row * 0.015), 3),
                "priority_index": round(0.9 + (row * 0.018), 3),
            }
        )

    for column in range(6):
        x_value = coord(-111.995 + (column * 0.03))
        records.append(
            {
                "site_id": f"stress-vertical-line-{column:02d}",
                "name": f"Stress Vertical Line {column:02d}",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [x_value, 40.63],
                        [coord(x_value + 0.003), 40.72],
                        [x_value, 40.81],
                    ],
                },
                "demand_index": round(0.68 + (column * 0.025), 3),
                "capacity_index": round(0.79 + (column * 0.018), 3),
                "priority_index": round(0.88 + (column * 0.02), 3),
            }
        )

    for row in range(4):
        for column in range(4):
            min_polygon_x = coord(-112.0 + (column * 0.04))
            min_polygon_y = coord(40.645 + (row * 0.04))
            max_polygon_x = coord(min_polygon_x + 0.028)
            max_polygon_y = coord(min_polygon_y + 0.028)
            records.append(
                {
                    "site_id": f"stress-polygon-{row:02d}-{column:02d}",
                    "name": f"Stress Polygon {row:02d}-{column:02d}",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[
                            [min_polygon_x, min_polygon_y],
                            [max_polygon_x, min_polygon_y],
                            [max_polygon_x, max_polygon_y],
                            [min_polygon_x, max_polygon_y],
                        ]],
                    },
                    "demand_index": round(0.74 + (row * 0.03) + (column * 0.015), 3),
                    "capacity_index": round(0.77 + (column * 0.02), 3),
                    "priority_index": round(0.93 + (row * 0.025), 3),
                }
            )

    records.append(
        {
            "site_id": "stress-remote-point",
            "name": "Stress Remote Point",
            "geometry": {"type": "Point", "coordinates": [-111.72, 40.86]},
            "demand_index": 0.5,
            "capacity_index": 0.62,
            "priority_index": 0.71,
        }
    )

    return records


def _stress_region_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    min_x = -112.02
    min_y = 40.62
    cell_width = 0.05
    cell_height = 0.05

    def coord(value: float) -> float:
        return round(value, 6)

    for row in range(4):
        for column in range(4):
            region_min_x = coord(min_x + (column * cell_width))
            region_min_y = coord(min_y + (row * cell_height))
            region_max_x = coord(region_min_x + cell_width)
            region_max_y = coord(region_min_y + cell_height)
            records.append(
                {
                    "region_id": f"stress-sector-{row:02d}-{column:02d}",
                    "region_name": f"Stress Sector {row:02d}-{column:02d}",
                    "region_band": "north" if row >= 2 else "south",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[
                            [region_min_x, region_min_y],
                            [region_max_x, region_min_y],
                            [region_max_x, region_max_y],
                            [region_min_x, region_max_y],
                        ]],
                    },
                }
            )

    return records


def _materialize_case(case: CorpusCase) -> CorpusCase:
    if case.name != "stress":
        return case
    return CorpusCase(
        name=case.name,
        feature_path=case.feature_path,
        crs=case.crs,
        query_bounds=case.query_bounds,
        join_path=case.join_path,
        feature_records=_stress_feature_records(),
        join_records=_stress_region_records(),
    )


def _frame_from_case(case: CorpusCase) -> GeoPromptFrame:
    if case.feature_records is not None:
        return GeoPromptFrame.from_records(case.feature_records, crs=case.crs)
    if case.feature_path is None:
        raise ValueError(f"case '{case.name}' is missing feature input")
    return read_features(case.feature_path, crs=case.crs)


def _path_cache_token(path: Path | None) -> tuple[str | None, int | None]:
    if path is None:
        return (None, None)
    resolved = path.resolve()
    try:
        return (str(resolved), resolved.stat().st_mtime_ns)
    except OSError:
        return (str(resolved), None)


def _dataset_fixture_key(case: CorpusCase) -> tuple[Any, ...]:
    feature_path, feature_mtime = _path_cache_token(case.feature_path)
    join_path, join_mtime = _path_cache_token(case.join_path)
    return (
        case.name,
        feature_path,
        feature_mtime,
        join_path,
        join_mtime,
        case.crs,
        case.query_bounds,
        bool(case.feature_records is not None),
        bool(case.join_records is not None),
    )


def _dataset_fixture(case: CorpusCase) -> dict[str, Any]:
    materialized_case = _materialize_case(case)
    cache_key = _dataset_fixture_key(materialized_case)
    cached = _DATASET_FIXTURE_CACHE.get(cache_key)
    if cached is not None:
        return cached

    geopandas, shape, box = _load_compare_dependencies()
    frame = _frame_from_case(materialized_case)
    records = frame.to_records()
    feature_ids = [str(record.get("site_id", index)) for index, record in enumerate(records)]
    shapely_geometries = [shape(_as_geojson_geometry(record["geometry"])) for record in records]
    geopandas_frame = geopandas.GeoDataFrame(
        [{key: value for key, value in record.items() if key != "geometry"} for record in records],
        geometry=shapely_geometries,
        crs=materialized_case.crs,
    )
    min_x, min_y, max_x, max_y = materialized_case.query_bounds
    spatial_index = frame.spatial_index()
    query_candidate_indexes = spatial_index.query((min_x, min_y, max_x, max_y))

    changed_records = [dict(record) for record in records]
    if changed_records:
        changed_records[0] = {
            **changed_records[0],
            "geometry": transform_geometry(changed_records[0]["geometry"], lambda coordinate: (coordinate[0] + 0.005, coordinate[1] + 0.002)),
        }
        if "demand_index" in changed_records[0]:
            changed_records[0]["demand_index"] = float(changed_records[0]["demand_index"]) + 0.1
    if len(changed_records) >= 3:
        changed_records.pop(1)
    if changed_records:
        added_record = dict(changed_records[-1])
        added_record["site_id"] = f"{added_record.get('site_id', 'site')}-added"
        added_record["geometry"] = transform_geometry(added_record["geometry"], lambda coordinate: (coordinate[0] + 0.02, coordinate[1] + 0.015))
        changed_records.append(added_record)
    changed_frame = GeoPromptFrame.from_records(changed_records, crs=materialized_case.crs)

    changed_variant_records = [dict(record) for record in records]
    if changed_variant_records:
        changed_variant_records[0] = {
            **changed_variant_records[0],
            "geometry": transform_geometry(changed_variant_records[0]["geometry"], lambda coordinate: (coordinate[0] - 0.004, coordinate[1] + 0.003)),
        }
        if "demand_index" in changed_variant_records[0]:
            changed_variant_records[0]["demand_index"] = float(changed_variant_records[0]["demand_index"]) + 0.2
    if len(changed_variant_records) >= 2:
        changed_variant_records.pop(-1)
    if changed_variant_records:
        variant_added_record = dict(changed_variant_records[0])
        variant_added_record["site_id"] = f"{variant_added_record.get('site_id', 'site')}-variant"
        variant_added_record["geometry"] = transform_geometry(variant_added_record["geometry"], lambda coordinate: (coordinate[0] + 0.03, coordinate[1] - 0.01))
        changed_variant_records.append(variant_added_record)
    changed_frame_variant = GeoPromptFrame.from_records(changed_variant_records, crs=materialized_case.crs)

    analysis_points = _analysis_point_frame(frame)
    analysis_point_records = analysis_points.to_records()
    analysis_queries = GeoPromptFrame.from_records(analysis_point_records[: min(5, len(analysis_point_records))], crs=materialized_case.crs)
    analysis_zones = _analysis_zone_frame(analysis_points)
    analysis_polygons = _analysis_polygon_frame(analysis_points)
    polygon_shift = max((analysis_points.bounds().max_x - analysis_points.bounds().min_x) / 80.0, 0.001)
    shifted_polygons = _shift_polygons(analysis_polygons, polygon_shift, polygon_shift)
    analysis_lines = _analysis_line_frame(analysis_points)
    analysis_network = analysis_lines.network_build() if len(analysis_lines) else GeoPromptFrame.from_records([], crs=materialized_case.crs)
    analysis_trajectory = _analysis_trajectory_frame(analysis_points)
    analysis_slivers = _analysis_sliver_frame(analysis_points)
    regions = _join_frame_from_case(materialized_case)
    baseline_change_frame = frame.change_detection(changed_frame, max_distance=0.05) if len(records) else GeoPromptFrame.from_records([], crs=materialized_case.crs)
    current_change_frame = frame.change_detection(changed_frame_variant, max_distance=0.05) if len(records) else GeoPromptFrame.from_records([], crs=materialized_case.crs)
    baseline_change_events = baseline_change_frame.extract_change_events() if len(baseline_change_frame) else GeoPromptFrame.from_records([], crs=materialized_case.crs)
    current_change_events = current_change_frame.extract_change_events() if len(current_change_frame) else GeoPromptFrame.from_records([], crs=materialized_case.crs)
    autocorrelation_frame = frame.spatial_autocorrelation("demand_index", mode="distance_band", max_distance=0.05) if records and "demand_index" in frame.columns else None
    clustered_frame = frame.centroid_cluster(k=min(3, len(frame))) if len(frame) else None

    fixture = {
        "case": materialized_case,
        "geopandas": geopandas,
        "shape": shape,
        "box": box,
        "frame": frame,
        "records": records,
        "feature_ids": feature_ids,
        "shapely_geometries": shapely_geometries,
        "geopandas_frame": geopandas_frame,
        "spatial_index": spatial_index,
        "query_candidate_indexes": query_candidate_indexes,
        "changed_frame": changed_frame,
        "changed_frame_variant": changed_frame_variant,
        "baseline_change_frame": baseline_change_frame,
        "current_change_frame": current_change_frame,
        "baseline_change_events": baseline_change_events,
        "current_change_events": current_change_events,
        "autocorrelation_frame": autocorrelation_frame,
        "clustered_frame": clustered_frame,
        "analysis_points": analysis_points,
        "analysis_point_records": analysis_point_records,
        "analysis_queries": analysis_queries,
        "analysis_zones": analysis_zones,
        "analysis_polygons": analysis_polygons,
        "shifted_polygons": shifted_polygons,
        "analysis_lines": analysis_lines,
        "analysis_network": analysis_network,
        "analysis_trajectory": analysis_trajectory,
        "analysis_slivers": analysis_slivers,
        "regions": regions,
    }
    _DATASET_FIXTURE_CACHE[cache_key] = fixture
    return fixture


def _run_selected_benchmark(
    benchmarks: list[dict[str, Any]],
    operation: str,
    func: Callable[[], Any],
    repeats: int = 20,
    benchmark_filter: Callable[[str], bool] | None = None,
) -> None:
    if benchmark_filter is not None and not benchmark_filter(operation):
        return
    benchmark, _ = _benchmark(operation, func, repeats=repeats)
    benchmarks.append(benchmark)


def _join_frame_from_case(case: CorpusCase) -> GeoPromptFrame | None:
    if case.join_records is not None:
        return GeoPromptFrame.from_records(case.join_records, crs=case.crs)
    if case.join_path is None:
        return None
    return read_features(case.join_path, crs=case.crs)


def _load_compare_dependencies() -> tuple[Any, Callable[[dict[str, Any]], Any], Callable[..., Any]]:
    try:
        geopandas = importlib.import_module("geopandas")
        shapely_geometry = importlib.import_module("shapely.geometry")
    except ImportError as exc:
        raise RuntimeError("Install comparison extras with 'pip install -e .[compare]' before running geoprompt-compare.") from exc

    return geopandas, shapely_geometry.shape, shapely_geometry.box


def _benchmark(operation: str, func: Callable[[], Any], repeats: int = 20) -> tuple[dict[str, Any], Any]:
    timings: list[float] = []
    result: Any = None
    for _ in range(repeats):
        started_at = time.perf_counter()
        result = func()
        timings.append(time.perf_counter() - started_at)
    return (
        {
            "operation": operation,
            "median_seconds": statistics.median(timings),
            "min_seconds": min(timings),
            "max_seconds": max(timings),
            "repeats": repeats,
        },
        result,
    )


def _nearest_neighbors_reference(ids: list[str], centroids: list[Any]) -> list[dict[str, Any]]:
    neighbors: list[dict[str, Any]] = []
    for index, origin in enumerate(ids):
        candidates: list[dict[str, Any]] = []
        for other_index, destination in enumerate(ids):
            if other_index == index:
                continue
            candidates.append(
                {
                    "origin": origin,
                    "neighbor": destination,
                    "distance": float(centroids[index].distance(centroids[other_index])),
                }
            )
        candidates.sort(key=lambda item: (float(item["distance"]), str(item["neighbor"])))
        neighbors.append(candidates[0])
    return neighbors


def _as_geojson_geometry(geometry: dict[str, Any]) -> dict[str, Any]:
    geometry_type = str(geometry["type"])
    coordinates = geometry["coordinates"]
    if geometry_type == "Point":
        return {"type": "Point", "coordinates": list(coordinates)}
    if geometry_type == "LineString":
        return {"type": "LineString", "coordinates": [list(coord) for coord in coordinates]}
    if geometry_type == "Polygon":
        return {"type": "Polygon", "coordinates": [[list(coord) for coord in coordinates]]}
    raise TypeError(f"unsupported geometry type for comparison: {geometry_type}")


def _rectangular_polygon(min_x: float, min_y: float, max_x: float, max_y: float) -> dict[str, Any]:
    return {
        "type": "Polygon",
        "coordinates": [
            (min_x, min_y),
            (max_x, min_y),
            (max_x, max_y),
            (min_x, max_y),
            (min_x, min_y),
        ],
    }


def _analysis_point_frame(frame: GeoPromptFrame) -> GeoPromptFrame:
    rows: list[dict[str, Any]] = []
    for index, record in enumerate(sorted(frame.to_records(), key=lambda item: str(item.get("site_id", ""))), start=1):
        centroid = geometry_centroid(record["geometry"])
        demand_value = float(record.get("demand_index", index) or index)
        capacity_value = float(record.get("capacity_index", demand_value + 1.0) or (demand_value + 1.0))
        priority_value = float(record.get("priority_index", 1.0) or 1.0)
        rows.append(
            {
                "site_id": str(record.get("site_id", f"feature-{index:03d}")),
                "source_type": str(record["geometry"]["type"]),
                "value": (demand_value * 100.0) + (capacity_value * 10.0),
                "demand_index": demand_value,
                "capacity_index": capacity_value,
                "priority_index": priority_value,
                "weight": max(priority_value, 0.1),
                "time": float(index),
                "geometry": {"type": "Point", "coordinates": [float(centroid[0]), float(centroid[1])]},
            }
        )
    return GeoPromptFrame.from_records(rows, crs=frame.crs)


def _analysis_zone_frame(point_frame: GeoPromptFrame) -> GeoPromptFrame:
    bounds = point_frame.bounds()
    extent = max(bounds.max_x - bounds.min_x, bounds.max_y - bounds.min_y, 1e-6)
    padding = extent * 0.05
    mid_x = (bounds.min_x + bounds.max_x) / 2.0
    mid_y = (bounds.min_y + bounds.max_y) / 2.0
    rows = [
        {
            "zone_id": "zone-sw",
            "geometry": _rectangular_polygon(bounds.min_x - padding, bounds.min_y - padding, mid_x, mid_y),
        },
        {
            "zone_id": "zone-ne",
            "geometry": _rectangular_polygon(mid_x, mid_y, bounds.max_x + padding, bounds.max_y + padding),
        },
    ]
    return GeoPromptFrame.from_records(rows, crs=point_frame.crs)


def _analysis_polygon_frame(point_frame: GeoPromptFrame) -> GeoPromptFrame:
    bounds = point_frame.bounds()
    half_size = max((bounds.max_x - bounds.min_x) / 60.0, (bounds.max_y - bounds.min_y) / 60.0, 0.002)
    rows: list[dict[str, Any]] = []
    for index, record in enumerate(point_frame.to_records()[:8], start=1):
        cx, cy = geometry_centroid(record["geometry"])
        rows.append(
            {
                "site_id": f"poly-{index:03d}",
                "group_id": "group-a" if index % 2 else "group-b",
                "value": float(record.get("value", index) or index),
                "geometry": _rectangular_polygon(cx - half_size, cy - half_size, cx + half_size, cy + half_size),
            }
        )
    return GeoPromptFrame.from_records(rows, crs=point_frame.crs)


def _shift_polygons(frame: GeoPromptFrame, dx: float, dy: float) -> GeoPromptFrame:
    rows = []
    for record in frame.to_records():
        rows.append(
            {
                **record,
                "site_id": f"{record.get('site_id', 'poly')}-shifted",
                "geometry": transform_geometry(record["geometry"], lambda coordinate: (coordinate[0] + dx, coordinate[1] + dy)),
            }
        )
    return GeoPromptFrame.from_records(rows, crs=frame.crs)


def _analysis_line_frame(point_frame: GeoPromptFrame) -> GeoPromptFrame:
    coords = [geometry_centroid(record["geometry"]) for record in point_frame.to_records()[:6]]
    if len(coords) < 2:
        coords = [(-111.95, 40.7), (-111.9, 40.7), (-111.85, 40.7), (-111.8, 40.7)]
    rows: list[dict[str, Any]] = []
    for index in range(len(coords) - 1):
        rows.append(
            {
                "site_id": f"edge-{index + 1:03d}",
                "geometry": {"type": "LineString", "coordinates": [coords[index], coords[index + 1]]},
                "demand_index": float(index + 1),
                "capacity_index": float(index + 2),
                "priority_index": float(index + 1),
            }
        )
    return GeoPromptFrame.from_records(rows, crs=point_frame.crs)


def _analysis_trajectory_frame(point_frame: GeoPromptFrame) -> GeoPromptFrame:
    bounds = point_frame.bounds()
    step = max((bounds.max_x - bounds.min_x) / 100.0, (bounds.max_y - bounds.min_y) / 100.0, 0.001)
    rows = [
        {"site_id": "traj-001", "time": 0.0, "value": 1.0, "geometry": {"type": "Point", "coordinates": [bounds.min_x, bounds.min_y]}},
        {"site_id": "traj-002", "time": 1.0, "value": 2.0, "geometry": {"type": "Point", "coordinates": [bounds.min_x + (step * 0.3), bounds.min_y + (step * 0.2)]}},
        {"site_id": "traj-003", "time": 2.0, "value": 3.0, "geometry": {"type": "Point", "coordinates": [bounds.min_x + (step * 0.6), bounds.min_y + (step * 0.1)]}},
        {"site_id": "traj-004", "time": 3.0, "value": 4.0, "geometry": {"type": "Point", "coordinates": [bounds.max_x - (step * 1.2), bounds.max_y - (step * 1.1)]}},
        {"site_id": "traj-005", "time": 4.0, "value": 5.0, "geometry": {"type": "Point", "coordinates": [bounds.max_x - (step * 0.8), bounds.max_y - (step * 0.9)]}},
        {"site_id": "traj-006", "time": 5.0, "value": 6.0, "geometry": {"type": "Point", "coordinates": [bounds.max_x, bounds.max_y]}},
    ]
    return GeoPromptFrame.from_records(rows, crs=point_frame.crs)


def _analysis_sliver_frame(point_frame: GeoPromptFrame) -> GeoPromptFrame:
    bounds = point_frame.bounds()
    extent = max(bounds.max_x - bounds.min_x, bounds.max_y - bounds.min_y, 1e-6)
    big_size = extent / 8.0
    tiny_size = max(extent / 10000.0, 1e-6)
    rows = [
        {
            "site_id": "big",
            "geometry": _rectangular_polygon(bounds.min_x, bounds.min_y, bounds.min_x + big_size, bounds.min_y + big_size),
        },
        {
            "site_id": "tiny",
            "geometry": _rectangular_polygon(bounds.min_x, bounds.min_y, bounds.min_x + tiny_size, bounds.min_y + tiny_size),
        },
    ]
    return GeoPromptFrame.from_records(rows, crs=point_frame.crs)


def _dataset_report(case: CorpusCase, tolerance: float, benchmark_filter: Callable[[str], bool] | None = None) -> dict[str, Any]:
    fixture = _dataset_fixture(case)
    case = fixture["case"]
    geopandas = fixture["geopandas"]
    shape = fixture["shape"]
    box = fixture["box"]
    projection_tolerance = max(tolerance, 1e-6)

    frame = fixture["frame"]
    records = fixture["records"]
    feature_ids = fixture["feature_ids"]
    geoprompt_lengths = frame.geometry_lengths()
    geoprompt_areas = frame.geometry_areas()
    geoprompt_centroids = [geometry_centroid(record["geometry"]) for record in records]

    shapely_geometries = fixture["shapely_geometries"]
    geopandas_frame = fixture["geopandas_frame"]

    geometry_comparison: list[dict[str, Any]] = []
    for record, geoprompt_length, geoprompt_area, geoprompt_centroid, shapely_geometry in zip(
        records,
        geoprompt_lengths,
        geoprompt_areas,
        geoprompt_centroids,
        shapely_geometries,
        strict=True,
    ):
        shapely_centroid = shapely_geometry.centroid
        geometry_comparison.append(
            {
                "site_id": str(record.get("site_id", "unknown")),
                "geometry_type": str(record["geometry"]["type"]),
                "length_delta": abs(float(geoprompt_length) - float(shapely_geometry.length)),
                "area_delta": abs(float(geoprompt_area) - float(shapely_geometry.area)),
                "centroid_x_delta": abs(float(geoprompt_centroid[0]) - float(shapely_centroid.x)),
                "centroid_y_delta": abs(float(geoprompt_centroid[1]) - float(shapely_centroid.y)),
            }
        )

    geoprompt_bounds = frame.bounds().__dict__
    geopandas_bounds = geopandas_frame.total_bounds.tolist()
    geoprompt_nearest = frame.nearest_neighbors(k=1)
    reference_nearest = _nearest_neighbors_reference(feature_ids, [geometry.centroid for geometry in shapely_geometries])

    min_x, min_y, max_x, max_y = case.query_bounds
    geoprompt_query = [str(record.get("site_id", "unknown")) for record in frame.query_bounds(min_x=min_x, min_y=min_y, max_x=max_x, max_y=max_y)]
    spatial_index = fixture["spatial_index"]
    query_candidate_indexes = fixture["query_candidate_indexes"]
    reference_query = [
        str(value)
        for value in geopandas_frame.loc[
            geopandas_frame.geometry.intersects(box(min_x, min_y, max_x, max_y)),
            "site_id",
        ].tolist()
    ]

    projected_frame = frame.to_crs("EPSG:3857")
    projected_reference = geopandas_frame.to_crs("EPSG:3857")
    projected_bounds = projected_frame.bounds().__dict__
    projected_reference_bounds = projected_reference.total_bounds.tolist()
    changed_frame = fixture["changed_frame"]
    changed_frame_variant = fixture["changed_frame_variant"]

    join_report: dict[str, Any] | None = None
    clip_report: dict[str, Any] | None = None
    dissolve_report: dict[str, Any] | None = None
    performance_report: dict[str, Any] = {
        "spatial_index": spatial_index.stats().__dict__,
        "query_bounds_candidates": len(query_candidate_indexes),
        "query_bounds_total": len(records),
        "query_bounds_pruning_ratio": 1.0 - (len(query_candidate_indexes) / len(records) if records else 0.0),
    }
    analysis_points = fixture["analysis_points"]
    analysis_point_records = fixture["analysis_point_records"]
    analysis_queries = fixture["analysis_queries"]
    analysis_zones = fixture["analysis_zones"]
    analysis_polygons = fixture["analysis_polygons"]
    shifted_polygons = fixture["shifted_polygons"]
    analysis_lines = fixture["analysis_lines"]
    analysis_network = fixture["analysis_network"]
    analysis_trajectory = fixture["analysis_trajectory"]
    analysis_slivers = fixture["analysis_slivers"]
    regions = fixture["regions"]
    baseline_change_frame = fixture["baseline_change_frame"]
    current_change_frame = fixture["current_change_frame"]
    baseline_change_events = fixture["baseline_change_events"]
    current_change_events = fixture["current_change_events"]
    autocorrelation_frame = fixture["autocorrelation_frame"]
    clustered_frame = fixture["clustered_frame"]
    if regions is not None:
        geoprompt_join = regions.spatial_join(frame, predicate="intersects")
        geoprompt_pairs = sorted(f"{row['region_id']}->{row['site_id']}" for row in geoprompt_join)

        region_geometries = [shape(_as_geojson_geometry(record["geometry"])) for record in regions.to_records()]
        region_ids = [str(record["region_id"]) for record in regions.to_records()]
        reference_pairs: list[str] = []
        for region_id, region_geometry in zip(region_ids, region_geometries, strict=True):
            for feature_id, feature_geometry in zip(feature_ids, shapely_geometries, strict=True):
                if region_geometry.intersects(feature_geometry):
                    reference_pairs.append(f"{region_id}->{feature_id}")
        join_report = {
            "pair_match": geoprompt_pairs == sorted(set(reference_pairs)),
            "geoprompt_pairs": geoprompt_pairs,
            "reference_pairs": sorted(set(reference_pairs)),
        }

        clipped = frame.clip(regions)
        shapely_ops = importlib.import_module("shapely.ops")
        mask_union = shapely_ops.unary_union([geometry_to_shapely(record["geometry"]) for record in regions.to_records()])
        reference_clip_geometries = [
            geometry
            for feature_geometry in shapely_geometries
            for geometry in geometry_from_shapely(feature_geometry.intersection(mask_union))
        ]
        clip_report = {
            "feature_count_match": len(clipped) == len(reference_clip_geometries),
            "geoprompt_feature_count": len(clipped),
            "reference_feature_count": len(reference_clip_geometries),
        }

        geoprompt_dissolved = regions.dissolve(by="region_band", aggregations={"region_name": "count"})
        geopandas_dissolved = geopandas.GeoDataFrame(
            [{key: value for key, value in record.items() if key != "geometry"} for record in regions.to_records()],
            geometry=region_geometries,
            crs=case.crs,
        ).dissolve(by="region_band", aggfunc={"region_name": "count"}).reset_index()
        dissolve_report = {
            "feature_count_match": len(geoprompt_dissolved) == len(geopandas_dissolved),
            "bands_match": sorted(str(record["region_band"]) for record in geoprompt_dissolved) == sorted(str(value) for value in geopandas_dissolved["region_band"].tolist()),
        }

        region_index = regions.spatial_index(mode="geometry")
        join_candidate_pairs = sum(len(region_index.query(geometry_bounds(record["geometry"]))) for record in records)
        total_pairs = len(records) * len(regions)
        performance_report["spatial_join_candidate_pairs"] = join_candidate_pairs
        performance_report["spatial_join_total_pairs"] = total_pairs
        performance_report["spatial_join_pruning_ratio"] = 1.0 - (join_candidate_pairs / total_pairs if total_pairs else 0.0)

    benchmarks: list[dict[str, Any]] = []
    for operation, func in [
        (f"{case.name}.geoprompt.geometry_metrics", lambda: (frame.geometry_lengths(), frame.geometry_areas(), frame.bounds())),
        (f"{case.name}.reference.geometry_metrics", lambda: ([geometry.length for geometry in shapely_geometries], [geometry.area for geometry in shapely_geometries], geopandas_frame.total_bounds)),
        (f"{case.name}.geoprompt.spatial_index_query", lambda: frame.spatial_index().query((min_x, min_y, max_x, max_y))),
        (f"{case.name}.geoprompt.nearest_neighbors", lambda: frame.nearest_neighbors(k=1)),
        (f"{case.name}.reference.nearest_neighbors", lambda: _nearest_neighbors_reference(feature_ids, [geometry.centroid for geometry in shapely_geometries])),
        (f"{case.name}.geoprompt.query_bounds", lambda: frame.query_bounds(min_x=min_x, min_y=min_y, max_x=max_x, max_y=max_y)),
        (f"{case.name}.reference.query_bounds", lambda: geopandas_frame.loc[geopandas_frame.geometry.intersects(box(min_x, min_y, max_x, max_y))]),
        (f"{case.name}.geoprompt.to_crs", lambda: frame.to_crs("EPSG:3857")),
        (f"{case.name}.reference.to_crs", lambda: geopandas_frame.to_crs("EPSG:3857")),
        (f"{case.name}.geoprompt.centroid_cluster", lambda: frame.centroid_cluster(k=min(3, len(frame)))),
        (f"{case.name}.geoprompt.cluster_diagnostics", lambda: frame.cluster_diagnostics(k_values=[1, min(2, len(frame)), min(3, len(frame))])),
        (f"{case.name}.geoprompt.summarize_clusters", lambda: clustered_frame.summarize_clusters() if clustered_frame is not None else GeoPromptFrame.from_records([], crs=case.crs)),
        (f"{case.name}.geoprompt.spatial_lag", lambda: frame.spatial_lag("demand_index", mode="distance_band", max_distance=0.05)),
        (f"{case.name}.geoprompt.spatial_autocorrelation", lambda: frame.spatial_autocorrelation("demand_index", mode="distance_band", max_distance=0.05)),
        (f"{case.name}.geoprompt.summarize_autocorrelation", lambda: autocorrelation_frame.summarize_autocorrelation("demand_index") if autocorrelation_frame is not None else GeoPromptFrame.from_records([], crs=case.crs)),
        (f"{case.name}.geoprompt.report_autocorrelation_patterns", lambda: autocorrelation_frame.report_autocorrelation_patterns("demand_index") if autocorrelation_frame is not None else GeoPromptFrame.from_records([], crs=case.crs)),
        (f"{case.name}.geoprompt.change_detection", lambda: frame.change_detection(changed_frame, max_distance=0.05)),
        (f"{case.name}.geoprompt.extract_change_events", lambda: baseline_change_frame.extract_change_events()),
        (f"{case.name}.geoprompt.compare_change_events", lambda: baseline_change_events.compare_change_events(current_change_events)),
        (f"{case.name}.geoprompt.compare_change_events_equivalent", lambda: baseline_change_events.compare_change_events(current_change_events, match_mode="equivalent")),
        (f"{case.name}.geoprompt.snap_geometries", lambda: frame.snap_geometries(tolerance=0.005)),
        (f"{case.name}.geoprompt.clean_topology", lambda: frame.clean_topology(tolerance=0.005, min_segment_length=0.001)),
    ]:
        _run_selected_benchmark(benchmarks, operation, func, benchmark_filter=benchmark_filter)

    compare_bounds = analysis_points.bounds()
    benchmark_inputs: list[tuple[str, Callable[[], Any], int]] = [
        (f"{case.name}.geoprompt.raster_sample", lambda: analysis_points.raster_sample(analysis_queries, value_column="value", k=1), 5),
        (f"{case.name}.geoprompt.zonal_stats", lambda: analysis_points.zonal_stats(analysis_zones, value_column="value", zone_id_column="zone_id"), 5),
        (f"{case.name}.geoprompt.reclassify", lambda: analysis_points.reclassify("value", breaks=[(0.0, 100.0, "low"), (100.0, 1000.0, "high")]), 5),
        (f"{case.name}.geoprompt.resample", lambda: analysis_points.resample(method="spatial_thin", min_distance=max((compare_bounds.max_x - compare_bounds.min_x) / 40.0, 0.001)), 5),
        (f"{case.name}.geoprompt.raster_clip", lambda: analysis_points.raster_clip(compare_bounds.min_x, compare_bounds.min_y, (compare_bounds.min_x + compare_bounds.max_x) / 2.0, (compare_bounds.min_y + compare_bounds.max_y) / 2.0), 5),
        (f"{case.name}.geoprompt.mosaic", lambda: analysis_points.mosaic(analysis_queries, conflict_resolution="first"), 5),
        (f"{case.name}.geoprompt.to_points", lambda: analysis_polygons.to_points(), 5),
        (f"{case.name}.geoprompt.to_polygons", lambda: analysis_points.to_polygons(buffer_distance=max((compare_bounds.max_x - compare_bounds.min_x) / 200.0, 0.001)), 5),
        (f"{case.name}.geoprompt.contours", lambda: analysis_points.contours(value_column="value", interval_count=3, grid_resolution=10), 3),
        (f"{case.name}.geoprompt.hillshade", lambda: analysis_points.hillshade(elevation_column="value", grid_resolution=10), 3),
        (f"{case.name}.geoprompt.slope_aspect", lambda: analysis_points.slope_aspect(elevation_column="value", grid_resolution=10), 3),
        (f"{case.name}.geoprompt.idw_interpolation", lambda: analysis_points.idw_interpolation(value_column="value", grid_resolution=10), 3),
        (f"{case.name}.geoprompt.kriging_surface", lambda: analysis_points.kriging_surface(value_column="value", grid_resolution=10), 3),
        (f"{case.name}.geoprompt.thiessen_polygons", lambda: analysis_points.thiessen_polygons(), 5),
        (f"{case.name}.geoprompt.spatial_weights_matrix", lambda: analysis_points.spatial_weights_matrix(k=4), 5),
        (f"{case.name}.geoprompt.hotspot_getis_ord", lambda: analysis_points.hotspot_getis_ord(value_column="value", mode="k_nearest", k=4), 5),
        (f"{case.name}.geoprompt.local_outlier_factor_spatial", lambda: analysis_points.local_outlier_factor_spatial(value_column="value", k=4), 5),
        (f"{case.name}.geoprompt.kernel_density", lambda: analysis_points.kernel_density(grid_resolution=10), 3),
        (f"{case.name}.geoprompt.standard_deviational_ellipse", lambda: analysis_points.standard_deviational_ellipse(weight_column="weight"), 5),
        (f"{case.name}.geoprompt.center_of_minimum_distance", lambda: analysis_points.center_of_minimum_distance(weight_column="weight"), 5),
        (f"{case.name}.geoprompt.spatial_regression", lambda: analysis_points.spatial_regression(dependent_column="value", independent_columns=["demand_index"], k_neighbors=4), 5),
        (f"{case.name}.geoprompt.geographically_weighted_summary", lambda: analysis_points.geographically_weighted_summary(dependent_column="value", independent_columns=["demand_index"], bandwidth=max((compare_bounds.max_x - compare_bounds.min_x) / 10.0, 0.01)), 3),
        (f"{case.name}.geoprompt.join_by_largest_overlap", lambda: analysis_polygons.join_by_largest_overlap(shifted_polygons), 5),
        (f"{case.name}.geoprompt.erase", lambda: analysis_polygons.erase(shifted_polygons), 3),
        (f"{case.name}.geoprompt.identity_overlay", lambda: analysis_polygons.identity_overlay(shifted_polygons), 3),
        (f"{case.name}.geoprompt.multipart_to_singlepart", lambda: analysis_polygons.multipart_to_singlepart(), 5),
        (f"{case.name}.geoprompt.singlepart_to_multipart", lambda: analysis_polygons.singlepart_to_multipart(group_column="group_id"), 5),
        (f"{case.name}.geoprompt.eliminate_slivers", lambda: analysis_slivers.eliminate_slivers(min_area=max((compare_bounds.max_x - compare_bounds.min_x) / 1000.0, 1e-6)), 5),
        (f"{case.name}.geoprompt.simplify", lambda: analysis_lines.simplify(tolerance=max((compare_bounds.max_x - compare_bounds.min_x) / 1000.0, 1e-6)), 5),
        (f"{case.name}.geoprompt.densify", lambda: analysis_lines.densify(max_segment_length=max((compare_bounds.max_x - compare_bounds.min_x) / 40.0, 0.001)), 5),
        (f"{case.name}.geoprompt.smooth_geometry", lambda: analysis_lines.smooth_geometry(iterations=2), 5),
        (f"{case.name}.geoprompt.trajectory_staypoint_detection", lambda: analysis_trajectory.trajectory_staypoint_detection(time_column="time", max_radius=max((compare_bounds.max_x - compare_bounds.min_x) / 50.0, 0.005), min_duration=1.0), 5),
        (f"{case.name}.geoprompt.trajectory_simplify", lambda: analysis_trajectory.trajectory_simplify(tolerance=max((compare_bounds.max_x - compare_bounds.min_x) / 1000.0, 1e-6)), 5),
        (f"{case.name}.geoprompt.spatiotemporal_cube", lambda: analysis_points.spatiotemporal_cube(time_column="time", value_column="value", time_intervals=3, grid_resolution=4, aggregation="count"), 3),
        (f"{case.name}.geoprompt.geohash_encode", lambda: analysis_points.geohash_encode(precision=6), 5),
        (f"{case.name}.geoprompt.spatial_elastic_net", lambda: analysis_points.spatial_elastic_net(["demand_index", "capacity_index", "priority_index"], "value", alpha=0.05, l1_ratio=0.4, epochs=120), 3),
        (f"{case.name}.geoprompt.spatial_dbscan_clustering", lambda: analysis_points.spatial_dbscan_clustering(min_points=4), 3),
        (f"{case.name}.geoprompt.spatial_hdbscan", lambda: analysis_points.spatial_hdbscan(min_cluster_size=4, min_samples=3), 3),
        (f"{case.name}.geoprompt.spatial_optimal_transport", lambda: analysis_points.spatial_optimal_transport("weight", reg=0.25, n_iterations=20), 3),
        (f"{case.name}.geoprompt.spatial_conformal_predictor", lambda: analysis_points.spatial_conformal_predictor(["demand_index", "capacity_index", "priority_index"], "value", calibration_fraction=0.25, k_neighbors=5, alpha=0.2), 3),
    ]
    for operation, func, repeats in benchmark_inputs:
        _run_selected_benchmark(benchmarks, operation, func, repeats=repeats, benchmark_filter=benchmark_filter)

    if len(analysis_network) > 0:
        node_lookup: dict[str, tuple[float, float]] = {}
        for network_row in analysis_network.to_records():
            node_lookup.setdefault(str(network_row["from_node_id"]), tuple(network_row["from_node"]))
            node_lookup.setdefault(str(network_row["to_node_id"]), tuple(network_row["to_node"]))
        node_items = list(node_lookup.items())
        if len(node_items) >= 3:
            origin_frame = GeoPromptFrame.from_records([
                {"site_id": "origin-a", "geometry": {"type": "Point", "coordinates": list(node_items[0][1])}},
            ], crs=case.crs)
            destination_frame = GeoPromptFrame.from_records([
                {"site_id": "destination-a", "geometry": {"type": "Point", "coordinates": list(node_items[-1][1])}},
            ], crs=case.crs)
            stop_frame = GeoPromptFrame.from_records([
                {"site_id": f"stop-{index + 1}", "geometry": {"type": "Point", "coordinates": list(node_items[index][1])}}
                for index in range(min(3, len(node_items)))
            ], crs=case.crs)
            network_benchmarks: list[tuple[str, Callable[[], Any], int]] = [
                (f"{case.name}.geoprompt.snap_to_network_nodes", lambda: analysis_network.snap_to_network_nodes(analysis_queries), 5),
                (f"{case.name}.geoprompt.origin_destination_matrix", lambda: analysis_network.origin_destination_matrix(origin_frame, destination_frame), 5),
                (f"{case.name}.geoprompt.k_shortest_paths", lambda: analysis_network.k_shortest_paths(node_items[0][0], node_items[-1][0], k=2), 5),
                (f"{case.name}.geoprompt.network_trace", lambda: analysis_network.network_trace(node_items[0][0], direction="downstream"), 5),
                (f"{case.name}.geoprompt.route_sequence_optimize", lambda: analysis_network.route_sequence_optimize(stop_frame), 5),
            ]
            for operation, func, repeats in network_benchmarks:
                _run_selected_benchmark(benchmarks, operation, func, repeats=repeats, benchmark_filter=benchmark_filter)

    if regions is not None:
        region_geometries = [shape(_as_geojson_geometry(record["geometry"])) for record in regions.to_records()]
        region_ids = [str(record["region_id"]) for record in regions.to_records()]
        _run_selected_benchmark(benchmarks, f"{case.name}.geoprompt.spatial_join", lambda: regions.spatial_join(frame, predicate="intersects"), benchmark_filter=benchmark_filter)
        _run_selected_benchmark(
            benchmarks,
            f"{case.name}.reference.spatial_join",
            lambda: [
                f"{region_id}->{feature_id}"
                for region_id, region_geometry in zip(region_ids, region_geometries, strict=True)
                for feature_id, feature_geometry in zip(feature_ids, shapely_geometries, strict=True)
                if region_geometry.intersects(feature_geometry)
            ],
            benchmark_filter=benchmark_filter,
        )
        _run_selected_benchmark(benchmarks, f"{case.name}.geoprompt.clip", lambda: frame.clip(regions), benchmark_filter=benchmark_filter)
        shapely_ops = importlib.import_module("shapely.ops")
        mask_union = shapely_ops.unary_union([geometry_to_shapely(record["geometry"]) for record in regions.to_records()])
        _run_selected_benchmark(
            benchmarks,
            f"{case.name}.reference.clip",
            lambda: [
                geometry
                for feature_geometry in shapely_geometries
                for geometry in geometry_from_shapely(feature_geometry.intersection(mask_union))
            ],
            benchmark_filter=benchmark_filter,
        )
        _run_selected_benchmark(benchmarks, f"{case.name}.geoprompt.dissolve", lambda: regions.dissolve(by="region_band", aggregations={"region_name": "count"}), benchmark_filter=benchmark_filter)
        _run_selected_benchmark(
            benchmarks,
            f"{case.name}.reference.dissolve",
            lambda: geopandas.GeoDataFrame(
                [{key: value for key, value in record.items() if key != "geometry"} for record in regions.to_records()],
                geometry=region_geometries,
                crs=case.crs,
            ).dissolve(by="region_band", aggfunc={"region_name": "count"}).reset_index(),
            benchmark_filter=benchmark_filter,
        )

        _run_selected_benchmark(benchmarks, f"{case.name}.geoprompt.zone_fit_score", lambda: frame.zone_fit_score(regions, zone_id_column="region_id"), benchmark_filter=benchmark_filter)
        _run_selected_benchmark(benchmarks, f"{case.name}.geoprompt.overlay_summary_grouped", lambda: frame.overlay_summary(regions, right_id_column="region_id", group_by="region_band", normalize_by="both"), benchmark_filter=benchmark_filter)
        _run_selected_benchmark(benchmarks, f"{case.name}.geoprompt.overlay_group_comparison", lambda: frame.overlay_group_comparison(regions, group_by="region_band", right_id_column="region_id"), benchmark_filter=benchmark_filter)
        _run_selected_benchmark(
            benchmarks,
            f"{case.name}.geoprompt.overlay_union",
            lambda: regions.overlay_union(
                regions.query_bounds(min_x=case.query_bounds[0], min_y=case.query_bounds[1], max_x=case.query_bounds[2], max_y=case.query_bounds[3]),
                left_id_column="region_id",
                right_id_column="region_id",
            ),
            benchmark_filter=benchmark_filter,
        )
        _run_selected_benchmark(
            benchmarks,
            f"{case.name}.geoprompt.overlay_difference",
            lambda: regions.overlay_difference(
                regions.query_bounds(min_x=case.query_bounds[0], min_y=case.query_bounds[1], max_x=case.query_bounds[2], max_y=case.query_bounds[3]),
                left_id_column="region_id",
                right_id_column="region_id",
            ),
            benchmark_filter=benchmark_filter,
        )
        _run_selected_benchmark(
            benchmarks,
            f"{case.name}.geoprompt.overlay_symmetric_difference",
            lambda: regions.overlay_symmetric_difference(
                regions.query_bounds(min_x=case.query_bounds[0], min_y=case.query_bounds[1], max_x=case.query_bounds[2], max_y=case.query_bounds[3]),
                left_id_column="region_id",
                right_id_column="region_id",
            ),
            benchmark_filter=benchmark_filter,
        )
        _run_selected_benchmark(
            benchmarks,
            f"{case.name}.geoprompt.polygon_split",
            lambda: regions.polygon_split(
                regions.query_bounds(min_x=case.query_bounds[0], min_y=case.query_bounds[1], max_x=case.query_bounds[2], max_y=case.query_bounds[3]),
                id_column="region_id",
                splitter_id_column="region_id",
            ),
            benchmark_filter=benchmark_filter,
        )

        corridor_rows = [row for row in frame.to_records() if row["geometry"]["type"] == "LineString"]
        if corridor_rows:
            corridor_frame = GeoPromptFrame.from_records(corridor_rows, crs=case.crs)
            network_frame = corridor_frame.network_build()
            _run_selected_benchmark(benchmarks, f"{case.name}.geoprompt.network_build", lambda: corridor_frame.network_build(), benchmark_filter=benchmark_filter)
            _run_selected_benchmark(benchmarks, f"{case.name}.geoprompt.corridor_reach", lambda: frame.corridor_reach(corridor_frame, max_distance=0.05, corridor_id_column="site_id"), benchmark_filter=benchmark_filter)
            _run_selected_benchmark(benchmarks, f"{case.name}.geoprompt.corridor_diagnostics", lambda: frame.corridor_diagnostics(corridor_frame, max_distance=0.05, corridor_id_column="site_id"), benchmark_filter=benchmark_filter)
            _run_selected_benchmark(benchmarks, f"{case.name}.geoprompt.line_split", lambda: corridor_frame.line_split(split_at_intersections=True), benchmark_filter=benchmark_filter)
            if len(network_frame) > 0:
                first_row = network_frame.to_records()[0]
                _run_selected_benchmark(benchmarks, f"{case.name}.geoprompt.shortest_path", lambda: network_frame.shortest_path(first_row["from_node_id"], first_row["to_node_id"]), benchmark_filter=benchmark_filter)
                _run_selected_benchmark(benchmarks, f"{case.name}.geoprompt.service_area", lambda: network_frame.service_area(first_row["from_node_id"], max_cost=float(first_row["edge_length"]) * 2.0), benchmark_filter=benchmark_filter)
                node_lookup: dict[str, tuple[float, float]] = {}
                for network_row in network_frame.to_records():
                    node_lookup.setdefault(str(network_row["from_node_id"]), tuple(network_row["from_node"]))
                    node_lookup.setdefault(str(network_row["to_node_id"]), tuple(network_row["to_node"]))
                node_items = list(node_lookup.items())
                if len(node_items) >= 4:
                    facility_records = [
                        {
                            "facility_id": f"facility-{index + 1}",
                            "geometry": {"type": "Point", "coordinates": list(node_items[index][1])},
                        }
                        for index in range(2)
                    ]
                    demand_records = [
                        {
                            "demand_id": f"demand-{index - 1}",
                            "demand": 1.0,
                            "geometry": {"type": "Point", "coordinates": list(node_items[index][1])},
                        }
                        for index in range(2, min(len(node_items), 6))
                    ]
                    facility_frame = GeoPromptFrame.from_records(facility_records, crs=case.crs)
                    demand_frame = GeoPromptFrame.from_records(demand_records, crs=case.crs)
                    _run_selected_benchmark(
                        benchmarks,
                        f"{case.name}.geoprompt.location_allocate",
                        lambda: network_frame.location_allocate(
                            facility_frame,
                            demand_frame,
                            facility_id_column="facility_id",
                            demand_id_column="demand_id",
                            demand_weight_column="demand",
                        ),
                        benchmark_filter=benchmark_filter,
                    )
                observation_records = []
                for index, network_record in enumerate(network_frame.to_records()[: min(4, len(network_frame))], start=1):
                    from_node = tuple(network_record["from_node"])
                    to_node = tuple(network_record["to_node"])
                    observation_records.append(
                        {
                            "site_id": f"obs-{index}",
                            "track_id": "track-a",
                            "sequence": index,
                            "geometry": {
                                "type": "Point",
                                "coordinates": [
                                    (from_node[0] + to_node[0]) / 2.0,
                                    (from_node[1] + to_node[1]) / 2.0,
                                ],
                            },
                        }
                    )
                if observation_records:
                    observation_frame = GeoPromptFrame.from_records(observation_records, crs=case.crs)
                    _run_selected_benchmark(benchmarks, f"{case.name}.geoprompt.trajectory_match", lambda: network_frame.trajectory_match(observation_frame, candidate_k=3, max_distance=0.05), benchmark_filter=benchmark_filter)
                    matched_trajectory = network_frame.trajectory_match(observation_frame, candidate_k=3, max_distance=0.05)
                    _run_selected_benchmark(benchmarks, f"{case.name}.geoprompt.summarize_trajectory_segments", lambda: matched_trajectory.summarize_trajectory_segments(), benchmark_filter=benchmark_filter)
                    summarized_trajectory = matched_trajectory.summarize_trajectory_segments()
                    _run_selected_benchmark(benchmarks, f"{case.name}.geoprompt.score_trajectory_segments", lambda: summarized_trajectory.score_trajectory_segments(), benchmark_filter=benchmark_filter)

    return {
        "dataset": case.name,
        "input_path": str(case.feature_path) if case.feature_path is not None else "generated:stress",
        "join_path": str(case.join_path) if case.join_path is not None else ("generated:stress-regions" if case.join_records is not None else None),
        "crs": case.crs,
        "feature_count": len(records),
        "join_feature_count": len(regions) if regions is not None else 0,
        "correctness": {
            "bounds_match": all(
                abs(left - right) <= tolerance
                for left, right in zip(
                    [geoprompt_bounds["min_x"], geoprompt_bounds["min_y"], geoprompt_bounds["max_x"], geoprompt_bounds["max_y"]],
                    geopandas_bounds,
                    strict=True,
                )
            ),
            "nearest_neighbor_match": [item["neighbor"] for item in geoprompt_nearest] == [item["neighbor"] for item in reference_nearest],
            "bounds_query_match": sorted(geoprompt_query) == sorted(reference_query),
            "geometry_metrics_within_tolerance": all(
                item["length_delta"] <= tolerance
                and item["area_delta"] <= tolerance
                and item["centroid_x_delta"] <= tolerance
                and item["centroid_y_delta"] <= tolerance
                for item in geometry_comparison
            ),
            "projected_bounds_match": all(
                abs(left - right) <= projection_tolerance
                for left, right in zip(
                    [projected_bounds["min_x"], projected_bounds["min_y"], projected_bounds["max_x"], projected_bounds["max_y"]],
                    projected_reference_bounds,
                    strict=True,
                )
            ),
            "geometry_comparison": geometry_comparison,
            "clip": clip_report,
            "dissolve": dissolve_report,
            "spatial_join": join_report,
        },
        "performance": performance_report,
        "benchmarks": benchmarks,
    }


def build_comparison_report(
    input_path: Path | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    tolerance: float = 1e-7,
    crs: str = "EPSG:4326",
    join_path: Path | None = None,
    benchmark_filter: Callable[[str], bool] | None = None,
) -> dict[str, Any]:
    cases = DEFAULT_CORPUS if input_path is None else [
        CorpusCase(
            name=input_path.stem,
            feature_path=input_path,
            crs=crs,
            query_bounds=(-111.97, 40.68, -111.84, 40.79),
            join_path=join_path,
        )
    ]
    datasets = [_dataset_report(case, tolerance=tolerance, benchmark_filter=benchmark_filter) for case in cases]

    return {
        "package": "geoprompt",
        "comparison": {
            "output_dir": str(output_dir),
            "tolerance": tolerance,
            "engines": ["geoprompt", "shapely", "geopandas"],
            "corpus": [dataset["dataset"] for dataset in datasets],
            "notes": [
                "Planar metric comparisons use raw coordinate space so Geoprompt matches Shapely and GeoPandas defaults.",
                "Geographic haversine distance is a separate Geoprompt mode and is not directly compared to Shapely or GeoPandas here.",
                "Projection comparisons use EPSG:3857 as a common reference target.",
            ],
        },
        "summary": {
            "all_bounds_match": all(dataset["correctness"]["bounds_match"] for dataset in datasets),
            "all_nearest_neighbor_match": all(dataset["correctness"]["nearest_neighbor_match"] for dataset in datasets),
            "all_bounds_query_match": all(dataset["correctness"]["bounds_query_match"] for dataset in datasets),
            "all_geometry_metrics_within_tolerance": all(dataset["correctness"]["geometry_metrics_within_tolerance"] for dataset in datasets),
            "all_projected_bounds_match": all(dataset["correctness"]["projected_bounds_match"] for dataset in datasets),
            "all_clip_matches": all(
                dataset["correctness"]["clip"] is None or dataset["correctness"]["clip"]["feature_count_match"]
                for dataset in datasets
            ),
            "all_dissolve_matches": all(
                dataset["correctness"]["dissolve"] is None or (
                    dataset["correctness"]["dissolve"]["feature_count_match"] and dataset["correctness"]["dissolve"]["bands_match"]
                )
                for dataset in datasets
            ),
            "all_spatial_joins_match": all(
                dataset["correctness"]["spatial_join"] is None or dataset["correctness"]["spatial_join"]["pair_match"]
                for dataset in datasets
            ),
        },
        "datasets": datasets,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare Geoprompt results and runtime against Shapely and GeoPandas.")
    parser.add_argument("--input-path", type=Path, default=None, help="Optional single input fixture to compare. If omitted, the built-in corpus is used.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Output directory for the comparison report.")
    parser.add_argument("--tolerance", type=float, default=1e-7, help="Absolute tolerance for correctness checks.")
    parser.add_argument("--crs", type=str, default="EPSG:4326", help="Source CRS for a custom single input fixture.")
    parser.add_argument("--join-path", type=Path, default=None, help="Optional polygon region fixture for a custom single input comparison.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_comparison_report(
        input_path=args.input_path,
        output_dir=args.output_dir,
        tolerance=args.tolerance,
        crs=args.crs,
        join_path=args.join_path,
    )
    report_path = write_json(args.output_dir / "geoprompt_comparison_report.json", report)
    print(f"Wrote GeoPrompt comparison report to {report_path}")


__all__ = ["build_comparison_report", "main"]


if __name__ == "__main__":
    main()