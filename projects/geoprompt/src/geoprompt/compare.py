from __future__ import annotations

import argparse
import importlib
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .frame import GeoPromptFrame
from .geometry import geometry_centroid
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


def _dataset_report(case: CorpusCase, tolerance: float) -> dict[str, Any]:
    case = _materialize_case(case)
    geopandas, shape, box = _load_compare_dependencies()
    projection_tolerance = max(tolerance, 1e-6)

    frame = _frame_from_case(case)
    records = frame.to_records()
    feature_ids = [str(record.get("site_id", index)) for index, record in enumerate(records)]
    geoprompt_lengths = frame.geometry_lengths()
    geoprompt_areas = frame.geometry_areas()
    geoprompt_centroids = [geometry_centroid(record["geometry"]) for record in records]

    shapely_geometries = [shape(_as_geojson_geometry(record["geometry"])) for record in records]
    geopandas_frame = geopandas.GeoDataFrame(
        [{key: value for key, value in record.items() if key != "geometry"} for record in records],
        geometry=shapely_geometries,
        crs=case.crs,
    )

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

    join_report: dict[str, Any] | None = None
    clip_report: dict[str, Any] | None = None
    dissolve_report: dict[str, Any] | None = None
    regions = _join_frame_from_case(case)
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

    benchmarks: list[dict[str, Any]] = []
    for operation, func in [
        (f"{case.name}.geoprompt.geometry_metrics", lambda: (frame.geometry_lengths(), frame.geometry_areas(), frame.bounds())),
        (f"{case.name}.reference.geometry_metrics", lambda: ([geometry.length for geometry in shapely_geometries], [geometry.area for geometry in shapely_geometries], geopandas_frame.total_bounds)),
        (f"{case.name}.geoprompt.nearest_neighbors", lambda: frame.nearest_neighbors(k=1)),
        (f"{case.name}.reference.nearest_neighbors", lambda: _nearest_neighbors_reference(feature_ids, [geometry.centroid for geometry in shapely_geometries])),
        (f"{case.name}.geoprompt.query_bounds", lambda: frame.query_bounds(min_x=min_x, min_y=min_y, max_x=max_x, max_y=max_y)),
        (f"{case.name}.reference.query_bounds", lambda: geopandas_frame.loc[geopandas_frame.geometry.intersects(box(min_x, min_y, max_x, max_y))]),
        (f"{case.name}.geoprompt.to_crs", lambda: frame.to_crs("EPSG:3857")),
        (f"{case.name}.reference.to_crs", lambda: geopandas_frame.to_crs("EPSG:3857")),
    ]:
        benchmark, _ = _benchmark(operation, func)
        benchmarks.append(benchmark)

    if regions is not None:
        region_geometries = [shape(_as_geojson_geometry(record["geometry"])) for record in regions.to_records()]
        region_ids = [str(record["region_id"]) for record in regions.to_records()]
        benchmark, _ = _benchmark(
            f"{case.name}.geoprompt.spatial_join",
            lambda: regions.spatial_join(frame, predicate="intersects"),
        )
        benchmarks.append(benchmark)
        benchmark, _ = _benchmark(
            f"{case.name}.reference.spatial_join",
            lambda: [
                f"{region_id}->{feature_id}"
                for region_id, region_geometry in zip(region_ids, region_geometries, strict=True)
                for feature_id, feature_geometry in zip(feature_ids, shapely_geometries, strict=True)
                if region_geometry.intersects(feature_geometry)
            ],
        )
        benchmarks.append(benchmark)
        benchmark, _ = _benchmark(
            f"{case.name}.geoprompt.clip",
            lambda: frame.clip(regions),
        )
        benchmarks.append(benchmark)
        shapely_ops = importlib.import_module("shapely.ops")
        mask_union = shapely_ops.unary_union([geometry_to_shapely(record["geometry"]) for record in regions.to_records()])
        benchmark, _ = _benchmark(
            f"{case.name}.reference.clip",
            lambda: [
                geometry
                for feature_geometry in shapely_geometries
                for geometry in geometry_from_shapely(feature_geometry.intersection(mask_union))
            ],
        )
        benchmarks.append(benchmark)
        benchmark, _ = _benchmark(
            f"{case.name}.geoprompt.dissolve",
            lambda: regions.dissolve(by="region_band", aggregations={"region_name": "count"}),
        )
        benchmarks.append(benchmark)
        benchmark, _ = _benchmark(
            f"{case.name}.reference.dissolve",
            lambda: geopandas.GeoDataFrame(
                [{key: value for key, value in record.items() if key != "geometry"} for record in regions.to_records()],
                geometry=region_geometries,
                crs=case.crs,
            ).dissolve(by="region_band", aggfunc={"region_name": "count"}).reset_index(),
        )
        benchmarks.append(benchmark)

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
        "benchmarks": benchmarks,
    }


def build_comparison_report(
    input_path: Path | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    tolerance: float = 1e-7,
    crs: str = "EPSG:4326",
    join_path: Path | None = None,
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
    datasets = [_dataset_report(case, tolerance=tolerance) for case in cases]

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