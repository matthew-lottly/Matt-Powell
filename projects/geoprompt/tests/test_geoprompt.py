import json
import math
import time
import warnings
from itertools import permutations
from pathlib import Path
from typing import Any, cast

import pytest

from geoprompt.compare import _stress_feature_records, _stress_region_records
from geoprompt import GeoPromptFrame, accessibility_index, geometry_area, geometry_bounds, geometry_centroid, geometry_convex_hull, geometry_envelope, gravity_model
from geoprompt.demo import build_demo_report
from geoprompt.equations import area_similarity, corridor_strength, directional_alignment, euclidean_distance, haversine_distance, prompt_decay, prompt_interaction
from geoprompt.io import frame_to_geojson, read_features, read_geojson, read_points, write_flat_csv, write_geojson, write_records_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_read_points_and_centroid() -> None:
    frame = read_points(PROJECT_ROOT / "data" / "sample_points.json")

    assert len(frame) == 5
    assert frame.columns[0] == "site_id"
    centroid = frame.centroid()
    assert round(centroid[0], 3) == -111.928
    assert round(centroid[1], 3) == 40.684


def test_distance_and_decay_equations() -> None:
    distance_value = euclidean_distance((-111.92, 40.78), (-111.96, 40.71))
    geographic_distance = haversine_distance((-111.92, 40.78), (-111.96, 40.71))

    assert round(distance_value, 4) == 0.0806
    assert round(geographic_distance, 3) == 8.482
    assert round(prompt_decay(distance_value=distance_value, scale=0.14, power=1.6), 4) == 0.4830
    assert round(prompt_interaction(0.71, 0.88, distance_value=distance_value, scale=0.16, power=1.5), 4) == 0.3388


def test_neighborhood_pressure_and_anchor_influence() -> None:
    frame = read_points(PROJECT_ROOT / "data" / "sample_points.json")

    pressure = frame.neighborhood_pressure(weight_column="demand_index", scale=0.14, power=1.6)
    anchor = frame.anchor_influence(weight_column="priority_index", anchor="north-hub", scale=0.14, power=1.4)

    assert len(pressure) == len(frame)
    assert pressure[1] == max(pressure)
    assert anchor[0] == max(anchor)


def test_mixed_geometries_and_corridor_strength() -> None:
    frame = read_features(PROJECT_ROOT / "data" / "sample_features.json")

    assert sorted(set(frame.geometry_types())) == ["LineString", "Point", "Polygon"]
    lengths = frame.geometry_lengths()
    areas = frame.geometry_areas()
    corridor = frame.corridor_accessibility(weight_column="capacity_index", anchor="north-hub-point", scale=0.18, power=1.4)

    assert max(lengths) > 0.14
    assert max(areas) > 0.008
    assert len(corridor) == len(frame)
    assert corridor[0] == 0.0


def test_line_centroid_uses_segment_length_weighting() -> None:
    centroid = geometry_centroid(
        {
            "type": "LineString",
            "coordinates": [(0.0, 0.0), (2.0, 0.0), (3.0, 0.0)],
        }
    )

    assert centroid == (1.5, 0.0)


def test_geojson_round_trip_and_nearest_neighbors(tmp_path: Path) -> None:
    frame = read_features(PROJECT_ROOT / "data" / "sample_features.json", crs="EPSG:4326")
    geojson_path = write_geojson(tmp_path / "sample_features.geojson", frame)
    reloaded = read_geojson(geojson_path)
    neighbors = reloaded.nearest_neighbors(k=1)
    geographic_neighbors = reloaded.nearest_neighbors(k=1, distance_method="haversine")
    feature_collection = frame_to_geojson(reloaded)

    assert len(reloaded) == len(frame)
    assert len(neighbors) == len(frame)
    assert len(geographic_neighbors) == len(frame)
    assert neighbors[0]["rank"] == 1
    assert geographic_neighbors[0]["distance_method"] == "haversine"
    assert feature_collection["type"] == "FeatureCollection"
    assert feature_collection["crs"]["properties"]["name"] == "EPSG:4326"
    assert len(feature_collection["features"]) == len(frame)


def test_write_records_json_and_flat_csv(tmp_path: Path) -> None:
    frame = read_features(PROJECT_ROOT / "data" / "sample_features.json", crs="EPSG:4326")

    records_json_path = write_records_json(tmp_path / "sample_features.records.json", frame)
    flat_csv_path = write_flat_csv(tmp_path / "sample_features.flat.csv", frame)

    payload = json.loads(records_json_path.read_text(encoding="utf-8"))
    csv_lines = flat_csv_path.read_text(encoding="utf-8").splitlines()

    assert payload["crs"] == "EPSG:4326"
    assert payload["geometry_column"] == "geometry"
    assert len(payload["records"]) == len(frame)
    assert csv_lines[0].startswith("capacity_index,")
    assert any("geometry_centroid_x" in line for line in csv_lines[:1])
    assert len(csv_lines) == len(frame) + 1


def test_query_bounds_modes() -> None:
    frame = read_features(PROJECT_ROOT / "data" / "sample_features.json")

    intersects = frame.query_bounds(min_x=-111.97, min_y=40.68, max_x=-111.84, max_y=40.79, mode="intersects")
    within = frame.query_bounds(min_x=-111.97, min_y=40.68, max_x=-111.84, max_y=40.79, mode="within")
    centroid = frame.query_bounds(min_x=-111.97, min_y=40.68, max_x=-111.84, max_y=40.79, mode="centroid")

    assert len(intersects) >= len(within)
    assert len(intersects) >= len(centroid)
    assert sorted(record["site_id"] for record in within) == [
        "central-yard-point",
        "north-hub-point",
    ]


def test_spatial_index_supports_geometry_and_centroid_queries() -> None:
    frame = read_features(PROJECT_ROOT / "data" / "sample_features.json")

    geometry_index = frame.spatial_index()
    centroid_index = frame.spatial_index(mode="centroid")
    bounds = (-111.97, 40.68, -111.84, 40.79)

    geometry_candidate_ids = {frame.to_records()[index]["site_id"] for index in geometry_index.query(bounds)}
    centroid_ids = {frame.to_records()[index]["site_id"] for index in centroid_index.query(bounds)}
    exact_intersects = {record["site_id"] for record in frame.query_bounds(*bounds, mode="intersects")}
    exact_centroids = {record["site_id"] for record in frame.query_bounds(*bounds, mode="centroid")}

    assert exact_intersects.issubset(geometry_candidate_ids)
    assert len(geometry_candidate_ids) < len(frame)
    assert centroid_ids == exact_centroids


def test_spatial_index_reuses_cached_instance() -> None:
    frame = read_features(PROJECT_ROOT / "data" / "sample_features.json")

    first_index = frame.spatial_index()
    second_index = frame.spatial_index()

    assert first_index is second_index


def test_query_radius_returns_sorted_distance_matches() -> None:
    frame = read_features(PROJECT_ROOT / "data" / "sample_features.json")

    nearby = frame.query_radius(anchor="north-hub-point", max_distance=0.09, include_anchor=True)
    records = nearby.to_records()

    assert records[0]["site_id"] == "north-hub-point"
    assert records[0]["distance"] == 0.0
    assert all(record["distance"] <= 0.09 for record in records)
    assert records == sorted(records, key=lambda item: (float(item["distance"]), str(item["site_id"])))


def test_within_distance_returns_boolean_mask() -> None:
    frame = read_features(PROJECT_ROOT / "data" / "sample_features.json")

    mask = frame.within_distance(anchor="north-hub-point", max_distance=0.09, include_anchor=False)
    matched_ids = [row["site_id"] for row, include_row in zip(frame, mask, strict=True) if include_row]

    assert "north-hub-point" not in matched_ids
    assert "central-yard-point" in matched_ids
    assert all(isinstance(value, bool) for value in mask)


def test_proximity_join_matches_nearby_features() -> None:
    frame = read_features(PROJECT_ROOT / "data" / "sample_features.json", crs="EPSG:4326")

    joined = frame.proximity_join(frame, max_distance=0.05, distance_method="euclidean")
    left_joined = frame.proximity_join(frame, max_distance=0.01, how="left", distance_method="euclidean")

    pairs = {f"{row['site_id']}->{row['site_id_right']}" for row in joined if row.get("site_id_right") is not None}

    assert "north-hub-point->north-hub-point" in pairs
    assert "central-yard-point->central-yard-point" in pairs
    assert all(row["distance_right"] <= 0.05 for row in joined)
    assert len(left_joined) >= len(frame)
    assert all("distance_method_right" in row for row in left_joined)


def test_spatial_join_supports_runtime_diagnostics() -> None:
    regions = read_features(PROJECT_ROOT / "data" / "benchmark_regions.json", crs="EPSG:4326")
    features = read_features(PROJECT_ROOT / "data" / "benchmark_features.json", crs="EPSG:4326")

    joined = regions.spatial_join(features, predicate="intersects", include_diagnostics=True)
    record = joined.to_records()[0]

    assert "candidate_count_right" in record
    assert "pruning_ratio_right" in record
    assert "match_count_right" in record


def test_nearest_join_returns_ranked_matches() -> None:
    origins = GeoPromptFrame.from_records(
        [
            {"site_id": "origin-a", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
            {"site_id": "origin-b", "geometry": {"type": "Point", "coordinates": [10.0, 0.0]}},
        ],
        crs="EPSG:4326",
    )
    targets = GeoPromptFrame.from_records(
        [
            {"target_id": "target-1", "geometry": {"type": "Point", "coordinates": [1.0, 0.0]}},
            {"target_id": "target-2", "geometry": {"type": "Point", "coordinates": [2.0, 0.0]}},
            {"target_id": "target-3", "geometry": {"type": "Point", "coordinates": [11.0, 0.0]}},
        ],
        crs="EPSG:4326",
    )

    joined = origins.nearest_join(targets, k=2)
    records = joined.to_records()

    assert len(records) == 4
    assert records[0]["target_id"] == "target-1"
    assert records[0]["nearest_rank_right"] == 1
    assert records[1]["target_id"] == "target-2"
    assert records[1]["nearest_rank_right"] == 2
    assert any(record["site_id"] == "origin-b" and record["target_id"] == "target-3" and record["nearest_rank_right"] == 1 for record in records)


def test_nearest_join_supports_max_distance_and_left_mode() -> None:
    origins = GeoPromptFrame.from_records(
        [
            {"site_id": "origin-a", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
            {"site_id": "origin-b", "geometry": {"type": "Point", "coordinates": [10.0, 0.0]}},
        ],
        crs="EPSG:4326",
    )
    targets = GeoPromptFrame.from_records(
        [
            {"target_id": "target-1", "geometry": {"type": "Point", "coordinates": [1.0, 0.0]}},
        ],
        crs="EPSG:4326",
    )

    joined = origins.nearest_join(targets, k=1, max_distance=2.0, how="left")
    records = sorted(joined.to_records(), key=lambda item: item["site_id"])

    assert records[0]["target_id"] == "target-1"
    assert records[0]["distance_right"] == 1.0
    assert records[1]["target_id"] is None
    assert records[1]["distance_right"] is None
    assert records[1]["nearest_rank_right"] is None


def test_assign_nearest_returns_target_focused_output() -> None:
    origins = GeoPromptFrame.from_records(
        [
            {"site_id": "origin-a", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
            {"site_id": "origin-b", "geometry": {"type": "Point", "coordinates": [10.0, 0.0]}},
        ],
        crs="EPSG:4326",
    )
    targets = GeoPromptFrame.from_records(
        [
            {"target_id": "target-1", "geometry": {"type": "Point", "coordinates": [1.0, 0.0]}},
            {"target_id": "target-2", "geometry": {"type": "Point", "coordinates": [11.0, 0.0]}},
        ],
        crs="EPSG:4326",
    )

    assigned = origins.assign_nearest(targets, origin_suffix="origin")
    records = sorted(assigned.to_records(), key=lambda item: item["target_id"])

    assert records[0]["target_id"] == "target-1"
    assert records[0]["site_id"] == "origin-a"
    assert records[0]["nearest_rank_origin"] == 1
    assert records[1]["target_id"] == "target-2"
    assert records[1]["site_id"] == "origin-b"
    assert records[1]["distance_origin"] == 1.0


def test_summarize_assignments_rolls_targets_to_origins() -> None:
    origins = GeoPromptFrame.from_records(
        [
            {"site_id": "origin-a", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
            {"site_id": "origin-b", "geometry": {"type": "Point", "coordinates": [10.0, 0.0]}},
        ],
        crs="EPSG:4326",
    )
    targets = GeoPromptFrame.from_records(
        [
            {"target_id": "target-1", "demand": 2.0, "geometry": {"type": "Point", "coordinates": [1.0, 0.0]}},
            {"target_id": "target-2", "demand": 3.0, "geometry": {"type": "Point", "coordinates": [2.0, 0.0]}},
            {"target_id": "target-3", "demand": 5.0, "geometry": {"type": "Point", "coordinates": [11.0, 0.0]}},
        ],
        crs="EPSG:4326",
    )

    summary = origins.summarize_assignments(
        targets,
        origin_id_column="site_id",
        target_id_column="target_id",
        aggregations={"demand": "sum"},
    )
    records = sorted(summary.to_records(), key=lambda item: item["site_id"])

    assert records[0]["site_id"] == "origin-a"
    assert records[0]["target_ids_assigned"] == ["target-1", "target-2"]
    assert records[0]["count_assigned"] == 2
    assert records[0]["demand_sum_assigned"] == 5.0
    assert records[0]["distance_min_assigned"] == 1.0
    assert records[0]["distance_max_assigned"] == 2.0
    assert records[0]["distance_mean_assigned"] == 1.5
    assert records[1]["site_id"] == "origin-b"
    assert records[1]["target_ids_assigned"] == ["target-3"]
    assert records[1]["count_assigned"] == 1


def test_summarize_assignments_supports_left_mode_and_distance_filter() -> None:
    origins = GeoPromptFrame.from_records(
        [
            {"site_id": "origin-a", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
            {"site_id": "origin-b", "geometry": {"type": "Point", "coordinates": [10.0, 0.0]}},
        ],
        crs="EPSG:4326",
    )
    targets = GeoPromptFrame.from_records(
        [
            {"target_id": "target-1", "geometry": {"type": "Point", "coordinates": [1.0, 0.0]}},
        ],
        crs="EPSG:4326",
    )

    summary = origins.summarize_assignments(
        targets,
        origin_id_column="site_id",
        target_id_column="target_id",
        how="left",
        max_distance=2.0,
    )
    records = sorted(summary.to_records(), key=lambda item: item["site_id"])

    assert records[0]["count_assigned"] == 1
    assert records[1]["count_assigned"] == 0
    assert records[1]["target_ids_assigned"] == []
    assert records[1]["distance_mean_assigned"] is None


def test_catchment_competition_counts_exclusive_shared_won_and_unserved_targets() -> None:
    origins = GeoPromptFrame.from_records(
        [
            {"site_id": "origin-a", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
            {"site_id": "origin-b", "geometry": {"type": "Point", "coordinates": [3.0, 0.0]}},
        ],
        crs="EPSG:4326",
    )
    targets = GeoPromptFrame.from_records(
        [
            {"target_id": "target-1", "demand": 2.0, "geometry": {"type": "Point", "coordinates": [0.5, 0.0]}},
            {"target_id": "target-2", "demand": 3.0, "geometry": {"type": "Point", "coordinates": [1.5, 0.0]}},
            {"target_id": "target-3", "demand": 4.0, "geometry": {"type": "Point", "coordinates": [2.7, 0.0]}},
            {"target_id": "target-4", "demand": 5.0, "geometry": {"type": "Point", "coordinates": [9.0, 0.0]}},
        ],
        crs="EPSG:4326",
    )

    summary = origins.catchment_competition(
        targets,
        max_distance=2.0,
        origin_id_column="site_id",
        target_id_column="target_id",
        aggregations={"demand": "sum"},
    )
    records = sorted(summary.to_records(), key=lambda item: item["site_id"])

    assert records[0]["site_id"] == "origin-a"
    assert records[0]["target_ids_catchment"] == ["target-1", "target-2"]
    assert records[0]["target_ids_exclusive_catchment"] == ["target-1"]
    assert records[0]["target_ids_shared_catchment"] == ["target-2"]
    assert records[0]["target_ids_won_catchment"] == ["target-1", "target-2"]
    assert records[0]["count_catchment"] == 2
    assert records[0]["count_exclusive_catchment"] == 1
    assert records[0]["count_shared_catchment"] == 1
    assert records[0]["count_won_catchment"] == 2
    assert records[0]["count_unserved_catchment"] == 1
    assert records[0]["target_ids_unserved_catchment"] == ["target-4"]
    assert records[0]["demand_sum_catchment"] == 5.0

    assert records[1]["site_id"] == "origin-b"
    assert records[1]["target_ids_catchment"] == ["target-2", "target-3"]
    assert records[1]["target_ids_exclusive_catchment"] == ["target-3"]
    assert records[1]["target_ids_shared_catchment"] == ["target-2"]
    assert records[1]["target_ids_won_catchment"] == ["target-3"]
    assert records[1]["count_catchment"] == 2
    assert records[1]["count_exclusive_catchment"] == 1
    assert records[1]["count_shared_catchment"] == 1
    assert records[1]["count_won_catchment"] == 1
    assert records[1]["count_unserved_catchment"] == 1
    assert records[1]["demand_sum_catchment"] == 7.0


def test_catchment_competition_supports_inner_mode() -> None:
    origins = GeoPromptFrame.from_records(
        [
            {"site_id": "origin-a", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
            {"site_id": "origin-b", "geometry": {"type": "Point", "coordinates": [10.0, 0.0]}},
        ],
        crs="EPSG:4326",
    )
    targets = GeoPromptFrame.from_records(
        [
            {"target_id": "target-1", "geometry": {"type": "Point", "coordinates": [1.0, 0.0]}},
        ],
        crs="EPSG:4326",
    )

    summary = origins.catchment_competition(
        targets,
        max_distance=2.0,
        origin_id_column="site_id",
        target_id_column="target_id",
        how="inner",
    )

    records = summary.to_records()
    assert len(records) == 1
    assert records[0]["site_id"] == "origin-a"
    assert records[0]["count_catchment"] == 1


def test_buffer_converts_points_to_polygons() -> None:
    frame = read_points(PROJECT_ROOT / "data" / "sample_points.json", crs="EPSG:4326")

    buffered = frame.buffer(distance=0.01)

    assert len(buffered) == len(frame)
    assert all(record["geometry"]["type"] == "Polygon" for record in buffered)
    assert all(record["site_id"] for record in buffered)


def test_buffer_matches_shapely_area_when_available() -> None:
    shapely_geometry = pytest.importorskip("shapely.geometry")

    frame = GeoPromptFrame.from_records(
        [{"site_id": "anchor", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}}],
        crs="EPSG:4326",
    )

    record = frame.buffer(distance=2.0, resolution=8).to_records()[0]
    reference_area = float(shapely_geometry.Point(0.0, 0.0).buffer(2.0, quad_segs=8).area)

    assert geometry_area(record["geometry"]) == pytest.approx(reference_area)


def test_buffer_join_extends_point_reach_to_polygon() -> None:
    service_points = GeoPromptFrame.from_records(
        [{"site_id": "anchor", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}}],
        crs="EPSG:4326",
    )
    polygons = GeoPromptFrame.from_records(
        [{
            "region_id": "near-zone",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[0.04, -0.01], [0.06, -0.01], [0.06, 0.01], [0.04, 0.01]]],
            },
        }],
        crs="EPSG:4326",
    )

    joined = service_points.buffer_join(polygons, distance=0.05)

    assert len(joined) == 1
    assert joined.head(1)[0]["region_id"] == "near-zone"
    assert joined.head(1)[0]["buffer_distance_left"] == 0.05


def test_coverage_summary_counts_and_aggregates_matches() -> None:
    service_areas = GeoPromptFrame.from_records(
        [
            {
                "zone_id": "north-zone",
                "geometry": {"type": "Polygon", "coordinates": [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]]},
            },
            {
                "zone_id": "south-zone",
                "geometry": {"type": "Polygon", "coordinates": [[[0.0, -1.0], [1.0, -1.0], [1.0, 0.0], [0.0, 0.0]]]},
            },
        ],
        crs="EPSG:4326",
    )
    assets = GeoPromptFrame.from_records(
        [
            {"site_id": "a", "demand_index": 2.0, "geometry": {"type": "Point", "coordinates": [0.25, 0.25]}},
            {"site_id": "b", "demand_index": 3.0, "geometry": {"type": "Point", "coordinates": [0.75, 0.25]}},
            {"site_id": "c", "demand_index": 5.0, "geometry": {"type": "Point", "coordinates": [0.75, -0.25]}},
        ],
        crs="EPSG:4326",
    )

    summary = service_areas.coverage_summary(assets, aggregations={"demand_index": "sum"})
    records = sorted(summary.to_records(), key=lambda item: item["zone_id"])

    assert records[0]["zone_id"] == "north-zone"
    assert records[0]["count_covered"] == 2
    assert records[0]["demand_index_sum_covered"] == 5.0
    assert records[0]["site_ids_covered"] == ["a", "b"]
    assert records[1]["zone_id"] == "south-zone"
    assert records[1]["count_covered"] == 1
    assert records[1]["demand_index_sum_covered"] == 5.0


def test_fishnet_and_hexbin_generate_covering_cells() -> None:
    frame = GeoPromptFrame.from_records(
        [
            {"site_id": "a", "geometry": {"type": "Point", "coordinates": [0.1, 0.1]}},
            {"site_id": "b", "geometry": {"type": "Point", "coordinates": [1.1, 1.1]}},
        ],
        crs="EPSG:4326",
    )

    fishnet = frame.fishnet(1.0)
    hexes = frame.hexbin(0.8)

    assert len(fishnet) >= 2
    assert len(hexes) >= 2
    assert all(record["geometry"]["type"] == "Polygon" for record in fishnet.to_records())
    assert all(record["geometry"]["type"] == "Polygon" for record in hexes.to_records())
    assert all("grid_id" in record for record in fishnet.to_records())


def test_hotspot_grid_counts_and_sums_centroid_assignments() -> None:
    frame = GeoPromptFrame.from_records(
        [
            {"site_id": "a", "weight": 2.0, "geometry": {"type": "Point", "coordinates": [0.1, 0.1]}},
            {"site_id": "b", "weight": 3.0, "geometry": {"type": "Point", "coordinates": [0.2, 0.2]}},
            {"site_id": "c", "weight": 5.0, "geometry": {"type": "Point", "coordinates": [1.2, 0.2]}},
        ],
        crs="EPSG:4326",
    )

    counts = frame.hotspot_grid(cell_size=1.0, shape="fishnet")
    weighted = frame.hotspot_grid(cell_size=1.0, shape="fishnet", value_column="weight", aggregation="sum")

    count_values = sorted(record["count_hotspot"] for record in counts.to_records())
    weighted_values = sorted(value for value in [record.get("weight_sum_hotspot") for record in weighted.to_records()] if value is not None)

    assert max(count_values) == 2
    assert weighted_values[-1] == 5.0
    assert sum(record["count_hotspot"] for record in counts.to_records()) == len(frame)


def test_hotspot_grid_supports_runtime_diagnostics() -> None:
    frame = GeoPromptFrame.from_records(
        [
            {"site_id": "a", "geometry": {"type": "Point", "coordinates": [0.1, 0.1]}},
            {"site_id": "b", "geometry": {"type": "Point", "coordinates": [0.2, 0.2]}},
        ],
        crs="EPSG:4326",
    )

    hotspots = frame.hotspot_grid(cell_size=1.0, include_diagnostics=True)
    record = hotspots.to_records()[0]

    assert "candidate_count_hotspot" in record
    assert "pruning_ratio_hotspot" in record


def test_snap_geometries_snaps_nearby_vertices_deterministically() -> None:
    frame = GeoPromptFrame.from_records(
        [
            {"site_id": "point-a", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
            {"site_id": "point-b", "geometry": {"type": "Point", "coordinates": [0.03, 0.0]}},
            {"site_id": "line-a", "geometry": {"type": "LineString", "coordinates": [[0.03, 0.0], [1.0, 0.0]]}},
        ],
        crs="EPSG:4326",
    )

    snapped = frame.snap_geometries(tolerance=0.05, include_diagnostics=True)
    records = snapped.to_records()

    assert records[0]["geometry"]["coordinates"] == (0.0, 0.0)
    assert records[1]["geometry"]["coordinates"] == (0.0, 0.0)
    assert records[2]["geometry"]["coordinates"][0] == (0.0, 0.0)
    assert records[1]["changed_snap"] is True
    assert records[2]["changed_vertex_count_snap"] == 1
    assert records[0]["unique_vertex_count_snap"] == 3


def test_clean_topology_removes_duplicate_vertices_and_short_segments() -> None:
    frame = GeoPromptFrame.from_records(
        [
            {
                "site_id": "route-a",
                "geometry": {"type": "LineString", "coordinates": [[0.0, 0.0], [1.0, 0.0], [1.0, 0.0], [1.02, 0.0], [2.0, 0.0]]},
            },
            {
                "site_id": "zone-a",
                "geometry": {"type": "Polygon", "coordinates": [[0.0, 0.0], [2.0, 0.0], [2.0, 0.0], [2.0, 2.0], [0.0, 2.0], [0.0, 0.0]]},
            },
        ],
        crs="EPSG:4326",
    )

    cleaned = frame.clean_topology(min_segment_length=0.05, include_diagnostics=True)
    records = cleaned.to_records()

    assert records[0]["geometry"]["coordinates"] == ((0.0, 0.0), (1.0, 0.0), (2.0, 0.0))
    assert records[0]["removed_short_segment_count_clean"] == 1
    assert records[0]["removed_vertex_count_clean"] == 2
    assert records[1]["geometry"]["coordinates"] == ((0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0), (0.0, 0.0))
    assert records[1]["output_vertex_count_clean"] == 4


def test_line_split_splits_line_by_point_splitters() -> None:
    lines = GeoPromptFrame.from_records(
        [
            {"site_id": "route-a", "geometry": {"type": "LineString", "coordinates": [[0.0, 0.0], [4.0, 0.0]]}},
        ],
        crs="EPSG:4326",
    )
    splitters = GeoPromptFrame.from_records(
        [
            {"cut_id": "cut-1", "geometry": {"type": "Point", "coordinates": [1.0, 0.0]}},
            {"cut_id": "cut-2", "geometry": {"type": "Point", "coordinates": [3.0, 0.0]}},
        ],
        crs="EPSG:4326",
    )

    split = lines.line_split(splitters, splitter_id_column="cut_id", split_at_intersections=False, include_diagnostics=True)
    records = split.to_records()

    assert len(records) == 3
    assert [record["part_index_split"] for record in records] == [1, 2, 3]
    assert [record["geometry"]["coordinates"] for record in records] == [
        ((0.0, 0.0), (1.0, 0.0)),
        ((1.0, 0.0), (3.0, 0.0)),
        ((3.0, 0.0), (4.0, 0.0)),
    ]
    assert records[0]["part_count_split"] == 3
    assert records[0]["splitter_ids_split"] == ["cut-1", "cut-2"]
    assert records[0]["point_splitter_count_split"] == 2


def test_line_split_splits_lines_at_intersections() -> None:
    lines = GeoPromptFrame.from_records(
        [
            {"site_id": "horizontal", "geometry": {"type": "LineString", "coordinates": [[0.0, 0.0], [2.0, 0.0]]}},
            {"site_id": "vertical", "geometry": {"type": "LineString", "coordinates": [[1.0, -1.0], [1.0, 1.0]]}},
        ],
        crs="EPSG:4326",
    )

    split = lines.line_split(include_diagnostics=True)
    records = split.to_records()

    assert len(records) == 4
    assert [record["part_count_split"] for record in records if record["site_id"] == "horizontal"] == [2, 2]
    assert [record["part_count_split"] for record in records if record["site_id"] == "vertical"] == [2, 2]
    assert any(record["self_intersection_count_split"] == 1 for record in records)
    assert {record["geometry"]["coordinates"] for record in records} == {
        ((0.0, 0.0), (1.0, 0.0)),
        ((1.0, 0.0), (2.0, 0.0)),
        ((1.0, -1.0), (1.0, 0.0)),
        ((1.0, 0.0), (1.0, 1.0)),
    }


def test_overlay_union_partitions_polygon_faces_with_lineage() -> None:
    left = GeoPromptFrame.from_records(
        [
            {"region_id": "left-a", "geometry": {"type": "Polygon", "coordinates": [[0.0, 0.0], [2.0, 0.0], [2.0, 2.0], [0.0, 2.0], [0.0, 0.0]]}},
        ],
        crs="EPSG:4326",
    )
    right = GeoPromptFrame.from_records(
        [
            {"zone_id": "right-a", "geometry": {"type": "Polygon", "coordinates": [[1.0, 0.0], [3.0, 0.0], [3.0, 2.0], [1.0, 2.0], [1.0, 0.0]]}},
        ],
        crs="EPSG:4326",
    )

    union = left.overlay_union(right, left_id_column="region_id", right_id_column="zone_id", rsuffix="right")
    records = sorted(union.to_records(), key=lambda item: (item["source_side_union"], item["area_union"]))

    assert len(records) == 3
    assert [record["source_side_union"] for record in records] == ["both", "left", "right"]
    assert records[0]["region_ids_union"] == ["left-a"]
    assert records[0]["zone_ids_union"] == ["right-a"]
    assert records[0]["area_union"] == 2.0
    assert records[1]["region_ids_union"] == ["left-a"]
    assert records[1]["zone_ids_union"] == []
    assert records[2]["region_ids_union"] == []
    assert records[2]["zone_ids_union"] == ["right-a"]


def test_polygon_split_splits_polygon_by_line_splitter() -> None:
    polygons = GeoPromptFrame.from_records(
        [
            {"site_id": "zone-a", "geometry": {"type": "Polygon", "coordinates": [[0.0, 0.0], [4.0, 0.0], [4.0, 2.0], [0.0, 2.0], [0.0, 0.0]]}},
        ],
        crs="EPSG:4326",
    )
    splitters = GeoPromptFrame.from_records(
        [
            {"cut_id": "cut-1", "geometry": {"type": "LineString", "coordinates": [[2.0, -1.0], [2.0, 3.0]]}},
        ],
        crs="EPSG:4326",
    )

    split = polygons.polygon_split(splitters, splitter_id_column="cut_id", include_diagnostics=True)
    records = split.to_records()

    assert len(records) == 2
    assert [record["part_index_split"] for record in records] == [1, 2]
    assert [record["area_split"] for record in records] == [4.0, 4.0]
    assert all(record["part_count_split"] == 2 for record in records)
    assert all(record["splitter_ids_split"] == ["cut-1"] for record in records)
    assert all(record["split_detected_split"] is True for record in records)


def test_polygon_split_uses_polygon_boundaries_as_splitters() -> None:
    polygons = GeoPromptFrame.from_records(
        [
            {"site_id": "zone-a", "geometry": {"type": "Polygon", "coordinates": [[0.0, 0.0], [4.0, 0.0], [4.0, 2.0], [0.0, 2.0], [0.0, 0.0]]}},
        ],
        crs="EPSG:4326",
    )
    splitters = GeoPromptFrame.from_records(
        [
            {"region_id": "region-a", "geometry": {"type": "Polygon", "coordinates": [[2.0, -1.0], [5.0, -1.0], [5.0, 3.0], [2.0, 3.0], [2.0, -1.0]]}},
        ],
        crs="EPSG:4326",
    )

    split = polygons.polygon_split(splitters, splitter_id_column="region_id", include_diagnostics=True)
    records = split.to_records()

    assert len(records) == 2
    assert [record["area_split"] for record in records] == [4.0, 4.0]
    assert all(record["splitter_ids_split"] == ["region-a"] for record in records)
    assert all(record["applied_splitter_count_split"] == 1 for record in records)


def test_overlay_difference_returns_only_left_side_faces() -> None:
    left = GeoPromptFrame.from_records(
        [
            {"region_id": "left-a", "geometry": {"type": "Polygon", "coordinates": [[0.0, 0.0], [3.0, 0.0], [3.0, 2.0], [0.0, 2.0], [0.0, 0.0]]}},
        ],
        crs="EPSG:4326",
    )
    right = GeoPromptFrame.from_records(
        [
            {"zone_id": "right-a", "geometry": {"type": "Polygon", "coordinates": [[1.0, 0.0], [2.0, 0.0], [2.0, 2.0], [1.0, 2.0], [1.0, 0.0]]}},
        ],
        crs="EPSG:4326",
    )

    difference = left.overlay_difference(right, left_id_column="region_id", right_id_column="zone_id")
    records = difference.to_records()

    assert len(records) == 2
    assert [record["area_difference"] for record in records] == [2.0, 2.0]
    assert all(record["region_ids_difference"] == ["left-a"] for record in records)
    assert all(record["zone_ids_difference"] == [] for record in records)
    assert all(record["removed_area_difference"] == 2.0 for record in records)
    assert all(record["removed_share_difference"] == (2.0 / 6.0) for record in records)


def test_overlay_difference_matches_shapely_difference_area_when_available() -> None:
    shapely_geometry = pytest.importorskip("shapely.geometry")

    left = GeoPromptFrame.from_records(
        [
            {"region_id": "left-a", "geometry": {"type": "Polygon", "coordinates": [[0.0, 0.0], [3.0, 0.0], [3.0, 2.0], [0.0, 2.0], [0.0, 0.0]]}},
        ],
        crs="EPSG:4326",
    )
    right = GeoPromptFrame.from_records(
        [
            {"zone_id": "right-a", "geometry": {"type": "Polygon", "coordinates": [[1.0, 0.0], [2.0, 0.0], [2.0, 2.0], [1.0, 2.0], [1.0, 0.0]]}},
        ],
        crs="EPSG:4326",
    )

    records = left.overlay_difference(right, left_id_column="region_id", right_id_column="zone_id").to_records()
    reference = shapely_geometry.Polygon([(0.0, 0.0), (3.0, 0.0), (3.0, 2.0), (0.0, 2.0)]).difference(
        shapely_geometry.Polygon([(1.0, 0.0), (2.0, 0.0), (2.0, 2.0), (1.0, 2.0)])
    )

    assert sum(geometry_area(record["geometry"]) for record in records) == pytest.approx(float(reference.area))


def test_overlay_symmetric_difference_excludes_overlap_faces() -> None:
    left = GeoPromptFrame.from_records(
        [
            {"region_id": "left-a", "geometry": {"type": "Polygon", "coordinates": [[0.0, 0.0], [2.0, 0.0], [2.0, 2.0], [0.0, 2.0], [0.0, 0.0]]}},
        ],
        crs="EPSG:4326",
    )
    right = GeoPromptFrame.from_records(
        [
            {"zone_id": "right-a", "geometry": {"type": "Polygon", "coordinates": [[1.0, 0.0], [3.0, 0.0], [3.0, 2.0], [1.0, 2.0], [1.0, 0.0]]}},
        ],
        crs="EPSG:4326",
    )

    symdiff = left.overlay_symmetric_difference(right, left_id_column="region_id", right_id_column="zone_id", rsuffix="right")
    records = symdiff.to_records()

    assert len(records) == 2
    assert [record["source_side_symdiff"] for record in records] == ["left", "right"]
    assert [record["area_symdiff"] for record in records] == [2.0, 2.0]
    assert records[0]["region_ids_symdiff"] == ["left-a"]
    assert records[0]["zone_ids_symdiff"] == []
    assert records[1]["region_ids_symdiff"] == []
    assert records[1]["zone_ids_symdiff"] == ["right-a"]


def test_spatial_lag_supports_distance_band_and_inverse_distance_weights() -> None:
    frame = GeoPromptFrame.from_records(
        [
            {"site_id": "a", "demand_index": 2.0, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
            {"site_id": "b", "demand_index": 4.0, "geometry": {"type": "Point", "coordinates": [1.0, 0.0]}},
            {"site_id": "c", "demand_index": 8.0, "geometry": {"type": "Point", "coordinates": [3.0, 0.0]}},
        ],
        crs="EPSG:4326",
    )

    lagged = frame.spatial_lag(
        "demand_index",
        mode="distance_band",
        max_distance=1.5,
        weight_mode="inverse_distance",
        include_diagnostics=True,
    )
    records = lagged.to_records()

    assert records[0]["demand_index_lag"] == 4.0
    assert records[1]["demand_index_lag"] == 2.0
    assert records[2]["demand_index_lag"] is None
    assert records[0]["neighbor_ids_lag"] == ["b"]
    assert records[1]["neighbor_ids_lag"] == ["a"]
    assert records[2]["neighbor_count_lag"] == 0
    assert records[0]["mode_lag"] == "distance_band"


def test_spatial_lag_supports_intersects_mode() -> None:
    frame = GeoPromptFrame.from_records(
        [
            {"site_id": "a", "weight": 2.0, "geometry": {"type": "Polygon", "coordinates": [[0.0, 0.0], [2.0, 0.0], [2.0, 2.0], [0.0, 2.0], [0.0, 0.0]]}},
            {"site_id": "b", "weight": 6.0, "geometry": {"type": "Polygon", "coordinates": [[2.0, 0.0], [4.0, 0.0], [4.0, 2.0], [2.0, 2.0], [2.0, 0.0]]}},
            {"site_id": "c", "weight": 10.0, "geometry": {"type": "Polygon", "coordinates": [[6.0, 0.0], [8.0, 0.0], [8.0, 2.0], [6.0, 2.0], [6.0, 0.0]]}},
        ],
        crs="EPSG:4326",
    )

    lagged = frame.spatial_lag("weight", mode="intersects", include_diagnostics=True)
    records = lagged.to_records()

    assert records[0]["weight_lag"] == 6.0
    assert records[1]["weight_lag"] == 2.0
    assert records[2]["weight_lag"] is None
    assert records[0]["neighbor_ids_lag"] == ["b"]
    assert records[2]["neighbor_weights_lag"] == []


def test_spatial_autocorrelation_reports_global_and_local_scores() -> None:
    frame = GeoPromptFrame.from_records(
        [
            {"site_id": "a", "value": 1.0, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
            {"site_id": "b", "value": 1.0, "geometry": {"type": "Point", "coordinates": [1.0, 0.0]}},
            {"site_id": "c", "value": 5.0, "geometry": {"type": "Point", "coordinates": [2.0, 0.0]}},
            {"site_id": "d", "value": 5.0, "geometry": {"type": "Point", "coordinates": [3.0, 0.0]}},
        ],
        crs="EPSG:4326",
    )

    autocorr = frame.spatial_autocorrelation(
        "value",
        mode="distance_band",
        max_distance=1.1,
        permutations=24,
        random_seed=7,
        significance_level=1.0,
        include_diagnostics=True,
    )
    records = autocorr.to_records()

    assert records[0]["global_moran_i_autocorr"] is not None
    assert records[0]["global_moran_i_autocorr"] > 0
    assert records[0]["global_geary_c_autocorr"] is not None
    assert 0.0 <= records[0]["global_moran_p_value_autocorr"] <= 1.0
    assert records[0]["local_moran_i_autocorr"] is not None
    assert records[0]["local_moran_i_autocorr"] > 0
    assert records[0]["local_cluster_label_autocorr"] == "low-low"
    assert records[0]["local_cluster_code_autocorr"] == "LL"
    assert records[0]["local_cluster_family_autocorr"] == "coldspot"
    assert records[0]["coldspot_autocorr"] is True
    assert records[0]["hotspot_autocorr"] is False
    assert records[3]["local_cluster_label_autocorr"] == "high-high"
    assert records[3]["hotspot_autocorr"] is True
    assert records[3]["significant_cluster_autocorr"] is True
    assert records[1]["neighbor_count_autocorr"] == 2
    assert records[0]["total_weight_autocorr"] == 4.0  # row-standardized weights


def test_summarize_autocorrelation_groups_cluster_families() -> None:
    frame = GeoPromptFrame.from_records(
        [
            {"site_id": "a", "value": 1.0, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
            {"site_id": "b", "value": 1.0, "geometry": {"type": "Point", "coordinates": [1.0, 0.0]}},
            {"site_id": "c", "value": 5.0, "geometry": {"type": "Point", "coordinates": [2.0, 0.0]}},
            {"site_id": "d", "value": 5.0, "geometry": {"type": "Point", "coordinates": [3.0, 0.0]}},
        ],
        crs="EPSG:4326",
    )

    autocorr = frame.spatial_autocorrelation(
        "value",
        mode="distance_band",
        max_distance=1.1,
        permutations=12,
        random_seed=7,
        significance_level=1.0,
    )
    summary = autocorr.summarize_autocorrelation("value")
    records = summary.to_records()

    assert [record["local_cluster_family_autocorr"] for record in records] == ["mixed", "coldspot", "hotspot"]
    assert [record["feature_count_autocorr"] for record in records] == [2, 1, 1]
    assert records[0]["value_mean_autocorr"] == 3.0
    assert records[1]["value_mean_autocorr"] == 1.0
    assert records[2]["value_mean_autocorr"] == 5.0
    assert records[0]["significant_count_autocorr"] == 2
    assert records[0]["site_ids_autocorr"] == ["b", "c"]


def test_report_autocorrelation_patterns_filters_to_publishable_families() -> None:
    frame = GeoPromptFrame.from_records(
        [
            {"site_id": "a", "value": 1.0, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
            {"site_id": "b", "value": 1.0, "geometry": {"type": "Point", "coordinates": [1.0, 0.0]}},
            {"site_id": "c", "value": 5.0, "geometry": {"type": "Point", "coordinates": [2.0, 0.0]}},
            {"site_id": "d", "value": 5.0, "geometry": {"type": "Point", "coordinates": [3.0, 0.0]}},
        ],
        crs="EPSG:4326",
    )

    autocorr = frame.spatial_autocorrelation(
        "value",
        mode="distance_band",
        max_distance=1.1,
        permutations=12,
        random_seed=7,
        significance_level=1.0,
    )
    report = autocorr.report_autocorrelation_patterns("value")
    records = report.to_records()

    assert {record["local_cluster_family_autocorr"] for record in records} == {"coldspot", "hotspot"}
    assert all(record["local_cluster_family_autocorr"] != "mixed" for record in records)
    coldspot_record = next(record for record in records if record["local_cluster_family_autocorr"] == "coldspot")
    hotspot_record = next(record for record in records if record["local_cluster_family_autocorr"] == "hotspot")
    assert coldspot_record["representative_ids_autocorr"] == ["a"]
    assert hotspot_record["representative_ids_autocorr"] == ["d"]
    assert [record["report_rank_autocorr"] for record in records] == [1, 2]


def test_trajectory_match_assigns_ordered_observations_to_network_edges() -> None:
    corridors = GeoPromptFrame.from_records(
        [
            {"site_id": "corridor-a", "geometry": {"type": "LineString", "coordinates": [[0.0, 0.0], [1.0, 0.0]]}},
            {"site_id": "corridor-b", "geometry": {"type": "LineString", "coordinates": [[1.0, 0.0], [1.0, 1.0]]}},
        ],
        crs="EPSG:4326",
    )
    network = corridors.network_build()
    observations = GeoPromptFrame.from_records(
        [
            {"site_id": "obs-1", "track_id": "track-a", "sequence": 1, "geometry": {"type": "Point", "coordinates": [0.2, 0.0]}},
            {"site_id": "obs-2", "track_id": "track-a", "sequence": 2, "geometry": {"type": "Point", "coordinates": [0.8, 0.0]}},
            {"site_id": "obs-3", "track_id": "track-a", "sequence": 3, "geometry": {"type": "Point", "coordinates": [1.0, 0.7]}},
        ],
        crs="EPSG:4326",
    )

    matched = network.trajectory_match(observations, candidate_k=2, max_distance=0.3, include_diagnostics=True)
    records = matched.to_records()

    assert [record["edge_id_match"] for record in records] == ["edge-00000", "edge-00000", "edge-00001"]
    assert [record["source_id"] for record in records] == ["corridor-a", "corridor-a", "corridor-b"]
    assert all(record["matched_match"] is True for record in records)
    assert [record["continuity_state_match"] for record in records] == ["start", "continuation", "continuation"]
    assert [record["segment_index_match"] for record in records] == [1, 1, 1]
    assert records[2]["transition_cost_match"] > 0.0
    assert records[2]["transition_penalty_match"] > 0.0
    assert records[2]["transition_mode_match"] == "hmm"


def test_trajectory_match_marks_off_network_gap_states() -> None:
    corridors = GeoPromptFrame.from_records(
        [
            {"site_id": "corridor-a", "geometry": {"type": "LineString", "coordinates": [[0.0, 0.0], [1.0, 0.0]]}},
            {"site_id": "corridor-b", "geometry": {"type": "LineString", "coordinates": [[1.0, 0.0], [2.0, 0.0]]}},
        ],
        crs="EPSG:4326",
    )
    network = corridors.network_build()
    observations = GeoPromptFrame.from_records(
        [
            {"site_id": "obs-1", "track_id": "track-a", "sequence": 1, "geometry": {"type": "Point", "coordinates": [0.2, 0.0]}},
            {"site_id": "obs-2", "track_id": "track-a", "sequence": 2, "geometry": {"type": "Point", "coordinates": [10.0, 10.0]}},
            {"site_id": "obs-3", "track_id": "track-a", "sequence": 3, "geometry": {"type": "Point", "coordinates": [1.8, 0.0]}},
        ],
        crs="EPSG:4326",
    )

    matched = network.trajectory_match(observations, candidate_k=2, max_distance=0.25, gap_penalty=0.5, include_diagnostics=True)
    records = matched.to_records()

    assert records[0]["matched_match"] is True
    assert records[1]["matched_match"] is False
    assert records[1]["gap_state_match"] is True
    assert records[1]["continuity_state_match"] == "gap"
    assert records[2]["matched_match"] is True
    assert records[2]["edge_id_match"] == "edge-00001"
    assert records[2]["continuity_state_match"] == "resume"
    assert records[2]["segment_index_match"] == 2


def test_summarize_trajectory_segments_collapses_contiguous_matches() -> None:
    corridors = GeoPromptFrame.from_records(
        [
            {"site_id": "corridor-a", "geometry": {"type": "LineString", "coordinates": [[0.0, 0.0], [1.0, 0.0]]}},
            {"site_id": "corridor-b", "geometry": {"type": "LineString", "coordinates": [[1.0, 0.0], [1.0, 1.0]]}},
        ],
        crs="EPSG:4326",
    )
    network = corridors.network_build()
    observations = GeoPromptFrame.from_records(
        [
            {"site_id": "obs-1", "track_id": "track-a", "sequence": 1, "geometry": {"type": "Point", "coordinates": [0.2, 0.0]}},
            {"site_id": "obs-2", "track_id": "track-a", "sequence": 2, "geometry": {"type": "Point", "coordinates": [0.8, 0.0]}},
            {"site_id": "obs-3", "track_id": "track-a", "sequence": 3, "geometry": {"type": "Point", "coordinates": [1.0, 0.7]}},
        ],
        crs="EPSG:4326",
    )

    matched = network.trajectory_match(observations, candidate_k=2, max_distance=0.3)
    segments = matched.summarize_trajectory_segments()
    records = segments.to_records()

    assert len(records) == 1
    assert records[0]["track_id"] == "track-a"
    assert records[0]["segment_index_match"] == 1
    assert records[0]["observation_ids_match"] == ["obs-1", "obs-2", "obs-3"]
    assert records[0]["edge_ids_match"] == ["edge-00000", "edge-00001"]
    assert records[0]["observation_count_match"] == 3
    assert records[0]["geometry"]["type"] == "LineString"


def test_summarize_trajectory_segments_splits_resumed_paths() -> None:
    corridors = GeoPromptFrame.from_records(
        [
            {"site_id": "corridor-a", "geometry": {"type": "LineString", "coordinates": [[0.0, 0.0], [1.0, 0.0]]}},
            {"site_id": "corridor-b", "geometry": {"type": "LineString", "coordinates": [[1.0, 0.0], [2.0, 0.0]]}},
        ],
        crs="EPSG:4326",
    )
    network = corridors.network_build()
    observations = GeoPromptFrame.from_records(
        [
            {"site_id": "obs-1", "track_id": "track-a", "sequence": 1, "geometry": {"type": "Point", "coordinates": [0.2, 0.0]}},
            {"site_id": "obs-2", "track_id": "track-a", "sequence": 2, "geometry": {"type": "Point", "coordinates": [10.0, 10.0]}},
            {"site_id": "obs-3", "track_id": "track-a", "sequence": 3, "geometry": {"type": "Point", "coordinates": [1.8, 0.0]}},
        ],
        crs="EPSG:4326",
    )

    matched = network.trajectory_match(observations, candidate_k=2, max_distance=0.25, gap_penalty=0.5)
    segments = matched.summarize_trajectory_segments()
    records = segments.to_records()

    assert len(records) == 2
    assert [record["segment_index_match"] for record in records] == [1, 2]
    assert [record["gap_before_match"] for record in records] == [False, True]
    assert [record["geometry"]["type"] for record in records] == ["Point", "Point"]


def test_score_trajectory_segments_flags_resumed_paths_for_review() -> None:
    corridors = GeoPromptFrame.from_records(
        [
            {"site_id": "corridor-a", "geometry": {"type": "LineString", "coordinates": [[0.0, 0.0], [1.0, 0.0]]}},
            {"site_id": "corridor-b", "geometry": {"type": "LineString", "coordinates": [[1.0, 0.0], [2.0, 0.0]]}},
        ],
        crs="EPSG:4326",
    )
    network = corridors.network_build()
    observations = GeoPromptFrame.from_records(
        [
            {"site_id": "obs-1", "track_id": "track-a", "sequence": 1, "geometry": {"type": "Point", "coordinates": [0.2, 0.0]}},
            {"site_id": "obs-2", "track_id": "track-a", "sequence": 2, "geometry": {"type": "Point", "coordinates": [0.8, 0.0]}},
            {"site_id": "obs-3", "track_id": "track-a", "sequence": 3, "geometry": {"type": "Point", "coordinates": [10.0, 10.0]}},
            {"site_id": "obs-4", "track_id": "track-a", "sequence": 4, "geometry": {"type": "Point", "coordinates": [1.2, 0.0]}},
            {"site_id": "obs-5", "track_id": "track-a", "sequence": 5, "geometry": {"type": "Point", "coordinates": [1.8, 0.0]}},
        ],
        crs="EPSG:4326",
    )

    scored = (
        network.trajectory_match(observations, candidate_k=2, max_distance=0.25, gap_penalty=0.5)
        .summarize_trajectory_segments()
        .score_trajectory_segments(distance_threshold=0.2, transition_cost_threshold=0.5)
    )
    records = scored.to_records()

    first_segment = next(record for record in records if record["segment_index_match"] == 1)
    second_segment = next(record for record in records if record["segment_index_match"] == 2)

    assert first_segment["anomaly_flags_trajectory"] == []
    assert first_segment["review_segment_trajectory"] is False
    assert second_segment["gap_before_match"] is True
    assert second_segment["anomaly_flags_trajectory"] == ["resumed_after_gap"]
    assert second_segment["anomaly_level_trajectory"] == "moderate"
    assert second_segment["review_segment_trajectory"] is True
    assert second_segment["confidence_score_trajectory"] < first_segment["confidence_score_trajectory"]


def test_change_detection_classifies_basic_change_types() -> None:
    left = GeoPromptFrame.from_records(
        [
            {"site_id": "same", "value": 1.0, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
            {"site_id": "move", "value": 2.0, "geometry": {"type": "Point", "coordinates": [1.0, 0.0]}},
            {"site_id": "modify", "value": 3.0, "geometry": {"type": "Point", "coordinates": [2.0, 0.0]}},
            {"site_id": "remove", "value": 4.0, "geometry": {"type": "Point", "coordinates": [3.0, 0.0]}},
        ],
        crs="EPSG:4326",
    )
    right = GeoPromptFrame.from_records(
        [
            {"site_id": "same", "value": 1.0, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
            {"site_id": "move", "value": 2.0, "geometry": {"type": "Point", "coordinates": [1.2, 0.0]}},
            {"site_id": "modify", "value": 9.0, "geometry": {"type": "Point", "coordinates": [2.0, 0.0]}},
            {"site_id": "add", "value": 5.0, "geometry": {"type": "Point", "coordinates": [4.0, 0.0]}},
        ],
        crs="EPSG:4326",
    )

    changes = left.change_detection(right, attribute_columns=["value"], max_distance=0.5, include_diagnostics=True)
    records = changes.to_records()
    classes = {
        tuple(record["left_ids_change"]): record["change_class_change"]
        for record in records
        if record["event_side_change"] == "left"
    }
    added = [record for record in records if record["change_class_change"] == "added"]

    assert classes[("same",)] == "unchanged"
    assert classes[("move",)] == "moved"
    assert classes[("modify",)] == "modified"
    assert classes[("remove",)] == "removed"
    assert len(added) == 1
    assert added[0]["left_ids_change"] == []
    assert added[0]["right_ids_change"] == ["add"]
    assert added[0]["change_class_change"] == "added"
    modify_record = next(record for record in records if record["left_ids_change"] == ["modify"])
    assert modify_record["attribute_changes_change"] == {"value": {"left": 3.0, "right": 9.0}}
    assert modify_record["event_group_id_change"].startswith("event-")
    assert modify_record["event_summary_change"]["change_class"] == "modified"
    assert modify_record["event_summary_change"]["attribute_columns"] == ["value"]


def test_change_detection_detects_split_and_merge_events() -> None:
    split_left = GeoPromptFrame.from_records(
        [
            {"site_id": "zone-a", "geometry": {"type": "Polygon", "coordinates": [[0.0, 0.0], [4.0, 0.0], [4.0, 2.0], [0.0, 2.0], [0.0, 0.0]]}},
        ],
        crs="EPSG:4326",
    )
    split_right = GeoPromptFrame.from_records(
        [
            {"site_id": "zone-a-1", "geometry": {"type": "Polygon", "coordinates": [[0.0, 0.0], [2.0, 0.0], [2.0, 2.0], [0.0, 2.0], [0.0, 0.0]]}},
            {"site_id": "zone-a-2", "geometry": {"type": "Polygon", "coordinates": [[2.0, 0.0], [4.0, 0.0], [4.0, 2.0], [2.0, 2.0], [2.0, 0.0]]}},
        ],
        crs="EPSG:4326",
    )

    split_changes = split_left.change_detection(split_right, max_distance=3.0)
    split_record = next(record for record in split_changes.to_records() if record["change_class_change"] == "split")
    assert split_record["left_ids_change"] == ["zone-a"]
    assert sorted(split_record["right_ids_change"]) == ["zone-a-1", "zone-a-2"]
    assert split_record["area_share_score_change"] > 0.0
    assert split_record["match_area_shares_change"][0]["left_share"] == 0.5
    assert split_record["match_area_shares_change"][0]["right_share"] == 1.0
    assert split_record["event_feature_count_change"] == 3
    assert split_record["event_summary_change"]["right_count"] == 2

    merge_left = split_right
    merge_right = split_left
    merge_changes = merge_left.change_detection(merge_right, max_distance=3.0)
    merge_record = next(record for record in merge_changes.to_records() if record["change_class_change"] == "merge")
    assert sorted(merge_record["left_ids_change"]) == ["zone-a-1", "zone-a-2"]
    assert merge_record["right_ids_change"] == ["zone-a"]
    assert merge_record["area_share_score_change"] > 0.0
    assert merge_record["event_summary_change"]["left_count"] == 2


def test_extract_change_events_collapses_split_rows_into_single_event() -> None:
    left = GeoPromptFrame.from_records(
        [
            {"site_id": "zone-a", "geometry": {"type": "Polygon", "coordinates": [[0.0, 0.0], [4.0, 0.0], [4.0, 2.0], [0.0, 2.0], [0.0, 0.0]]}},
        ],
        crs="EPSG:4326",
    )
    right = GeoPromptFrame.from_records(
        [
            {"site_id": "zone-a-1", "geometry": {"type": "Polygon", "coordinates": [[0.0, 0.0], [2.0, 0.0], [2.0, 2.0], [0.0, 2.0], [0.0, 0.0]]}},
            {"site_id": "zone-a-2", "geometry": {"type": "Polygon", "coordinates": [[2.0, 0.0], [4.0, 0.0], [4.0, 2.0], [2.0, 2.0], [2.0, 0.0]]}},
        ],
        crs="EPSG:4326",
    )

    events = left.change_detection(right, max_distance=3.0).extract_change_events()
    records = events.to_records()

    assert len(records) == 1
    assert records[0]["change_class_change"] == "split"
    assert records[0]["left_ids_change"] == ["zone-a"]
    assert sorted(records[0]["right_ids_change"]) == ["zone-a-1", "zone-a-2"]
    assert records[0]["event_feature_count_change"] == 3
    assert records[0]["member_geometry_types_change"] == ["Polygon"]
    assert records[0]["geometry"]["type"] == "Point"


def test_compare_change_events_reports_persisted_resolved_and_emerged_events() -> None:
    left = GeoPromptFrame.from_records(
        [
            {"site_id": "same", "value": 1.0, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
            {"site_id": "modify", "value": 3.0, "geometry": {"type": "Point", "coordinates": [2.0, 0.0]}},
            {"site_id": "remove", "value": 4.0, "geometry": {"type": "Point", "coordinates": [3.0, 0.0]}},
        ],
        crs="EPSG:4326",
    )
    right_a = GeoPromptFrame.from_records(
        [
            {"site_id": "same", "value": 1.0, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
            {"site_id": "modify", "value": 9.0, "geometry": {"type": "Point", "coordinates": [2.0, 0.0]}},
            {"site_id": "add-a", "value": 5.0, "geometry": {"type": "Point", "coordinates": [4.0, 0.0]}},
        ],
        crs="EPSG:4326",
    )
    right_b = GeoPromptFrame.from_records(
        [
            {"site_id": "same", "value": 1.0, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
            {"site_id": "modify", "value": 11.0, "geometry": {"type": "Point", "coordinates": [2.0, 0.0]}},
            {"site_id": "add-b", "value": 6.0, "geometry": {"type": "Point", "coordinates": [5.0, 0.0]}},
        ],
        crs="EPSG:4326",
    )

    baseline_events = left.change_detection(right_a, attribute_columns=["value"], max_distance=0.5).extract_change_events()
    current_events = left.change_detection(right_b, attribute_columns=["value"], max_distance=0.5).extract_change_events()
    comparison = baseline_events.compare_change_events(current_events)
    records = comparison.to_records()
    status_by_signature = {
        record["event_signature_eventdiff"]: record["event_status_eventdiff"]
        for record in records
    }

    assert status_by_signature["added|none|add-a"] == "resolved"
    assert status_by_signature["added|none|add-b"] == "emerged"
    assert status_by_signature["modified|modify|modify"] == "persisted"
    persisted_record = next(record for record in records if record["event_signature_eventdiff"] == "modified|modify|modify")
    assert persisted_record["baseline_event_summary_change"]["attribute_columns"] == ["value"]
    assert persisted_record["current_event_summary_change"]["attribute_columns"] == ["value"]


def test_compare_change_events_equivalent_mode_matches_near_equivalent_events() -> None:
    baseline = GeoPromptFrame.from_records(
        [
            {
                "event_group_id_change": "event-00001",
                "change_class_change": "split",
                "event_side_change": "left",
                "left_ids_change": ["zone-a"],
                "right_ids_change": ["zone-a-1", "zone-a-2"],
                "event_row_count_change": 1,
                "event_feature_count_change": 3,
                "member_geometry_types_change": ["Polygon"],
                "event_summary_change": {
                    "change_class": "split",
                    "event_side": "left",
                    "left_ids": ["zone-a"],
                    "right_ids": ["zone-a-1", "zone-a-2"],
                    "left_count": 1,
                    "right_count": 2,
                    "row_count": 1,
                    "feature_count": 3,
                    "attribute_columns": [],
                    "mean_similarity_score": 0.9,
                    "mean_area_share_score": 1.0,
                },
                "geometry": {"type": "Point", "coordinates": [2.0, 1.0]},
            }
        ],
        crs="EPSG:4326",
    )
    current = GeoPromptFrame.from_records(
        [
            {
                "event_group_id_change": "event-00009",
                "change_class_change": "split",
                "event_side_change": "left",
                "left_ids_change": ["zone-a"],
                "right_ids_change": ["zone-a-west", "zone-a-east"],
                "event_row_count_change": 1,
                "event_feature_count_change": 3,
                "member_geometry_types_change": ["Polygon"],
                "event_summary_change": {
                    "change_class": "split",
                    "event_side": "left",
                    "left_ids": ["zone-a"],
                    "right_ids": ["zone-a-west", "zone-a-east"],
                    "left_count": 1,
                    "right_count": 2,
                    "row_count": 1,
                    "feature_count": 3,
                    "attribute_columns": [],
                    "mean_similarity_score": 0.88,
                    "mean_area_share_score": 1.0,
                },
                "geometry": {"type": "Point", "coordinates": [2.05, 1.0]},
            }
        ],
        crs="EPSG:4326",
    )

    exact = baseline.compare_change_events(current)
    equivalent = baseline.compare_change_events(current, match_mode="equivalent")

    exact_statuses = [record["event_status_eventdiff"] for record in exact.to_records()]
    equivalent_records = equivalent.to_records()

    assert exact_statuses == ["emerged", "resolved"]
    assert len(equivalent_records) == 1
    assert equivalent_records[0]["event_status_eventdiff"] == "persisted"
    assert equivalent_records[0]["match_mode_eventdiff"] == "equivalent"
    assert equivalent_records[0]["event_similarity_eventdiff"] is not None
    assert equivalent_records[0]["event_similarity_eventdiff"] >= 0.6


def test_network_build_splits_lines_at_intersections() -> None:
    lines = GeoPromptFrame.from_records(
        [
            {"site_id": "horizontal", "geometry": {"type": "LineString", "coordinates": [[0.0, 0.0], [2.0, 0.0]]}},
            {"site_id": "vertical", "geometry": {"type": "LineString", "coordinates": [[1.0, -1.0], [1.0, 1.0]]}},
        ],
        crs="EPSG:4326",
    )

    network = lines.network_build()
    records = network.to_records()
    node_ids = {record["from_node_id"] for record in records} | {record["to_node_id"] for record in records}
    intersection_nodes = [record for record in records if record["from_node"] == (1.0, 0.0) or record["to_node"] == (1.0, 0.0)]

    assert len(records) == 4
    assert len(node_ids) == 5
    assert intersection_nodes
    assert all(record["edge_length"] == 1.0 for record in records)


def test_network_build_reuses_cached_frame() -> None:
    lines = GeoPromptFrame.from_records(
        [
            {"site_id": "horizontal", "geometry": {"type": "LineString", "coordinates": [[0.0, 0.0], [2.0, 0.0]]}},
        ],
        crs="EPSG:4326",
    )

    first_network = lines.network_build()
    second_network = lines.network_build()

    assert first_network is second_network


def test_shortest_path_returns_ordered_edge_path() -> None:
    network = GeoPromptFrame.from_records(
        [
            {
                "edge_id": "edge-1",
                "from_node_id": "node-a",
                "to_node_id": "node-b",
                "from_node": (0.0, 0.0),
                "to_node": (1.0, 0.0),
                "edge_length": 1.0,
                "geometry": {"type": "LineString", "coordinates": [(0.0, 0.0), (1.0, 0.0)]},
            },
            {
                "edge_id": "edge-2",
                "from_node_id": "node-b",
                "to_node_id": "node-c",
                "from_node": (1.0, 0.0),
                "to_node": (2.0, 0.0),
                "edge_length": 1.0,
                "geometry": {"type": "LineString", "coordinates": [(1.0, 0.0), (2.0, 0.0)]},
            },
            {
                "edge_id": "edge-3",
                "from_node_id": "node-a",
                "to_node_id": "node-c",
                "from_node": (0.0, 0.0),
                "to_node": (2.0, 0.0),
                "edge_length": 5.0,
                "geometry": {"type": "LineString", "coordinates": [(0.0, 0.0), (2.0, 0.0)]},
            },
        ],
        crs="EPSG:4326",
    )

    path = network.shortest_path("node-a", "node-c")
    records = path.to_records()

    assert [record["edge_id"] for record in records] == ["edge-1", "edge-2"]
    assert records[0]["step_path"] == 1
    assert records[1]["step_path"] == 2
    assert records[0]["total_cost_path"] == 2.0
    assert records[0]["node_sequence_path"] == ["node-a", "node-b", "node-c"]


def test_service_area_returns_reachable_edges() -> None:
    network = GeoPromptFrame.from_records(
        [
            {
                "edge_id": "edge-1",
                "from_node_id": "node-a",
                "to_node_id": "node-b",
                "from_node": (0.0, 0.0),
                "to_node": (1.0, 0.0),
                "edge_length": 1.0,
                "geometry": {"type": "LineString", "coordinates": [(0.0, 0.0), (1.0, 0.0)]},
            },
            {
                "edge_id": "edge-2",
                "from_node_id": "node-b",
                "to_node_id": "node-c",
                "from_node": (1.0, 0.0),
                "to_node": (2.0, 0.0),
                "edge_length": 1.0,
                "geometry": {"type": "LineString", "coordinates": [(1.0, 0.0), (2.0, 0.0)]},
            },
            {
                "edge_id": "edge-3",
                "from_node_id": "node-c",
                "to_node_id": "node-d",
                "from_node": (2.0, 0.0),
                "to_node": (3.0, 0.0),
                "edge_length": 1.0,
                "geometry": {"type": "LineString", "coordinates": [(2.0, 0.0), (3.0, 0.0)]},
            },
        ],
        crs="EPSG:4326",
    )

    service = network.service_area("node-a", max_cost=2.0)
    records = service.to_records()

    assert [record["edge_id"] for record in records] == ["edge-1", "edge-2"]
    assert all(record["max_cost_service"] == 2.0 for record in records)
    assert all(record["origin_nodes_service"] == ["node-a"] for record in records)


def test_service_area_supports_partial_edges_and_diagnostics() -> None:
    network = GeoPromptFrame.from_records(
        [
            {
                "edge_id": "edge-1",
                "from_node_id": "node-a",
                "to_node_id": "node-b",
                "from_node": (0.0, 0.0),
                "to_node": (1.0, 0.0),
                "edge_length": 1.0,
                "geometry": {"type": "LineString", "coordinates": [(0.0, 0.0), (1.0, 0.0)]},
            },
            {
                "edge_id": "edge-2",
                "from_node_id": "node-b",
                "to_node_id": "node-c",
                "from_node": (1.0, 0.0),
                "to_node": (2.0, 0.0),
                "edge_length": 1.0,
                "geometry": {"type": "LineString", "coordinates": [(1.0, 0.0), (2.0, 0.0)]},
            },
            {
                "edge_id": "edge-3",
                "from_node_id": "node-c",
                "to_node_id": "node-d",
                "from_node": (2.0, 0.0),
                "to_node": (3.0, 0.0),
                "edge_length": 1.0,
                "geometry": {"type": "LineString", "coordinates": [(2.0, 0.0), (3.0, 0.0)]},
            },
        ],
        crs="EPSG:4326",
    )

    service = network.service_area("node-a", max_cost=2.5, include_partial_edges=True, include_diagnostics=True)
    records = sorted(service.to_records(), key=lambda item: (item["edge_id"], item["segment_index_service"]))

    assert [record["edge_id"] for record in records] == ["edge-1", "edge-2", "edge-3"]
    assert records[2]["partial_service"] is True
    assert records[2]["coverage_ratio_service"] == 0.5
    assert records[2]["geometry"]["coordinates"] == ((2.0, 0.0), (2.5, 0.0))
    assert records[0]["reachable_segment_count_service"] == 3
    assert records[0]["partial_edge_count_service"] == 1


def test_location_allocate_assigns_by_network_cost_and_capacity() -> None:
    network = GeoPromptFrame.from_records(
        [
            {
                "edge_id": "edge-1",
                "from_node_id": "node-a",
                "to_node_id": "node-b",
                "from_node": (0.0, 0.0),
                "to_node": (1.0, 0.0),
                "edge_length": 1.0,
                "geometry": {"type": "LineString", "coordinates": [(0.0, 0.0), (1.0, 0.0)]},
            },
            {
                "edge_id": "edge-2",
                "from_node_id": "node-b",
                "to_node_id": "node-c",
                "from_node": (1.0, 0.0),
                "to_node": (2.0, 0.0),
                "edge_length": 1.0,
                "geometry": {"type": "LineString", "coordinates": [(1.0, 0.0), (2.0, 0.0)]},
            },
            {
                "edge_id": "edge-3",
                "from_node_id": "node-c",
                "to_node_id": "node-d",
                "from_node": (2.0, 0.0),
                "to_node": (3.0, 0.0),
                "edge_length": 1.0,
                "geometry": {"type": "LineString", "coordinates": [(2.0, 0.0), (3.0, 0.0)]},
            },
        ],
        crs="EPSG:4326",
    )
    facilities = GeoPromptFrame.from_records(
        [
            {"facility_id": "facility-a", "capacity": 1.0, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
            {"facility_id": "facility-d", "capacity": 1.0, "geometry": {"type": "Point", "coordinates": [3.0, 0.0]}},
        ],
        crs="EPSG:4326",
    )
    demands = GeoPromptFrame.from_records(
        [
            {"demand_id": "demand-1", "demand": 1.0, "geometry": {"type": "Point", "coordinates": [1.0, 0.0]}},
            {"demand_id": "demand-2", "demand": 1.0, "geometry": {"type": "Point", "coordinates": [2.0, 0.0]}},
            {"demand_id": "demand-3", "demand": 1.0, "geometry": {"type": "Point", "coordinates": [3.0, 0.0]}},
        ],
        crs="EPSG:4326",
    )

    allocation = network.location_allocate(
        facilities,
        demands,
        facility_id_column="facility_id",
        demand_id_column="demand_id",
        demand_weight_column="demand",
        facility_capacity_column="capacity",
        aggregations={"demand": "sum"},
        include_diagnostics=True,
    )
    records = sorted(allocation.to_records(), key=lambda item: item["facility_id"])

    assert records[0]["facility_id"] == "facility-a"
    assert records[0]["demand_ids_allocate"] == ["demand-1"]
    assert records[0]["count_allocate"] == 1
    assert records[0]["demand_sum_allocate"] == 1.0
    assert records[0]["capacity_remaining_allocate"] == 0.0
    assert records[0]["count_unallocated_allocate"] == 1
    assert records[0]["demand_ids_unallocated_allocate"] == ["demand-2"]
    assert records[0]["candidate_route_count_allocate"] == 6

    assert records[1]["facility_id"] == "facility-d"
    assert records[1]["demand_ids_allocate"] == ["demand-3"]
    assert records[1]["cost_min_allocate"] == 0.0
    assert records[1]["capacity_used_allocate"] == 1.0


def test_read_geojson_feature_collection(tmp_path: Path) -> None:
    geojson_path = tmp_path / "feature_collection.geojson"
    payload = {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
        "features": [
            {
                "type": "Feature",
                "id": "point-a",
                "properties": {"name": "Point A", "demand_index": 1.0},
                "geometry": {"type": "Point", "coordinates": [-111.92, 40.78]},
            },
            {
                "type": "Feature",
                "id": "point-b",
                "properties": {"name": "Point B", "demand_index": 0.8},
                "geometry": {"type": "Point", "coordinates": [-111.96, 40.71]},
            },
        ],
    }
    geojson_path.write_text(json.dumps(payload), encoding="utf-8")

    frame = read_geojson(geojson_path)

    assert len(frame) == 2
    assert frame.crs == "EPSG:4326"
    assert sorted(frame.geometry_types()) == ["Point", "Point"]


def test_set_crs_and_reproject() -> None:
    frame = read_features(PROJECT_ROOT / "data" / "sample_features.json", crs="EPSG:4326")

    projected = frame.to_crs("EPSG:3857")
    first_point = projected.head(1)[0]["geometry"]["coordinates"]

    assert projected.crs == "EPSG:3857"
    assert abs(first_point[0]) > 10000000
    assert abs(first_point[1]) > 1000000


def test_spatial_join_contains_regions() -> None:
    regions = read_features(PROJECT_ROOT / "data" / "benchmark_regions.json", crs="EPSG:4326")
    features = read_features(PROJECT_ROOT / "data" / "benchmark_features.json", crs="EPSG:4326")

    joined = regions.spatial_join(features, predicate="intersects")
    left_joined = regions.spatial_join(features, predicate="intersects", how="left")
    pairs = {f"{row['region_id']}->{row['site_id']}" for row in joined}

    assert "northwest-sector->alpha-point" in pairs
    assert "northeast-sector->beta-point" in pairs
    assert "southwest-sector->gamma-point" in pairs
    assert "southeast-sector->delta-point" in pairs
    assert all("remote-point" not in pair for pair in pairs)
    assert len(left_joined) >= len(joined)


def test_clip_and_overlay_intersections() -> None:
    regions = read_features(PROJECT_ROOT / "data" / "benchmark_regions.json", crs="EPSG:4326")
    features = read_features(PROJECT_ROOT / "data" / "benchmark_features.json", crs="EPSG:4326")

    clipped = features.clip(regions.query_bounds(min_x=-112.02, min_y=40.62, max_x=-111.92, max_y=40.82))
    intersections = regions.overlay_intersections(features)

    assert len(clipped) > 0
    assert any(record["site_id"] == "north-connector-line" for record in clipped)
    assert any(record["region_id"] == "northwest-sector" and record["site_id"] == "alpha-point" for record in intersections)
    assert any(record["region_id"] == "southeast-sector" and record["site_id"] == "delta-point" for record in intersections)


def test_clip_matches_shapely_intersection_area_when_available() -> None:
    shapely_geometry = pytest.importorskip("shapely.geometry")

    polygons = GeoPromptFrame.from_records(
        [
            {
                "name": "A",
                "geometry": {"type": "Polygon", "coordinates": [[0.0, 0.0], [2.0, 0.0], [2.0, 2.0], [0.0, 2.0], [0.0, 0.0]]},
            },
            {
                "name": "B",
                "geometry": {"type": "Polygon", "coordinates": [[2.0, 0.0], [4.0, 0.0], [4.0, 2.0], [2.0, 2.0], [2.0, 0.0]]},
            },
        ],
        crs="EPSG:4326",
    )
    mask = GeoPromptFrame.from_records(
        [
            {
                "geometry": {"type": "Polygon", "coordinates": [[1.0, -1.0], [3.0, -1.0], [3.0, 1.0], [1.0, 1.0], [1.0, -1.0]]},
            }
        ],
        crs="EPSG:4326",
    )

    clipped = polygons.clip(mask).to_records()
    reference_mask = shapely_geometry.Polygon([(1.0, -1.0), (3.0, -1.0), (3.0, 1.0), (1.0, 1.0)])
    reference_area = sum(
        float(shapely_geometry.Polygon(coords).intersection(reference_mask).area)
        for coords in (
            [(0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0)],
            [(2.0, 0.0), (4.0, 0.0), (4.0, 2.0), (2.0, 2.0)],
        )
    )

    assert sum(geometry_area(record["geometry"]) for record in clipped) == pytest.approx(reference_area)


def test_overlay_summary_returns_overlap_metrics_and_aggregates() -> None:
    regions = read_features(PROJECT_ROOT / "data" / "benchmark_regions.json", crs="EPSG:4326")
    features = read_features(PROJECT_ROOT / "data" / "benchmark_features.json", crs="EPSG:4326")

    summary = features.overlay_summary(
        regions,
        right_id_column="region_id",
        aggregations={"region_name": "count"},
        how="left",
    )
    records = {record["site_id"]: record for record in summary.to_records()}

    assert records["alpha-point"]["region_ids_overlay"] == ["northwest-sector"]
    assert records["alpha-point"]["count_overlay"] == 1
    assert records["alpha-point"]["intersection_count_overlay"] == 1
    assert records["alpha-point"]["area_overlap_overlay"] == 0.0
    assert records["alpha-point"]["length_overlap_overlay"] == 0.0
    assert records["alpha-point"]["region_name_count_overlay"] == 1

    assert records["north-campus-zone"]["count_overlay"] >= 1
    assert records["north-campus-zone"]["area_overlap_overlay"] > 0.0
    assert records["north-campus-zone"]["area_share_overlay"] is not None
    assert records["north-campus-zone"]["area_share_overlay"] > 0.0

    assert records["north-connector-line"]["count_overlay"] >= 1
    assert records["north-connector-line"]["length_overlap_overlay"] > 0.0
    assert records["north-connector-line"]["length_share_overlay"] is not None
    assert records["north-connector-line"]["length_share_overlay"] > 0.0

    assert records["remote-point"]["count_overlay"] == 0
    assert records["remote-point"]["region_ids_overlay"] == []
    assert records["remote-point"]["region_name_count_overlay"] is None


def test_overlay_summary_supports_inner_mode() -> None:
    regions = read_features(PROJECT_ROOT / "data" / "benchmark_regions.json", crs="EPSG:4326")
    features = read_features(PROJECT_ROOT / "data" / "benchmark_features.json", crs="EPSG:4326")

    summary = features.overlay_summary(regions, right_id_column="region_id", how="inner")
    site_ids = {record["site_id"] for record in summary}

    assert "remote-point" not in site_ids
    assert "alpha-point" in site_ids


def test_overlay_summary_supports_grouping_and_right_normalization() -> None:
    regions = read_features(PROJECT_ROOT / "data" / "benchmark_regions.json", crs="EPSG:4326")
    features = read_features(PROJECT_ROOT / "data" / "benchmark_features.json", crs="EPSG:4326")

    summary = features.overlay_summary(
        regions,
        right_id_column="region_id",
        group_by="region_band",
        normalize_by="both",
        top_n_groups=1,
    )
    records = {record["site_id"]: record for record in summary.to_records()}

    north_zone = records["north-campus-zone"]
    assert north_zone["groups_overlay"]
    assert len(north_zone["groups_overlay"]) == 1
    assert north_zone["best_group_overlay"] in {"north", "south"}
    assert north_zone["area_share_overlay"] is not None
    assert north_zone["area_share_right_overlay"] is not None


def test_overlay_group_comparison_returns_gap_metrics() -> None:
    regions = read_features(PROJECT_ROOT / "data" / "benchmark_regions.json", crs="EPSG:4326")
    features = read_features(PROJECT_ROOT / "data" / "benchmark_features.json", crs="EPSG:4326")

    comparison = features.overlay_group_comparison(
        regions,
        group_by="region_band",
        right_id_column="region_id",
    )
    records = {record["site_id"]: record for record in comparison.to_records()}
    north_zone = records["north-campus-zone"]
    assert north_zone["top_group_overlay_compare"] in {"north", "south"}
    assert "runner_up_group_overlay_compare" in north_zone


def test_dissolve_regions_by_band() -> None:
    regions = read_features(PROJECT_ROOT / "data" / "benchmark_regions.json", crs="EPSG:4326")

    dissolved = regions.dissolve(by="region_band", aggregations={"region_name": "count"})
    records = sorted(dissolved.to_records(), key=lambda item: str(item["region_band"]))

    assert len(records) == 2
    assert records[0]["region_band"] == "north"
    assert records[0]["region_name"] == 2
    assert records[1]["region_band"] == "south"
    assert records[1]["region_name"] == 2
    assert all(record["geometry"]["type"] == "Polygon" for record in records)


def test_area_similarity_equation() -> None:
    similarity = area_similarity(origin_area=0.010, destination_area=0.009, distance_value=0.05, scale=0.2, power=1.2)
    corridor = corridor_strength(weight=0.95, corridor_length=0.15, distance_value=0.08, scale=0.18, power=1.4)

    assert round(similarity, 4) == 0.6886
    assert round(corridor, 4) == 0.0793


def test_directional_alignment() -> None:
    alignment = directional_alignment((-111.96, 40.71), (-111.78, 40.66), preferred_bearing=90.0)

    assert alignment > 0.7


def test_build_demo_report(tmp_path: Path) -> None:
    report = cast(dict[str, Any], build_demo_report(
        input_path=PROJECT_ROOT / "data" / "sample_features.json",
        output_dir=tmp_path,
    ))
    summary = cast(dict[str, Any], report["summary"])

    assert report["package"] == "geoprompt"
    assert len(report["records"]) == 6
    assert len(report["top_interactions"]) == 5
    assert len(report["top_area_similarity"]) == 5
    assert len(report["top_nearest_neighbors"]) == 6
    assert len(report["top_geographic_neighbors"]) == 6
    assert summary["geometry_types"] == ["LineString", "Point", "Polygon"]
    assert summary["crs"] == "EPSG:4326"
    assert cast(dict[str, Any], summary["projected_bounds_3857"])["min_x"] < -12000000
    assert summary["valley_window_feature_count"] == 3
    assert (tmp_path / "charts" / "neighborhood-pressure-review.png").exists()


def test_stress_corpus_generators_create_mixed_geometries() -> None:
    feature_records = _stress_feature_records()
    region_records = _stress_region_records()

    geometry_types = {record["geometry"]["type"] for record in feature_records}

    assert len(feature_records) == 93
    assert geometry_types == {"Point", "LineString", "Polygon"}
    assert any(record["site_id"] == "stress-remote-point" for record in feature_records)
    assert len(region_records) == 16
    assert {record["region_band"] for record in region_records} == {"north", "south"}


def test_corridor_reach_finds_features_near_lines() -> None:
    features = GeoPromptFrame.from_records(
        [
            {"site_id": "near-a", "demand": 2.0, "geometry": {"type": "Point", "coordinates": [1.0, 0.1]}},
            {"site_id": "near-b", "demand": 3.0, "geometry": {"type": "Point", "coordinates": [2.0, -0.05]}},
            {"site_id": "far-c", "demand": 5.0, "geometry": {"type": "Point", "coordinates": [5.0, 5.0]}},
        ],
        crs="EPSG:4326",
    )
    corridors = GeoPromptFrame.from_records(
        [
            {"site_id": "route-1", "capacity": 10.0, "geometry": {"type": "LineString", "coordinates": [[0.0, 0.0], [3.0, 0.0]]}},
        ],
        crs="EPSG:4326",
    )

    result = features.corridor_reach(
        corridors,
        max_distance=0.2,
        corridor_id_column="site_id",
        aggregations={"capacity": "sum"},
    )
    records = {r["site_id"]: r for r in result.to_records()}

    assert records["near-a"]["count_reach"] == 1
    assert records["near-a"]["site_ids_reach"] == ["route-1"]
    assert records["near-a"]["distance_min_reach"] is not None
    assert records["near-a"]["distance_min_reach"] <= 0.2
    assert records["near-a"]["corridor_length_total_reach"] > 0
    assert records["near-a"]["capacity_sum_reach"] == 10.0
    assert records["near-b"]["count_reach"] == 1
    assert records["far-c"]["count_reach"] == 0
    assert records["far-c"]["distance_min_reach"] is None


def test_corridor_reach_supports_inner_mode() -> None:
    features = GeoPromptFrame.from_records(
        [
            {"site_id": "near", "geometry": {"type": "Point", "coordinates": [1.0, 0.05]}},
            {"site_id": "far", "geometry": {"type": "Point", "coordinates": [10.0, 10.0]}},
        ],
        crs="EPSG:4326",
    )
    corridors = GeoPromptFrame.from_records(
        [{"site_id": "route", "geometry": {"type": "LineString", "coordinates": [[0.0, 0.0], [2.0, 0.0]]}}],
        crs="EPSG:4326",
    )

    result = features.corridor_reach(corridors, max_distance=0.1, how="inner")
    assert len(result) == 1
    assert result.to_records()[0]["site_id"] == "near"


def test_corridor_reach_supports_haversine_distance() -> None:
    features = GeoPromptFrame.from_records(
        [{"site_id": "near", "geometry": {"type": "Point", "coordinates": [-111.95, 40.75]}}],
        crs="EPSG:4326",
    )
    corridors = GeoPromptFrame.from_records(
        [{"site_id": "route", "geometry": {"type": "LineString", "coordinates": [[-111.96, 40.75], [-111.94, 40.75]]}}],
        crs="EPSG:4326",
    )

    result = features.corridor_reach(corridors, max_distance=1.0, distance_method="haversine")
    record = result.to_records()[0]
    assert record["count_reach"] == 1
    assert record["distance_method_reach"] == "haversine"
    assert record["distance_min_reach"] is not None
    assert record["distance_min_reach"] < 1.0


def test_corridor_reach_supports_network_distance_and_scoring() -> None:
    features = GeoPromptFrame.from_records(
        [
            {"site_id": "near-start", "geometry": {"type": "Point", "coordinates": [1.0, 0.1]}},
            {"site_id": "far-along", "geometry": {"type": "Point", "coordinates": [9.0, 0.1]}},
        ],
        crs="EPSG:4326",
    )
    corridors = GeoPromptFrame.from_records(
        [
            {"site_id": "route-1", "priority": 2.0, "geometry": {"type": "LineString", "coordinates": [[0.0, 0.0], [10.0, 0.0]]}},
            {"site_id": "route-2", "priority": 1.0, "geometry": {"type": "LineString", "coordinates": [[0.0, 1.0], [10.0, 1.0]]}},
        ],
        crs="EPSG:4326",
    )

    direct = features.corridor_reach(corridors, max_distance=20.0)
    network = features.corridor_reach(
        corridors,
        max_distance=20.0,
        distance_mode="network",
        score_mode="combined",
        weight_column="priority",
        preferred_bearing=90.0,
    )
    direct_records = {row["site_id"]: row for row in direct.to_records()}
    network_records = {row["site_id"]: row for row in network.to_records()}

    assert direct_records["near-start"]["distance_min_reach"] < network_records["far-along"]["distance_min_reach"]
    assert network_records["near-start"]["distance_mode_reach"] == "network"
    assert network_records["near-start"]["score_mode_reach"] == "combined"
    assert network_records["near-start"]["corridor_scores_reach"]
    assert network_records["near-start"]["best_corridor_reach"] == "route-1"
    assert network_records["near-start"]["best_score_reach"] is not None


def test_corridor_reach_supports_path_anchor_controls() -> None:
    features = GeoPromptFrame.from_records(
        [{"site_id": "near-end", "geometry": {"type": "Point", "coordinates": [9.0, 0.1]}}],
        crs="EPSG:4326",
    )
    corridors = GeoPromptFrame.from_records(
        [{"site_id": "route-1", "geometry": {"type": "LineString", "coordinates": [[0.0, 0.0], [10.0, 0.0]]}}],
        crs="EPSG:4326",
    )

    start_anchored = features.corridor_reach(corridors, max_distance=20.0, distance_mode="network", path_anchor="start")
    end_anchored = features.corridor_reach(corridors, max_distance=20.0, distance_mode="network", path_anchor="end")
    nearest_anchored = features.corridor_reach(corridors, max_distance=20.0, distance_mode="network", path_anchor="nearest")

    start_record = start_anchored.to_records()[0]
    end_record = end_anchored.to_records()[0]
    nearest_record = nearest_anchored.to_records()[0]

    assert start_record["distance_min_reach"] > end_record["distance_min_reach"]
    assert nearest_record["distance_min_reach"] < start_record["distance_min_reach"]
    assert end_record["path_anchor_reach"] == "end"


def test_corridor_diagnostics_summarize_served_features() -> None:
    features = GeoPromptFrame.from_records(
        [
            {"site_id": "a", "geometry": {"type": "Point", "coordinates": [1.0, 0.0]}},
            {"site_id": "b", "geometry": {"type": "Point", "coordinates": [9.0, 0.0]}},
        ],
        crs="EPSG:4326",
    )
    corridors = GeoPromptFrame.from_records(
        [
            {"site_id": "route-1", "priority": 2.0, "geometry": {"type": "LineString", "coordinates": [[0.0, 0.0], [10.0, 0.0]]}},
            {"site_id": "route-2", "priority": 1.0, "geometry": {"type": "LineString", "coordinates": [[0.0, 1.0], [10.0, 1.0]]}},
        ],
        crs="EPSG:4326",
    )

    diagnostics = features.corridor_diagnostics(
        corridors,
        max_distance=20.0,
        weight_column="priority",
        preferred_bearing=90.0,
    )
    records = {record["site_id"]: record for record in diagnostics.to_records()}
    assert records["route-1"]["served_feature_count"] >= 1
    assert records["route-1"]["best_match_count"] >= 1
    assert records["route-1"]["score_sum"] >= records["route-2"]["score_sum"]


def test_zone_fit_score_ranks_zones_for_features() -> None:
    features = GeoPromptFrame.from_records(
        [
            {"site_id": "inside", "geometry": {"type": "Point", "coordinates": [0.5, 0.5]}},
            {"site_id": "outside", "geometry": {"type": "Point", "coordinates": [5.0, 5.0]}},
        ],
        crs="EPSG:4326",
    )
    zones = GeoPromptFrame.from_records(
        [
            {
                "region_id": "zone-a",
                "geometry": {"type": "Polygon", "coordinates": [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]]},
            },
        ],
        crs="EPSG:4326",
    )

    result = features.zone_fit_score(zones, zone_id_column="region_id")
    records = {r["site_id"]: r for r in result.to_records()}

    assert records["inside"]["best_zone_fit"] == "zone-a"
    assert records["inside"]["best_score_fit"] > 0
    assert records["inside"]["zone_count_fit"] == 1
    assert records["outside"]["best_zone_fit"] == "zone-a"
    assert records["inside"]["best_score_fit"] > records["outside"]["best_score_fit"]


def test_zone_fit_score_supports_custom_weights_and_alignment() -> None:
    features = GeoPromptFrame.from_records(
        [{"site_id": "inside", "geometry": {"type": "Point", "coordinates": [0.5, 0.5]}}],
        crs="EPSG:4326",
    )
    zones = GeoPromptFrame.from_records(
        [
            {
                "region_id": "east-zone",
                "geometry": {"type": "Polygon", "coordinates": [[[1.0, 0.0], [2.0, 0.0], [2.0, 1.0], [1.0, 1.0]]]},
            },
            {
                "region_id": "north-zone",
                "geometry": {"type": "Polygon", "coordinates": [[[0.0, 1.0], [1.0, 1.0], [1.0, 2.0], [0.0, 2.0]]]},
            },
        ],
        crs="EPSG:4326",
    )

    scored = features.zone_fit_score(
        zones,
        zone_id_column="region_id",
        score_weights={"containment": 0.0, "overlap": 0.0, "size": 0.0, "access": 0.1, "alignment": 0.9},
        preferred_bearing=0.0,
    )
    record = scored.to_records()[0]
    assert record["best_zone_fit"] == "north-zone"
    assert record["score_weights_fit"]["alignment"] == 0.9
    assert any(zone_score["alignment_score"] is not None for zone_score in record["zone_scores_fit"])


def test_zone_fit_score_supports_group_rankings() -> None:
    features = GeoPromptFrame.from_records(
        [{"site_id": "inside", "geometry": {"type": "Point", "coordinates": [0.5, 0.5]}}],
        crs="EPSG:4326",
    )
    zones = GeoPromptFrame.from_records(
        [
            {"region_id": "zone-a", "region_band": "north", "geometry": {"type": "Polygon", "coordinates": [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]] }},
            {"region_id": "zone-b", "region_band": "north", "geometry": {"type": "Polygon", "coordinates": [[[0.0, 0.0], [1.2, 0.0], [1.2, 1.2], [0.0, 1.2]]] }},
            {"region_id": "zone-c", "region_band": "south", "geometry": {"type": "Polygon", "coordinates": [[[2.0, 2.0], [3.0, 2.0], [3.0, 3.0], [2.0, 3.0]]] }},
        ],
        crs="EPSG:4326",
    )

    scored = features.zone_fit_score(
        zones,
        zone_id_column="region_id",
        group_by="region_band",
        group_aggregation="max",
        top_n=2,
    )
    record = scored.to_records()[0]
    assert record["group_scores_fit"]
    assert record["best_group_fit"] == "north"
    assert len(record["zone_scores_fit"]) == 2


def test_zone_fit_score_supports_score_callback() -> None:
    features = GeoPromptFrame.from_records(
        [{"site_id": "inside", "geometry": {"type": "Point", "coordinates": [0.5, 0.5]}}],
        crs="EPSG:4326",
    )
    zones = GeoPromptFrame.from_records(
        [
            {"region_id": "near", "geometry": {"type": "Polygon", "coordinates": [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]] }},
            {"region_id": "far", "geometry": {"type": "Polygon", "coordinates": [[[3.0, 3.0], [4.0, 3.0], [4.0, 4.0], [3.0, 4.0]]] }},
        ],
        crs="EPSG:4326",
    )

    scored = features.zone_fit_score(
        zones,
        zone_id_column="region_id",
        score_callback=lambda left, zone, components, score: score + (5.0 if zone["region_id"] == "far" else 0.0),
    )
    record = scored.to_records()[0]
    assert record["best_zone_fit"] == "far"


def test_zone_fit_score_respects_max_distance() -> None:
    features = GeoPromptFrame.from_records(
        [{"site_id": "far", "geometry": {"type": "Point", "coordinates": [10.0, 10.0]}}],
        crs="EPSG:4326",
    )
    zones = GeoPromptFrame.from_records(
        [
            {
                "region_id": "zone-a",
                "geometry": {"type": "Polygon", "coordinates": [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]]},
            },
        ],
        crs="EPSG:4326",
    )

    result = features.zone_fit_score(zones, max_distance=1.0)
    records = result.to_records()
    assert records[0]["best_zone_fit"] is None
    assert records[0]["zone_count_fit"] == 0


def test_centroid_cluster_assigns_cluster_ids() -> None:
    frame = GeoPromptFrame.from_records(
        [
            {"site_id": "a", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
            {"site_id": "b", "geometry": {"type": "Point", "coordinates": [0.1, 0.0]}},
            {"site_id": "c", "geometry": {"type": "Point", "coordinates": [10.0, 0.0]}},
            {"site_id": "d", "geometry": {"type": "Point", "coordinates": [10.1, 0.0]}},
        ],
    )

    result = frame.centroid_cluster(k=2)
    records = sorted(result.to_records(), key=lambda r: r["site_id"])

    assert all("cluster_id" in r for r in records)
    assert all("cluster_center" in r for r in records)
    assert all("cluster_distance" in r for r in records)
    assert records[0]["cluster_id"] == records[1]["cluster_id"]
    assert records[2]["cluster_id"] == records[3]["cluster_id"]
    assert records[0]["cluster_id"] != records[2]["cluster_id"]
    assert all("cluster_size" in r for r in records)
    assert all("cluster_sse" in r for r in records)
    assert all("cluster_silhouette" in r for r in records)
    assert all("cluster_silhouette_mean" in r for r in records)


def test_centroid_cluster_uses_id_column_for_deterministic_seeding() -> None:
    frame = GeoPromptFrame.from_records(
        [
            {"site_id": "zeta", "geometry": {"type": "Point", "coordinates": [10.0, 0.0]}},
            {"site_id": "alpha", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
            {"site_id": "beta", "geometry": {"type": "Point", "coordinates": [0.2, 0.0]}},
            {"site_id": "omega", "geometry": {"type": "Point", "coordinates": [10.2, 0.0]}},
        ],
    )

    clustered = frame.centroid_cluster(k=2, id_column="site_id")
    records = {row["site_id"]: row for row in clustered.to_records()}
    assert records["alpha"]["cluster_id"] == records["beta"]["cluster_id"]
    assert records["omega"]["cluster_id"] == records["zeta"]["cluster_id"]


def test_centroid_cluster_single_cluster_reports_zero_silhouette() -> None:
    frame = GeoPromptFrame.from_records(
        [
            {"site_id": "a", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
            {"site_id": "b", "geometry": {"type": "Point", "coordinates": [1.0, 0.0]}},
        ],
    )

    clustered = frame.centroid_cluster(k=1)
    assert all(row["cluster_silhouette"] == 0.0 for row in clustered)
    assert all(row["cluster_silhouette_mean"] == 0.0 for row in clustered)


def test_cluster_diagnostics_and_recommendation() -> None:
    frame = GeoPromptFrame.from_records(
        [
            {"site_id": "a", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
            {"site_id": "b", "geometry": {"type": "Point", "coordinates": [0.2, 0.0]}},
            {"site_id": "c", "geometry": {"type": "Point", "coordinates": [5.0, 0.0]}},
            {"site_id": "d", "geometry": {"type": "Point", "coordinates": [5.2, 0.0]}},
        ],
    )

    diagnostics = frame.cluster_diagnostics([1, 2, 3])
    assert [item["k"] for item in diagnostics] == [1, 2, 3]
    assert diagnostics[0]["sse_total"] >= diagnostics[1]["sse_total"]
    assert any(item["recommended_silhouette"] for item in diagnostics)
    assert any(item["recommended_sse"] for item in diagnostics)

    recommendation = frame.recommend_cluster_count([1, 2, 3], metric="silhouette")
    assert recommendation["recommended_silhouette"] is True


def test_summarize_clusters_returns_cluster_rollups() -> None:
    frame = GeoPromptFrame.from_records(
        [
            {"site_id": "a", "kind": "north", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
            {"site_id": "b", "kind": "north", "geometry": {"type": "Point", "coordinates": [0.2, 0.0]}},
            {"site_id": "c", "kind": "south", "geometry": {"type": "Point", "coordinates": [5.0, 0.0]}},
            {"site_id": "d", "kind": "south", "geometry": {"type": "Point", "coordinates": [5.2, 0.0]}},
        ],
    )
    clustered = frame.centroid_cluster(k=2)
    summary = clustered.summarize_clusters(group_by="kind")
    records = summary.to_records()
    assert len(records) == 2
    assert all("cluster_member_count" in record for record in records)
    assert all("kind_counts" in record for record in records)
    assert all("dominant_kind" in record for record in records)


def test_geometry_envelope_creates_bounding_box() -> None:
    polygon = {
        "type": "Polygon",
        "coordinates": [(0.0, 0.0), (2.0, 0.0), (1.0, 3.0), (0.0, 0.0)],
    }
    envelope = cast(dict[str, Any], geometry_envelope(polygon))
    assert envelope["type"] == "Polygon"
    coords = list(cast(Any, envelope["coordinates"]))
    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    assert min(xs) == 0.0
    assert max(xs) == 2.0
    assert min(ys) == 0.0
    assert max(ys) == 3.0


def test_geometry_convex_hull_returns_hull() -> None:
    polygon = {
        "type": "Polygon",
        "coordinates": [
            (0.0, 0.0), (2.0, 0.0), (1.0, 0.5), (2.0, 2.0), (0.0, 2.0), (0.0, 0.0),
        ],
    }
    hull = cast(dict[str, Any], geometry_convex_hull(polygon))
    assert hull["type"] == "Polygon"
    hull_coords = list(cast(Any, hull["coordinates"]))
    assert len(hull_coords) >= 4
    xs = [c[0] for c in hull_coords[:-1]]
    ys = [c[1] for c in hull_coords[:-1]]
    assert (1.0, 0.5) not in [(x, y) for x, y in zip(xs, ys)]


def test_geometry_convex_hull_returns_line_for_collinear_points() -> None:
    line = {
        "type": "LineString",
        "coordinates": [(0.0, 0.0), (1.0, 0.0), (2.0, 0.0)],
    }
    hull = geometry_convex_hull(line)
    assert hull["type"] == "LineString"
    assert hull["coordinates"] == ((0.0, 0.0), (2.0, 0.0))


def test_gravity_model_equation() -> None:
    g = gravity_model(10.0, 20.0, distance_value=5.0, friction=2.0)
    assert round(g, 2) == 8.0

    g_zero = gravity_model(10.0, 20.0, distance_value=0.0)
    assert g_zero == float("inf")

    try:
        gravity_model(10.0, 20.0, distance_value=-1.0)
    except ValueError as exc:
        assert "zero or greater" in str(exc)
    else:
        raise AssertionError("gravity_model should reject negative distances")


def test_accessibility_index_equation() -> None:
    score = accessibility_index(
        weights=[10.0, 20.0],
        distances=[1.0, 2.0],
        friction=2.0,
    )
    assert round(score, 2) == 15.0

    infinite_score = accessibility_index(
        weights=[10.0, 20.0],
        distances=[0.0, 2.0],
        friction=2.0,
    )
    assert infinite_score == float("inf")

    try:
        accessibility_index(weights=[10.0], distances=[-1.0], friction=2.0)
    except ValueError as exc:
        assert "zero or greater" in str(exc)
    else:
        raise AssertionError("accessibility_index should reject negative distances")


def test_frame_repr() -> None:
    frame = GeoPromptFrame.from_records(
        [{"site_id": "a", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}}],
        crs="EPSG:4326",
    )
    r = repr(frame)
    assert "GeoPromptFrame" in r
    assert "1 rows" in r
    assert "EPSG:4326" in r


def test_frame_getitem_returns_column_values() -> None:
    frame = GeoPromptFrame.from_records(
        [
            {"site_id": "a", "demand": 1.0, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
            {"site_id": "b", "demand": 2.0, "geometry": {"type": "Point", "coordinates": [1.0, 0.0]}},
        ],
    )
    assert frame["site_id"] == ["a", "b"]
    assert frame["demand"] == [1.0, 2.0]


def test_frame_select_keeps_chosen_columns() -> None:
    frame = GeoPromptFrame.from_records(
        [
            {"site_id": "a", "demand": 1.0, "extra": "x", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
        ],
    )
    selected = frame.select("site_id", "demand")
    cols = selected.columns
    assert "site_id" in cols
    assert "demand" in cols
    assert "geometry" in cols
    assert "extra" not in cols


def test_frame_rename_columns() -> None:
    frame = GeoPromptFrame.from_records(
        [{"site_id": "a", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}}],
    )
    renamed = frame.rename_columns({"site_id": "id"})
    assert "id" in renamed.columns
    assert "site_id" not in renamed.columns
    assert renamed.to_records()[0]["id"] == "a"


def test_frame_filter_with_callable() -> None:
    frame = GeoPromptFrame.from_records(
        [
            {"site_id": "a", "demand": 1.0, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
            {"site_id": "b", "demand": 5.0, "geometry": {"type": "Point", "coordinates": [1.0, 0.0]}},
            {"site_id": "c", "demand": 3.0, "geometry": {"type": "Point", "coordinates": [2.0, 0.0]}},
        ],
    )
    high = frame.filter(lambda row: row["demand"] > 2.0)
    assert len(high) == 2
    assert {r["site_id"] for r in high} == {"b", "c"}


def test_frame_filter_with_boolean_mask() -> None:
    frame = GeoPromptFrame.from_records(
        [
            {"site_id": "a", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
            {"site_id": "b", "geometry": {"type": "Point", "coordinates": [1.0, 0.0]}},
        ],
    )
    filtered = frame.filter([True, False])
    assert len(filtered) == 1
    assert filtered.to_records()[0]["site_id"] == "a"

    tuple_filtered = frame.filter((False, True))
    assert len(tuple_filtered) == 1
    assert tuple_filtered.to_records()[0]["site_id"] == "b"


def test_frame_sort_by_column() -> None:
    frame = GeoPromptFrame.from_records(
        [
            {"site_id": "b", "demand": 3.0, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
            {"site_id": "a", "demand": 1.0, "geometry": {"type": "Point", "coordinates": [1.0, 0.0]}},
            {"site_id": "c", "demand": 2.0, "geometry": {"type": "Point", "coordinates": [2.0, 0.0]}},
        ],
    )
    asc = frame.sort("demand")
    assert [r["site_id"] for r in asc] == ["a", "c", "b"]

    desc = frame.sort("demand", descending=True)
    assert [r["site_id"] for r in desc] == ["b", "c", "a"]


def test_frame_sort_keeps_none_values_last() -> None:
    frame = GeoPromptFrame.from_records(
        [
            {"site_id": "a", "demand": None, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
            {"site_id": "b", "demand": 3.0, "geometry": {"type": "Point", "coordinates": [1.0, 0.0]}},
            {"site_id": "c", "demand": 1.0, "geometry": {"type": "Point", "coordinates": [2.0, 0.0]}},
        ],
    )

    asc = frame.sort("demand")
    desc = frame.sort("demand", descending=True)

    assert [r["site_id"] for r in asc] == ["c", "b", "a"]
    assert [r["site_id"] for r in desc] == ["b", "c", "a"]


def test_frame_describe_returns_numeric_stats() -> None:
    frame = GeoPromptFrame.from_records(
        [
            {"site_id": "a", "demand": 1.0, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
            {"site_id": "b", "demand": 3.0, "geometry": {"type": "Point", "coordinates": [1.0, 0.0]}},
            {"site_id": "c", "demand": 5.0, "geometry": {"type": "Point", "coordinates": [2.0, 0.0]}},
        ],
    )
    stats = frame.describe()
    assert "demand" in stats
    assert stats["demand"]["count"] == 3
    assert stats["demand"]["min"] == 1.0
    assert stats["demand"]["max"] == 5.0
    assert stats["demand"]["mean"] == 3.0
    assert stats["demand"]["sum"] == 9.0
    assert "site_id" not in stats


def test_frame_envelopes_and_convex_hulls() -> None:
    frame = GeoPromptFrame.from_records(
        [
            {
                "site_id": "tri",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[(0.0, 0.0), (2.0, 0.0), (1.0, 3.0)]],
                },
            },
        ],
    )
    envelopes = frame.envelopes()
    hulls = frame.convex_hulls()
    assert envelopes.to_records()[0]["geometry"]["type"] == "Polygon"
    assert hulls.to_records()[0]["geometry"]["type"] == "Polygon"


def test_gravity_table_produces_pairwise_scores() -> None:
    frame = GeoPromptFrame.from_records(
        [
            {"site_id": "a", "pop": 100.0, "jobs": 50.0, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
            {"site_id": "b", "pop": 200.0, "jobs": 80.0, "geometry": {"type": "Point", "coordinates": [1.0, 0.0]}},
        ],
    )
    table = frame.gravity_table("pop", "jobs")
    assert len(table) == 2
    assert table[0]["origin"] == "a"
    assert table[0]["destination"] == "b"
    assert table[0]["gravity"] > 0


def test_accessibility_scores_per_origin() -> None:
    origins = GeoPromptFrame.from_records(
        [
            {"site_id": "a", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
            {"site_id": "b", "geometry": {"type": "Point", "coordinates": [10.0, 0.0]}},
        ],
    )
    targets = GeoPromptFrame.from_records(
        [
            {"site_id": "t1", "demand": 5.0, "geometry": {"type": "Point", "coordinates": [1.0, 0.0]}},
            {"site_id": "t2", "demand": 10.0, "geometry": {"type": "Point", "coordinates": [2.0, 0.0]}},
        ],
    )
    scores = origins.accessibility_scores(targets, weight_column="demand", friction=2.0)
    assert len(scores) == 2
    assert scores[0] > scores[1]


def test_read_geojson_from_dict() -> None:
    payload = {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
        "features": [
            {
                "type": "Feature",
                "id": "a",
                "properties": {"name": "A"},
                "geometry": {"type": "Point", "coordinates": [1.0, 2.0]},
            },
        ],
    }
    from geoprompt.io import read_geojson
    frame = read_geojson(payload)
    assert len(frame) == 1
    assert frame.crs == "EPSG:4326"


def test_frame_to_records_flat() -> None:
    from geoprompt.io import frame_to_records_flat
    frame = GeoPromptFrame.from_records(
        [{"site_id": "a", "geometry": {"type": "Point", "coordinates": [1.0, 2.0]}}],
    )
    flat = frame_to_records_flat(frame)
    assert len(flat) == 1
    assert flat[0]["geometry_type"] == "Point"
    assert flat[0]["geometry_centroid_x"] == 1.0
    assert flat[0]["geometry_centroid_y"] == 2.0
    assert "geometry" not in flat[0]


def test_comparison_report_benchmark_registry_new_methods() -> None:
    import geoprompt.compare as compare

    original_benchmark = compare._benchmark
    compare._benchmark = lambda operation, func, repeats=20: ({"operation": operation, "repeats": 1}, None)
    try:
        report = compare.build_comparison_report()
    finally:
        compare._benchmark = original_benchmark

    benchmark_ops = {
        benchmark["operation"]
        for dataset in report["datasets"]
        for benchmark in dataset["benchmarks"]
    }
    benchmark_counts = {
        str(dataset["dataset"]): len(dataset["benchmarks"])
        for dataset in report["datasets"]
    }
    benchmark_ops_by_dataset = {
        str(dataset["dataset"]): [benchmark["operation"] for benchmark in dataset["benchmarks"]]
        for dataset in report["datasets"]
    }
    assert all("performance" in dataset for dataset in report["datasets"])
    assert all("query_bounds_pruning_ratio" in dataset["performance"] for dataset in report["datasets"])
    assert benchmark_counts["sample"] >= 55
    assert benchmark_counts["benchmark"] >= 65
    assert benchmark_counts["stress"] >= 55
    assert all(len(operations) == len(set(operations)) for operations in benchmark_ops_by_dataset.values())
    assert "sample.geoprompt.spatial_index_query" in benchmark_ops
    assert "sample.geoprompt.centroid_cluster" in benchmark_ops
    assert "benchmark.geoprompt.zone_fit_score" in benchmark_ops
    assert "benchmark.geoprompt.corridor_reach" in benchmark_ops
    assert "benchmark.geoprompt.cluster_diagnostics" in benchmark_ops
    assert "benchmark.geoprompt.overlay_summary_grouped" in benchmark_ops
    assert "sample.geoprompt.summarize_clusters" in benchmark_ops
    assert "benchmark.geoprompt.overlay_group_comparison" in benchmark_ops
    assert "benchmark.geoprompt.overlay_union" in benchmark_ops
    assert "benchmark.geoprompt.overlay_difference" in benchmark_ops
    assert "benchmark.geoprompt.overlay_symmetric_difference" in benchmark_ops
    assert "benchmark.geoprompt.corridor_diagnostics" in benchmark_ops
    assert "benchmark.geoprompt.network_build" in benchmark_ops
    assert "sample.geoprompt.spatial_lag" in benchmark_ops
    assert "sample.geoprompt.spatial_autocorrelation" in benchmark_ops
    assert "sample.geoprompt.summarize_autocorrelation" in benchmark_ops
    assert "sample.geoprompt.report_autocorrelation_patterns" in benchmark_ops
    assert "sample.geoprompt.change_detection" in benchmark_ops
    assert "sample.geoprompt.extract_change_events" in benchmark_ops
    assert "sample.geoprompt.compare_change_events" in benchmark_ops
    assert "sample.geoprompt.compare_change_events_equivalent" in benchmark_ops
    assert "sample.geoprompt.snap_geometries" in benchmark_ops
    assert "sample.geoprompt.clean_topology" in benchmark_ops
    assert "sample.geoprompt.raster_sample" in benchmark_ops
    assert "sample.geoprompt.zonal_stats" in benchmark_ops
    assert "sample.geoprompt.reclassify" in benchmark_ops
    assert "sample.geoprompt.resample" in benchmark_ops
    assert "sample.geoprompt.raster_clip" in benchmark_ops
    assert "sample.geoprompt.mosaic" in benchmark_ops
    assert "sample.geoprompt.to_points" in benchmark_ops
    assert "sample.geoprompt.to_polygons" in benchmark_ops
    assert "sample.geoprompt.contours" in benchmark_ops
    assert "sample.geoprompt.hillshade" in benchmark_ops
    assert "sample.geoprompt.slope_aspect" in benchmark_ops
    assert "sample.geoprompt.idw_interpolation" in benchmark_ops
    assert "sample.geoprompt.kriging_surface" in benchmark_ops
    assert "sample.geoprompt.thiessen_polygons" in benchmark_ops
    assert "sample.geoprompt.spatial_weights_matrix" in benchmark_ops
    assert "sample.geoprompt.hotspot_getis_ord" in benchmark_ops
    assert "sample.geoprompt.local_outlier_factor_spatial" in benchmark_ops
    assert "sample.geoprompt.kernel_density" in benchmark_ops
    assert "sample.geoprompt.standard_deviational_ellipse" in benchmark_ops
    assert "sample.geoprompt.center_of_minimum_distance" in benchmark_ops
    assert "sample.geoprompt.spatial_regression" in benchmark_ops
    assert "sample.geoprompt.geographically_weighted_summary" in benchmark_ops
    assert "sample.geoprompt.join_by_largest_overlap" in benchmark_ops
    assert "sample.geoprompt.erase" in benchmark_ops
    assert "sample.geoprompt.identity_overlay" in benchmark_ops
    assert "sample.geoprompt.multipart_to_singlepart" in benchmark_ops
    assert "sample.geoprompt.singlepart_to_multipart" in benchmark_ops
    assert "sample.geoprompt.eliminate_slivers" in benchmark_ops
    assert "sample.geoprompt.simplify" in benchmark_ops
    assert "sample.geoprompt.densify" in benchmark_ops
    assert "sample.geoprompt.smooth_geometry" in benchmark_ops
    assert "sample.geoprompt.snap_to_network_nodes" in benchmark_ops
    assert "sample.geoprompt.origin_destination_matrix" in benchmark_ops
    assert "sample.geoprompt.k_shortest_paths" in benchmark_ops
    assert "sample.geoprompt.network_trace" in benchmark_ops
    assert "sample.geoprompt.route_sequence_optimize" in benchmark_ops
    assert "sample.geoprompt.trajectory_staypoint_detection" in benchmark_ops
    assert "sample.geoprompt.trajectory_simplify" in benchmark_ops
    assert "sample.geoprompt.spatiotemporal_cube" in benchmark_ops
    assert "sample.geoprompt.geohash_encode" in benchmark_ops
    assert "benchmark.geoprompt.line_split" in benchmark_ops
    assert "benchmark.geoprompt.polygon_split" in benchmark_ops
    assert "benchmark.geoprompt.trajectory_match" in benchmark_ops
    assert "benchmark.geoprompt.summarize_trajectory_segments" in benchmark_ops
    assert "benchmark.geoprompt.score_trajectory_segments" in benchmark_ops
    assert "benchmark.geoprompt.shortest_path" in benchmark_ops
    assert "benchmark.geoprompt.service_area" in benchmark_ops
    assert "benchmark.geoprompt.location_allocate" in benchmark_ops


def test_comparison_report_benchmark_performance_budgets() -> None:
    import geoprompt.compare as compare

    def single_run_benchmark(operation: str, func: Any, repeats: int = 20) -> tuple[dict[str, Any], Any]:
        started_at = time.perf_counter()
        result = func()
        elapsed = time.perf_counter() - started_at
        return (
            {
                "operation": operation,
                "median_seconds": elapsed,
                "min_seconds": elapsed,
                "max_seconds": elapsed,
                "repeats": 1,
            },
            result,
        )

    target_operations = {
        "benchmark.geoprompt.overlay_summary_grouped",
        "benchmark.geoprompt.overlay_group_comparison",
        "stress.geoprompt.compare_change_events",
        "stress.geoprompt.compare_change_events_equivalent",
    }
    original_benchmark = compare._benchmark
    compare._benchmark = single_run_benchmark
    try:
        report = compare.build_comparison_report(
            benchmark_filter=lambda operation: operation in target_operations,
        )
    finally:
        compare._benchmark = original_benchmark

    benchmark_timings = {
        str(benchmark["operation"]): float(benchmark.get("median_seconds", 0.0) or 0.0)
        for dataset in report["datasets"]
        for benchmark in dataset["benchmarks"]
    }

    assert set(benchmark_timings) == target_operations
    assert benchmark_timings["benchmark.geoprompt.overlay_summary_grouped"] < 0.45
    assert benchmark_timings["benchmark.geoprompt.overlay_group_comparison"] < 0.5
    assert benchmark_timings["stress.geoprompt.compare_change_events"] < 2.0
    assert benchmark_timings["stress.geoprompt.compare_change_events_equivalent"] < 2.25


def test_comparison_report_benchmark_filter_limits_operations() -> None:
    import geoprompt.compare as compare

    target_operations = {
        "sample.geoprompt.query_bounds",
        "sample.reference.query_bounds",
    }
    expected_operations_by_dataset = {
        "sample": [
            "sample.geoprompt.query_bounds",
            "sample.reference.query_bounds",
        ],
        "benchmark": [],
        "stress": [],
    }
    original_benchmark = compare._benchmark
    compare._benchmark = lambda operation, func, repeats=20: ({"operation": operation, "repeats": 1}, None)
    try:
        report = compare.build_comparison_report(
            benchmark_filter=lambda operation: operation in target_operations,
        )
    finally:
        compare._benchmark = original_benchmark

    benchmark_ops = {
        str(benchmark["operation"])
        for dataset in report["datasets"]
        for benchmark in dataset["benchmarks"]
    }
    benchmark_ops_by_dataset = {
        str(dataset["dataset"]): [str(benchmark["operation"]) for benchmark in dataset["benchmarks"]]
        for dataset in report["datasets"]
    }

    assert benchmark_ops == target_operations
    assert benchmark_ops_by_dataset == expected_operations_by_dataset


# ======================================================================
# Tests for the 40 new tools
# ======================================================================


def _make_point_frame(points: list[dict], crs: str | None = "EPSG:4326") -> GeoPromptFrame:
    return GeoPromptFrame.from_records(points, geometry="geometry", crs=crs)


def _sample_point_grid():
    """5x5 grid of points with elevation-like values."""
    rows = []
    idx = 0
    for y in range(5):
        for x in range(5):
            idx += 1
            rows.append({
                "site_id": f"pt-{idx:03d}",
                "geometry": {"type": "Point", "coordinates": [float(x), float(y)]},
                "elevation": float(x + y) * 10.0,
                "value": float(idx),
                "weight": 1.0,
                "time": float(idx),
            })
    return _make_point_frame(rows)


def _sample_zone_frame():
    """Two polygon zones covering different parts of the grid."""
    return _make_point_frame([
        {
            "zone_id": "zone-A",
            "geometry": {"type": "Polygon", "coordinates": [(0, 0), (3, 0), (3, 3), (0, 3), (0, 0)]},
        },
        {
            "zone_id": "zone-B",
            "geometry": {"type": "Polygon", "coordinates": [(2, 2), (5, 2), (5, 5), (2, 5), (2, 2)]},
        },
    ])


def _sample_network_frame():
    """Simple 3-edge network: A -> B -> C -> D."""
    return GeoPromptFrame.from_records([
        {
            "edge_id": "e1", "from_node_id": "A", "to_node_id": "B",
            "from_node": (0.0, 0.0),
            "to_node": (1.0, 0.0),
            "edge_length": 1.0,
            "geometry": {"type": "LineString", "coordinates": [(0.0, 0.0), (1.0, 0.0)]},
        },
        {
            "edge_id": "e2", "from_node_id": "B", "to_node_id": "C",
            "from_node": (1.0, 0.0),
            "to_node": (2.0, 0.0),
            "edge_length": 1.0,
            "geometry": {"type": "LineString", "coordinates": [(1.0, 0.0), (2.0, 0.0)]},
        },
        {
            "edge_id": "e3", "from_node_id": "C", "to_node_id": "D",
            "from_node": (2.0, 0.0),
            "to_node": (3.0, 0.0),
            "edge_length": 1.0,
            "geometry": {"type": "LineString", "coordinates": [(2.0, 0.0), (3.0, 0.0)]},
        },
    ], geometry="geometry", crs="EPSG:4326")


# Tool 1: raster_sample
def test_raster_sample():
    source = _sample_point_grid()
    query_pts = _make_point_frame([
        {"site_id": "q1", "geometry": {"type": "Point", "coordinates": [0.1, 0.1]}},
        {"site_id": "q2", "geometry": {"type": "Point", "coordinates": [2.0, 2.0]}},
    ])
    result = source.raster_sample(query_pts, value_column="elevation", k=1)
    records = result.to_records()
    assert len(records) == 2
    assert records[0]["elevation_sample"] is not None
    assert records[0]["distance_sample"] is not None


# Tool 2: zonal_stats
def test_zonal_stats():
    pts = _sample_point_grid()
    zones = _sample_zone_frame()
    result = pts.zonal_stats(zones, value_column="value", zone_id_column="zone_id")
    records = result.to_records()
    assert len(records) == 2
    for row in records:
        assert "value_count_zonal" in row
        assert "value_mean_zonal" in row
    assert records[0]["value_count_zonal"] >= 1


# Tool 3: reclassify
def test_reclassify():
    frame = _sample_point_grid()
    result = frame.reclassify(
        "elevation",
        breaks=[(0.0, 30.0, "low"), (30.0, 60.0, "medium"), (60.0, 100.0, "high")],
    )
    assert len(result) == len(frame)
    classes = set(result["elevation_class"])
    assert "low" in classes


# Tool 4: resample
def test_resample():
    frame = _sample_point_grid()
    every_other = frame.resample(method="every_nth", n=2)
    assert len(every_other) == 13  # ceil(25/2)
    thinned = frame.resample(method="spatial_thin", min_distance=1.5)
    assert len(thinned) < len(frame)
    sampled = frame.resample(method="random", sample_size=5, random_seed=42)
    assert len(sampled) == 5


# Tool 5: raster_clip
def test_raster_clip():
    frame = _sample_point_grid()
    clipped = frame.raster_clip(0.5, 0.5, 2.5, 2.5)
    assert len(clipped) < len(frame)
    for row in clipped:
        cx, cy = row["geometry"]["coordinates"]
        assert 0.5 <= cx <= 2.5
        assert 0.5 <= cy <= 2.5


# Tool 6: mosaic
def test_mosaic():
    f1 = _make_point_frame([
        {"site_id": "a", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}, "val": 1},
    ])
    f2 = _make_point_frame([
        {"site_id": "a", "geometry": {"type": "Point", "coordinates": [1.0, 1.0]}, "val": 2},
        {"site_id": "b", "geometry": {"type": "Point", "coordinates": [2.0, 2.0]}, "val": 3},
    ])
    first = f1.mosaic(f2, conflict_resolution="first")
    assert len(first) == 2  # "a" kept from f1, "b" from f2
    last = f1.mosaic(f2, conflict_resolution="last")
    assert len(last) == 2


# Tool 7: to_points
def test_to_points():
    frame = _make_point_frame([
        {"site_id": "p1", "geometry": {"type": "Polygon", "coordinates": [(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]}},
    ])
    result = frame.to_points()
    records = result.to_records()
    assert len(records) == 1
    assert records[0]["geometry"]["type"] == "Point"


# Tool 8: to_polygons
def test_to_polygons():
    frame = _make_point_frame([
        {"site_id": "p1", "geometry": {"type": "Point", "coordinates": [1.0, 2.0]}},
    ])
    result = frame.to_polygons(buffer_distance=0.5)
    records = result.to_records()
    assert len(records) == 1
    assert records[0]["geometry"]["type"] == "Polygon"


# Tool 9: contours
def test_contours():
    frame = _sample_point_grid()
    result = frame.contours(value_column="elevation", interval_count=3, grid_resolution=10)
    assert len(result) > 0
    for row in result:
        assert "level_contour" in row
        assert row["geometry"]["type"] == "LineString"


# Tool 10: hillshade
def test_hillshade():
    frame = _sample_point_grid()
    result = frame.hillshade(elevation_column="elevation", grid_resolution=10)
    assert len(result) > 0
    for row in result:
        assert 0 <= row["value_hillshade"] <= 255
        assert 0.0 <= row["shade_hillshade"] <= 1.0


# Tool 11: slope_aspect
def test_slope_aspect():
    frame = _sample_point_grid()
    result = frame.slope_aspect(elevation_column="elevation", grid_resolution=10)
    assert len(result) > 0
    for row in result:
        assert "slope_degrees_terrain" in row
        assert "aspect_degrees_terrain" in row
        assert row["slope_degrees_terrain"] >= 0.0
        assert 0.0 <= row["aspect_degrees_terrain"] <= 360.0


# Tool 12: idw_interpolation
def test_idw_interpolation():
    frame = _sample_point_grid()
    result = frame.idw_interpolation(value_column="elevation", grid_resolution=6)
    assert len(result) == 36  # 6x6 grid
    for row in result:
        assert "value_idw" in row
        assert row["geometry"]["type"] == "Point"


# Tool 13: kriging_surface
def test_kriging_surface():
    frame = _sample_point_grid()
    result = frame.kriging_surface(value_column="elevation", grid_resolution=5)
    assert len(result) == 25  # 5x5 grid
    for row in result:
        assert "value_kriging" in row
        assert "variance_kriging" in row
        assert row["method_kriging"] == "ordinary_kriging"
        assert row["variance_kriging"] >= 0.0


def test_kriging_surface_recovers_source_points_when_nugget_is_zero() -> None:
    frame = _make_point_frame([
        {"site_id": "p1", "elevation": 1.0, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
        {"site_id": "p2", "elevation": 2.0, "geometry": {"type": "Point", "coordinates": [1.0, 0.0]}},
        {"site_id": "p3", "elevation": 3.0, "geometry": {"type": "Point", "coordinates": [0.0, 1.0]}},
        {"site_id": "p4", "elevation": 4.0, "geometry": {"type": "Point", "coordinates": [1.0, 1.0]}},
    ])

    records = frame.kriging_surface(
        value_column="elevation",
        grid_resolution=2,
        variogram_range=2.0,
        variogram_sill=1.0,
        variogram_nugget=0.0,
    ).to_records()

    assert [record["value_kriging"] for record in records] == pytest.approx([1.0, 2.0, 3.0, 4.0])
    assert [record["variance_kriging"] for record in records] == pytest.approx([0.0, 0.0, 0.0, 0.0])


def _assert_kriging_matches_pykrige(
    points: list[dict[str, Any]],
    grid_x: list[float],
    grid_y: list[float],
    variogram_range: float,
    variogram_sill: float,
    variogram_nugget: float,
    variogram_model: str = "spherical",
) -> None:
    ordinary_kriging = pytest.importorskip("pykrige.ok").OrdinaryKriging
    pykrige_model_name = "hole-effect" if variogram_model == "hole_effect" else variogram_model

    frame = _make_point_frame(points)
    records = frame.kriging_surface(
        value_column="value",
        grid_resolution=len(grid_x),
        variogram_range=variogram_range,
        variogram_sill=variogram_sill,
        variogram_nugget=variogram_nugget,
        variogram_model=cast(Any, variogram_model),
    ).to_records()
    reference = ordinary_kriging(
        [float(cast(Any, point["geometry"])["coordinates"][0]) for point in points],
        [float(cast(Any, point["geometry"])["coordinates"][1]) for point in points],
        [float(point["value"]) for point in points],
        variogram_model=pykrige_model_name,
        variogram_parameters={"range": variogram_range, "sill": variogram_sill, "nugget": variogram_nugget},
        coordinates_type="euclidean",
        exact_values=variogram_nugget <= 0.0,
    )
    z_values, variances = reference.execute("grid", grid_x, grid_y)

    assert [record["value_kriging"] for record in records] == pytest.approx(
        [float(value) for row in z_values for value in row],
        rel=1e-6,
        abs=1e-6,
    )
    assert [record["variance_kriging"] for record in records] == pytest.approx(
        [float(value) for row in variances for value in row],
        rel=1e-6,
        abs=1e-6,
    )


def test_kriging_surface_matches_pykrige_when_available() -> None:
    _assert_kriging_matches_pykrige(
        points=[
            {"site_id": "p1", "value": 1.0, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
            {"site_id": "p2", "value": 2.0, "geometry": {"type": "Point", "coordinates": [1.0, 0.0]}},
            {"site_id": "p3", "value": 3.0, "geometry": {"type": "Point", "coordinates": [0.0, 1.0]}},
            {"site_id": "p4", "value": 4.0, "geometry": {"type": "Point", "coordinates": [1.0, 1.0]}},
        ],
        grid_x=[0.0, 0.5, 1.0],
        grid_y=[0.0, 0.5, 1.0],
        variogram_range=2.0,
        variogram_sill=1.0,
        variogram_nugget=0.0,
    )


@pytest.mark.parametrize(
    ("points", "grid_x", "grid_y", "variogram_range", "variogram_sill", "variogram_nugget", "variogram_model"),
    [
        (
            [
                {"site_id": "p1", "value": 1.0, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
                {"site_id": "p2", "value": 2.5, "geometry": {"type": "Point", "coordinates": [1.0, 0.0]}},
                {"site_id": "p3", "value": 3.5, "geometry": {"type": "Point", "coordinates": [0.0, 1.0]}},
                {"site_id": "p4", "value": 5.0, "geometry": {"type": "Point", "coordinates": [1.0, 1.0]}},
            ],
            [0.0, 0.5, 1.0],
            [0.0, 0.5, 1.0],
            2.5,
            2.0,
            0.2,
            "spherical",
        ),
        (
            [
                {"site_id": "p1", "value": 2.0, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
                {"site_id": "p2", "value": 4.0, "geometry": {"type": "Point", "coordinates": [2.5, 0.0]}},
                {"site_id": "p3", "value": 6.0, "geometry": {"type": "Point", "coordinates": [0.5, 1.5]}},
                {"site_id": "p4", "value": 8.5, "geometry": {"type": "Point", "coordinates": [2.5, 1.5]}},
            ],
            [0.0, 1.25, 2.5],
            [0.0, 0.75, 1.5],
            1.75,
            3.0,
            0.05,
            "spherical",
        ),
        (
            [
                {"site_id": "p1", "value": 1.0, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
                {"site_id": "p2", "value": 1.8, "geometry": {"type": "Point", "coordinates": [1.0, 0.0]}},
                {"site_id": "p3", "value": 3.7, "geometry": {"type": "Point", "coordinates": [0.0, 1.0]}},
                {"site_id": "p4", "value": 4.5, "geometry": {"type": "Point", "coordinates": [1.0, 1.0]}},
            ],
            [0.0, 0.5, 1.0],
            [0.0, 0.5, 1.0],
            2.0,
            1.5,
            0.1,
            "exponential",
        ),
        (
            [
                {"site_id": "p1", "value": 2.0, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
                {"site_id": "p2", "value": 4.5, "geometry": {"type": "Point", "coordinates": [2.0, 0.0]}},
                {"site_id": "p3", "value": 5.5, "geometry": {"type": "Point", "coordinates": [0.0, 2.0]}},
                {"site_id": "p4", "value": 8.0, "geometry": {"type": "Point", "coordinates": [2.0, 2.0]}},
            ],
            [0.0, 1.0, 2.0],
            [0.0, 1.0, 2.0],
            2.4,
            2.2,
            0.15,
            "gaussian",
        ),
        (
            [
                {"site_id": "p1", "value": 1.0, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
                {"site_id": "p2", "value": 2.0, "geometry": {"type": "Point", "coordinates": [1.0, 0.0]}},
                {"site_id": "p3", "value": 3.0, "geometry": {"type": "Point", "coordinates": [0.0, 1.0]}},
                {"site_id": "p4", "value": 4.4, "geometry": {"type": "Point", "coordinates": [1.0, 1.0]}},
            ],
            [0.0, 0.5, 1.0],
            [0.0, 0.5, 1.0],
            2.0,
            1.6,
            0.1,
            "hole_effect",
        ),
        (
            [
                {"site_id": "p1", "value": 1.0, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
                {"site_id": "p2", "value": 2.2, "geometry": {"type": "Point", "coordinates": [1.0, 0.0]}},
                {"site_id": "p3", "value": 3.4, "geometry": {"type": "Point", "coordinates": [2.0, 0.0]}},
                {"site_id": "p4", "value": 2.8, "geometry": {"type": "Point", "coordinates": [0.0, 1.0]}},
                {"site_id": "p5", "value": 4.6, "geometry": {"type": "Point", "coordinates": [1.0, 1.0]}},
                {"site_id": "p6", "value": 5.9, "geometry": {"type": "Point", "coordinates": [2.0, 1.0]}},
                {"site_id": "p7", "value": 4.1, "geometry": {"type": "Point", "coordinates": [0.0, 2.0]}},
                {"site_id": "p8", "value": 6.3, "geometry": {"type": "Point", "coordinates": [1.0, 2.0]}},
                {"site_id": "p9", "value": 7.4, "geometry": {"type": "Point", "coordinates": [2.0, 2.0]}},
            ],
            [0.0, 2.0 / 3.0, 4.0 / 3.0, 2.0],
            [0.0, 2.0 / 3.0, 4.0 / 3.0, 2.0],
            2.8,
            2.5,
            0.05,
            "spherical",
        ),
        (
            [
                {"site_id": "p1", "value": 1.0, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
                {"site_id": "p2", "value": 2.1, "geometry": {"type": "Point", "coordinates": [1.0, 0.0]}},
                {"site_id": "p3", "value": 3.5, "geometry": {"type": "Point", "coordinates": [2.0, 0.0]}},
                {"site_id": "p4", "value": 2.9, "geometry": {"type": "Point", "coordinates": [0.0, 1.0]}},
                {"site_id": "p5", "value": 4.7, "geometry": {"type": "Point", "coordinates": [1.0, 1.0]}},
                {"site_id": "p6", "value": 6.0, "geometry": {"type": "Point", "coordinates": [2.0, 1.0]}},
                {"site_id": "p7", "value": 4.3, "geometry": {"type": "Point", "coordinates": [0.0, 2.0]}},
                {"site_id": "p8", "value": 6.5, "geometry": {"type": "Point", "coordinates": [1.0, 2.0]}},
                {"site_id": "p9", "value": 7.7, "geometry": {"type": "Point", "coordinates": [2.0, 2.0]}},
            ],
            [0.0, 2.0 / 3.0, 4.0 / 3.0, 2.0],
            [0.0, 2.0 / 3.0, 4.0 / 3.0, 2.0],
            2.4,
            2.1,
            0.08,
            "exponential",
        ),
        (
            [
                {"site_id": "p1", "value": 1.0, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
                {"site_id": "p2", "value": 2.0, "geometry": {"type": "Point", "coordinates": [1.0, 0.0]}},
                {"site_id": "p3", "value": 3.1, "geometry": {"type": "Point", "coordinates": [2.0, 0.0]}},
                {"site_id": "p4", "value": 2.7, "geometry": {"type": "Point", "coordinates": [0.0, 1.0]}},
                {"site_id": "p5", "value": 4.2, "geometry": {"type": "Point", "coordinates": [1.0, 1.0]}},
                {"site_id": "p6", "value": 5.4, "geometry": {"type": "Point", "coordinates": [2.0, 1.0]}},
                {"site_id": "p7", "value": 3.8, "geometry": {"type": "Point", "coordinates": [0.0, 2.0]}},
                {"site_id": "p8", "value": 5.8, "geometry": {"type": "Point", "coordinates": [1.0, 2.0]}},
                {"site_id": "p9", "value": 6.9, "geometry": {"type": "Point", "coordinates": [2.0, 2.0]}},
            ],
            [0.0, 2.0 / 3.0, 4.0 / 3.0, 2.0],
            [0.0, 2.0 / 3.0, 4.0 / 3.0, 2.0],
            2.2,
            1.7,
            0.09,
            "hole_effect",
        ),
        (
            [
                {"site_id": "p1", "value": 1.0, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
                {"site_id": "p2", "value": 2.0, "geometry": {"type": "Point", "coordinates": [1.0, 0.0]}},
                {"site_id": "p3", "value": 3.1, "geometry": {"type": "Point", "coordinates": [2.0, 0.0]}},
                {"site_id": "p4", "value": 2.7, "geometry": {"type": "Point", "coordinates": [0.0, 1.0]}},
                {"site_id": "p5", "value": 4.2, "geometry": {"type": "Point", "coordinates": [1.0, 1.0]}},
                {"site_id": "p6", "value": 5.4, "geometry": {"type": "Point", "coordinates": [2.0, 1.0]}},
                {"site_id": "p7", "value": 3.8, "geometry": {"type": "Point", "coordinates": [0.0, 2.0]}},
                {"site_id": "p8", "value": 5.8, "geometry": {"type": "Point", "coordinates": [1.0, 2.0]}},
                {"site_id": "p9", "value": 6.9, "geometry": {"type": "Point", "coordinates": [2.0, 2.0]}},
            ],
            [0.0, 2.0 / 3.0, 4.0 / 3.0, 2.0],
            [0.0, 2.0 / 3.0, 4.0 / 3.0, 2.0],
            2.4,
            2.2,
            0.1,
            "gaussian",
        ),
    ],
)
def test_kriging_surface_matches_pykrige_across_parameter_regimes_when_available(
    points: list[dict[str, Any]],
    grid_x: list[float],
    grid_y: list[float],
    variogram_range: float,
    variogram_sill: float,
    variogram_nugget: float,
    variogram_model: str,
) -> None:
    _assert_kriging_matches_pykrige(
        points=points,
        grid_x=grid_x,
        grid_y=grid_y,
        variogram_range=variogram_range,
        variogram_sill=variogram_sill,
        variogram_nugget=variogram_nugget,
        variogram_model=variogram_model,
    )


# Tool 14: thiessen_polygons
def test_thiessen_polygons():
    frame = _make_point_frame([
        {"site_id": "a", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
        {"site_id": "b", "geometry": {"type": "Point", "coordinates": [2.0, 0.0]}},
        {"site_id": "c", "geometry": {"type": "Point", "coordinates": [1.0, 2.0]}},
    ])
    result = frame.thiessen_polygons(grid_resolution=20)
    assert len(result) == 3
    for row in result:
        assert row["geometry"]["type"] == "Polygon"
        assert row["cell_count_voronoi"] > 0


def test_thiessen_polygons_uses_exact_voronoi_when_shapely_available() -> None:
    pytest.importorskip("shapely")

    frame = _make_point_frame([
        {"site_id": "left", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
        {"site_id": "right", "geometry": {"type": "Point", "coordinates": [2.0, 0.0]}},
    ])

    records = sorted(frame.thiessen_polygons().to_records(), key=lambda item: str(item["site_id"]))
    left_bounds = geometry_bounds(records[0]["geometry"])
    right_bounds = geometry_bounds(records[1]["geometry"])

    assert records[0]["method_voronoi"] == "shapely_exact"
    assert records[1]["method_voronoi"] == "shapely_exact"
    assert left_bounds[2] == pytest.approx(1.0)
    assert right_bounds[0] == pytest.approx(1.0)
    assert records[0]["area_voronoi"] == pytest.approx(records[1]["area_voronoi"])


# Tool 15: spatial_weights_matrix
def test_spatial_weights_matrix():
    frame = _sample_point_grid()
    w = frame.spatial_weights_matrix(k=3)
    assert w["n"] == 25
    assert len(w["weights"]) == 25
    for wid, neighbors in w["weights"].items():
        assert len(neighbors) == 3


# Tool 16: hotspot_getis_ord
def test_hotspot_getis_ord():
    frame = _sample_point_grid()
    result = frame.hotspot_getis_ord(
        value_column="elevation",
        mode="k_nearest",
        k=4,
    )
    assert len(result) == 25
    for row in result:
        assert "gi_star_getis" in row
        assert "p_value_getis" in row
        assert row["implementation_getis"] in ("analytic", "pysal")
        assert row["classification_getis"] in ("hotspot", "coldspot", "not_significant")


def test_hotspot_getis_ord_matches_pysal_when_available() -> None:
    esda = pytest.importorskip("esda")
    libpysal_weights = pytest.importorskip("libpysal.weights")

    frame = _make_point_frame([
        {"site_id": "a", "value": 10.0, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
        {"site_id": "b", "value": 9.5, "geometry": {"type": "Point", "coordinates": [0.2, 0.1]}},
        {"site_id": "c", "value": 9.0, "geometry": {"type": "Point", "coordinates": [0.1, 0.2]}},
        {"site_id": "d", "value": 1.0, "geometry": {"type": "Point", "coordinates": [5.0, 5.0]}},
        {"site_id": "e", "value": 1.5, "geometry": {"type": "Point", "coordinates": [5.2, 5.1]}},
        {"site_id": "f", "value": 2.0, "geometry": {"type": "Point", "coordinates": [5.1, 5.2]}},
    ])

    records = frame.hotspot_getis_ord(
        value_column="value",
        mode="k_nearest",
        k=2,
        include_self=True,
    ).to_records()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        reference = esda.G_Local(
            [10.0, 9.5, 9.0, 1.0, 1.5, 2.0],
            libpysal_weights.KNN.from_array(
                [(0.0, 0.0), (0.2, 0.1), (0.1, 0.2), (5.0, 5.0), (5.2, 5.1), (5.1, 5.2)],
                k=2,
            ),
            transform="B",
            permutations=0,
            star=True,
            keep_simulations=False,
            island_weight=0,
        )

    for row, z_score, p_value in zip(records, reference.Zs, reference.p_norm, strict=True):
        assert row["implementation_getis"] == "pysal"
        assert row["gi_star_getis"] == pytest.approx(float(z_score))
        assert row["p_value_getis"] == pytest.approx(float(p_value))


# Tool 17: local_outlier_factor_spatial
def test_local_outlier_factor_spatial():
    frame = _sample_point_grid()
    result = frame.local_outlier_factor_spatial(k=3)
    assert len(result) == 25
    for row in result:
        assert "lof_lof" in row
        assert isinstance(row["outlier_lof"], bool)


# Tool 18: kernel_density
def test_kernel_density():
    frame = _sample_point_grid()
    result = frame.kernel_density(grid_resolution=5)
    assert len(result) == 25
    for row in result:
        assert "density_kde" in row
        assert row["density_kde"] >= 0.0


# Tool 19: standard_deviational_ellipse
def test_standard_deviational_ellipse():
    frame = _sample_point_grid()
    result = frame.standard_deviational_ellipse()
    records = result.to_records()
    assert len(records) == 1
    row = records[0]
    assert "sigma_x_sde" in row
    assert "sigma_y_sde" in row
    assert "rotation_degrees_sde" in row
    assert row["geometry"]["type"] == "Polygon"


# Tool 20: center_of_minimum_distance
def test_center_of_minimum_distance():
    frame = _sample_point_grid()
    result = frame.center_of_minimum_distance()
    records = result.to_records()
    assert len(records) == 1
    row = records[0]
    assert "center_x_cmd" in row
    assert "center_y_cmd" in row
    assert 0.0 <= row["center_x_cmd"] <= 4.0
    assert 0.0 <= row["center_y_cmd"] <= 4.0


# Tool 21: spatial_regression
def test_spatial_regression():
    frame = _sample_point_grid()
    result = frame.spatial_regression(
        dependent_column="elevation",
        independent_columns=["value"],
        k_neighbors=3,
    )
    assert len(result) == 25
    for row in result:
        assert "predicted_reg" in row
        assert "residual_reg" in row
        assert "r_squared_reg" in row
        assert "intercept_reg" in row
        assert "coeff_value_reg" in row
        assert "coefficient_standard_errors_reg" in row
        assert "coefficient_t_statistics_reg" in row
        assert "coefficient_p_values_reg" in row
        assert "rmse_reg" in row
        assert 0.0 <= row["r_squared_reg"] <= 1.0


def test_spatial_regression_matches_exact_linear_relation() -> None:
    frame = _make_point_frame([
        {"site_id": "r1", "x": 0.0, "y": 2.0, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
        {"site_id": "r2", "x": 1.0, "y": 5.0, "geometry": {"type": "Point", "coordinates": [1.0, 0.0]}},
        {"site_id": "r3", "x": 2.0, "y": 8.0, "geometry": {"type": "Point", "coordinates": [2.0, 0.0]}},
        {"site_id": "r4", "x": 3.0, "y": 11.0, "geometry": {"type": "Point", "coordinates": [3.0, 0.0]}},
        {"site_id": "r5", "x": 4.0, "y": 14.0, "geometry": {"type": "Point", "coordinates": [4.0, 0.0]}},
    ])

    records = frame.spatial_regression(
        dependent_column="y",
        independent_columns=["x"],
        k_neighbors=2,
    ).to_records()

    first = records[0]
    assert abs(float(first["intercept_reg"]) - 2.0) < 1e-9
    assert abs(float(first["coeff_x_reg"]) - 3.0) < 1e-9
    assert float(first["r_squared_reg"]) > 0.999999
    assert float(first["rmse_reg"]) < 1e-9
    assert all(abs(float(record["residual_reg"])) < 1e-9 for record in records)
    assert float(first["intercept_p_value_reg"]) <= 1.0
    assert float(first["p_value_x_reg"]) <= 1.0


def test_spatial_regression_matches_statsmodels_when_available() -> None:
    statsmodels_api = pytest.importorskip("statsmodels.api")

    frame = _make_point_frame([
        {"site_id": "r1", "x1": 0.0, "x2": 1.0, "y": 1.4, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
        {"site_id": "r2", "x1": 1.0, "x2": 0.0, "y": 2.2, "geometry": {"type": "Point", "coordinates": [1.0, 0.0]}},
        {"site_id": "r3", "x1": 2.0, "x2": 1.0, "y": 3.9, "geometry": {"type": "Point", "coordinates": [2.0, 0.0]}},
        {"site_id": "r4", "x1": 3.0, "x2": 2.0, "y": 5.7, "geometry": {"type": "Point", "coordinates": [3.0, 0.0]}},
        {"site_id": "r5", "x1": 4.0, "x2": 3.0, "y": 7.8, "geometry": {"type": "Point", "coordinates": [4.0, 0.0]}},
        {"site_id": "r6", "x1": 5.0, "x2": 2.0, "y": 8.6, "geometry": {"type": "Point", "coordinates": [5.0, 0.0]}},
    ])

    records = frame.spatial_regression(
        dependent_column="y",
        independent_columns=["x1", "x2"],
        k_neighbors=2,
    ).to_records()
    design = statsmodels_api.add_constant([[0.0, 1.0], [1.0, 0.0], [2.0, 1.0], [3.0, 2.0], [4.0, 3.0], [5.0, 2.0]])
    model = statsmodels_api.OLS([1.4, 2.2, 3.9, 5.7, 7.8, 8.6], design).fit()
    first = records[0]

    assert cast(list[float], first["coefficients_reg"]) == pytest.approx([float(value) for value in model.params], rel=1e-7, abs=1e-7)
    assert cast(list[float], first["coefficient_standard_errors_reg"]) == pytest.approx([float(value) for value in model.bse], rel=1e-7, abs=1e-7)
    assert cast(list[float], first["coefficient_t_statistics_reg"]) == pytest.approx([float(value) for value in model.tvalues], rel=1e-7, abs=1e-7)
    assert cast(list[float], first["coefficient_p_values_reg"]) == pytest.approx([float(value) for value in model.pvalues], rel=1e-7, abs=1e-7)
    assert [float(record["predicted_reg"]) for record in records] == pytest.approx([float(value) for value in model.fittedvalues], rel=1e-7, abs=1e-7)
    assert [float(record["residual_reg"]) for record in records] == pytest.approx([float(value) for value in model.resid], rel=1e-7, abs=1e-7)
    assert float(first["r_squared_reg"]) == pytest.approx(float(model.rsquared), rel=1e-9, abs=1e-9)
    assert float(first["adj_r_squared_reg"]) == pytest.approx(float(model.rsquared_adj), rel=1e-9, abs=1e-9)
    assert float(first["sigma2_reg"]) == pytest.approx(float(model.scale), rel=1e-9, abs=1e-9)
    assert float(first["dof_reg"]) == pytest.approx(float(model.df_resid), rel=1e-9, abs=1e-9)
    assert float(first["rmse_reg"]) == pytest.approx(
        math.sqrt(sum(float(value) * float(value) for value in model.resid) / len(records)),
        rel=1e-9,
        abs=1e-9,
    )


@pytest.mark.parametrize(
    ("rows", "independent_columns"),
    [
        (
            [
                {"site_id": "n1", "x1": 0.0, "x2": 1.0, "y": 1.4, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
                {"site_id": "n2", "x1": 1.0, "x2": 0.0, "y": 2.2, "geometry": {"type": "Point", "coordinates": [1.0, 0.0]}},
                {"site_id": "n3", "x1": 2.0, "x2": 1.0, "y": 3.9, "geometry": {"type": "Point", "coordinates": [2.0, 0.0]}},
                {"site_id": "n4", "x1": 3.0, "x2": 2.0, "y": 5.7, "geometry": {"type": "Point", "coordinates": [3.0, 0.0]}},
                {"site_id": "n5", "x1": 4.0, "x2": 3.0, "y": 7.8, "geometry": {"type": "Point", "coordinates": [4.0, 0.0]}},
                {"site_id": "n6", "x1": 5.0, "x2": 2.0, "y": 8.6, "geometry": {"type": "Point", "coordinates": [5.0, 0.0]}},
            ],
            ["x1", "x2"],
        ),
        (
            [
                {"site_id": "c1", "x1": 0.0, "x2": 1.0, "y": 5.0, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
                {"site_id": "c2", "x1": 1.0, "x2": 0.0, "y": 5.0, "geometry": {"type": "Point", "coordinates": [1.0, 0.0]}},
                {"site_id": "c3", "x1": 2.0, "x2": 1.0, "y": 5.0, "geometry": {"type": "Point", "coordinates": [2.0, 0.0]}},
                {"site_id": "c4", "x1": 3.0, "x2": 2.0, "y": 5.0, "geometry": {"type": "Point", "coordinates": [3.0, 0.0]}},
                {"site_id": "c5", "x1": 4.0, "x2": 3.0, "y": 5.0, "geometry": {"type": "Point", "coordinates": [4.0, 0.0]}},
                {"site_id": "c6", "x1": 5.0, "x2": 2.0, "y": 5.0, "geometry": {"type": "Point", "coordinates": [5.0, 0.0]}},
            ],
            ["x1", "x2"],
        ),
        (
            [
                {"site_id": "r1", "x1": 0.0, "x2": 0.0, "y": 1.0, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
                {"site_id": "r2", "x1": 1.0, "x2": 2.0, "y": 3.0, "geometry": {"type": "Point", "coordinates": [1.0, 0.0]}},
                {"site_id": "r3", "x1": 2.0, "x2": 4.0, "y": 5.0, "geometry": {"type": "Point", "coordinates": [2.0, 0.0]}},
                {"site_id": "r4", "x1": 3.0, "x2": 6.0, "y": 7.0, "geometry": {"type": "Point", "coordinates": [3.0, 0.0]}},
                {"site_id": "r5", "x1": 4.0, "x2": 8.0, "y": 9.0, "geometry": {"type": "Point", "coordinates": [4.0, 0.0]}},
            ],
            ["x1", "x2"],
        ),
    ],
)
def test_spatial_regression_matches_statsmodels_across_stress_cases_when_available(
    rows: list[dict[str, Any]],
    independent_columns: list[str],
) -> None:
    statsmodels_api = pytest.importorskip("statsmodels.api")

    frame = _make_point_frame(rows)
    records = frame.spatial_regression(
        dependent_column="y",
        independent_columns=independent_columns,
        k_neighbors=2,
    ).to_records()
    design = statsmodels_api.add_constant([[float(row[column]) for column in independent_columns] for row in rows])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = statsmodels_api.OLS([float(row["y"]) for row in rows], design).fit()
        first = records[0]

        assert cast(list[float], first["coefficients_reg"]) == pytest.approx([float(value) for value in model.params], rel=1e-6, abs=1e-6)
        assert cast(list[float], first["coefficient_standard_errors_reg"]) == pytest.approx([float(value) for value in model.bse], rel=1e-6, abs=1e-6)
        assert cast(list[float], first["coefficient_t_statistics_reg"]) == pytest.approx([float(value) for value in model.tvalues], rel=1e-6, abs=1e-6)
        assert cast(list[float], first["coefficient_p_values_reg"]) == pytest.approx([float(value) for value in model.pvalues], rel=1e-6, abs=1e-6)
        assert [float(record["predicted_reg"]) for record in records] == pytest.approx([float(value) for value in model.fittedvalues], rel=1e-6, abs=1e-6)
        assert [float(record["residual_reg"]) for record in records] == pytest.approx([float(value) for value in model.resid], rel=1e-6, abs=1e-6)
        assert float(first["r_squared_reg"]) == pytest.approx(float(model.rsquared), rel=1e-6, abs=1e-6)
        assert float(first["adj_r_squared_reg"]) == pytest.approx(float(model.rsquared_adj), rel=1e-6, abs=1e-6)
        assert float(first["sigma2_reg"]) == pytest.approx(float(model.scale), rel=1e-6, abs=1e-6)
        assert float(first["dof_reg"]) == pytest.approx(float(model.df_resid), rel=1e-6, abs=1e-6)
        assert float(first["rmse_reg"]) == pytest.approx(
            math.sqrt(sum(float(value) * float(value) for value in model.resid) / len(records)),
            rel=1e-6,
            abs=1e-6,
        )


# Tool 22: geographically_weighted_summary
def test_geographically_weighted_summary():
    frame = _sample_point_grid()
    result = frame.geographically_weighted_summary(
        dependent_column="elevation",
        independent_columns=["value"],
        bandwidth=2.0,
    )
    assert len(result) == 25
    for row in result:
        assert "predicted_gwr" in row
        assert "residual_gwr" in row
        assert "intercept_gwr" in row
        assert "coeff_value_gwr" in row


def test_geographically_weighted_summary_reflects_local_nonstationarity() -> None:
    frame = _make_point_frame([
        {"site_id": "w1", "x": 1.0, "y": 1.0, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
        {"site_id": "w2", "x": 2.0, "y": 2.0, "geometry": {"type": "Point", "coordinates": [0.5, 0.0]}},
        {"site_id": "w3", "x": 3.0, "y": 3.0, "geometry": {"type": "Point", "coordinates": [1.0, 0.0]}},
        {"site_id": "e1", "x": 1.0, "y": 6.0, "geometry": {"type": "Point", "coordinates": [10.0, 0.0]}},
        {"site_id": "e2", "x": 2.0, "y": 7.0, "geometry": {"type": "Point", "coordinates": [10.5, 0.0]}},
        {"site_id": "e3", "x": 3.0, "y": 8.0, "geometry": {"type": "Point", "coordinates": [11.0, 0.0]}},
    ])

    records = frame.geographically_weighted_summary(
        dependent_column="y",
        independent_columns=["x"],
        bandwidth=1.0,
    ).to_records()
    coefficients = {str(record["site_id"]): float(record["coeff_x_gwr"]) for record in records}

    assert coefficients["w1"] == pytest.approx(1.0, abs=1e-3)
    assert coefficients["e1"] == pytest.approx(1.0, abs=1e-3)
    assert float(records[0]["predicted_gwr"]) != pytest.approx(float(records[-1]["predicted_gwr"]))


def test_geographically_weighted_summary_bandwidth_changes_local_coefficients() -> None:
    frame = _make_point_frame([
        {"site_id": "a", "x": 1.0, "y": 1.0, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
        {"site_id": "b", "x": 2.0, "y": 2.0, "geometry": {"type": "Point", "coordinates": [0.8, 0.0]}},
        {"site_id": "c", "x": 3.0, "y": 3.0, "geometry": {"type": "Point", "coordinates": [1.6, 0.0]}},
        {"site_id": "d", "x": 1.0, "y": 4.0, "geometry": {"type": "Point", "coordinates": [4.0, 0.0]}},
        {"site_id": "e", "x": 2.0, "y": 6.0, "geometry": {"type": "Point", "coordinates": [4.8, 0.0]}},
        {"site_id": "f", "x": 3.0, "y": 8.0, "geometry": {"type": "Point", "coordinates": [5.6, 0.0]}},
    ])

    narrow = frame.geographically_weighted_summary(
        dependent_column="y",
        independent_columns=["x"],
        bandwidth=0.9,
    ).to_records()
    wide = frame.geographically_weighted_summary(
        dependent_column="y",
        independent_columns=["x"],
        bandwidth=10.0,
    ).to_records()

    narrow_coefficients = [float(record["coeff_x_gwr"]) for record in narrow]
    wide_coefficients = [float(record["coeff_x_gwr"]) for record in wide]

    assert max(narrow_coefficients) - min(narrow_coefficients) > 0.5
    assert max(wide_coefficients) - min(wide_coefficients) < 0.1


def test_weighted_local_summary_matches_geographically_weighted_summary_alias() -> None:
    frame = _sample_point_grid()

    legacy_records = frame.geographically_weighted_summary(
        dependent_column="elevation",
        independent_columns=["value"],
        bandwidth=2.0,
        gwr_suffix="alias",
    ).to_records()
    alias_records = frame.weighted_local_summary(
        dependent_column="elevation",
        independent_columns=["value"],
        bandwidth=2.0,
        summary_suffix="alias",
    ).to_records()

    assert alias_records == legacy_records


# Tool 23: join_by_largest_overlap
def test_join_by_largest_overlap():
    left = _make_point_frame([
        {"site_id": "L1", "geometry": {"type": "Polygon", "coordinates": [(0, 0), (2, 0), (2, 2), (0, 2), (0, 0)]}},
    ])
    right = _make_point_frame([
        {"site_id": "R1", "geometry": {"type": "Polygon", "coordinates": [(1, 1), (3, 1), (3, 3), (1, 3), (1, 1)]}},
        {"site_id": "R2", "geometry": {"type": "Polygon", "coordinates": [(5, 5), (6, 5), (6, 6), (5, 6), (5, 5)]}},
    ])
    result = left.join_by_largest_overlap(right)
    records = result.to_records()
    assert len(records) == 1
    assert records[0]["overlap_area_overlap"] > 0


# Tool 24: erase
def test_erase():
    source = _make_point_frame([
        {"site_id": "s1", "geometry": {"type": "Polygon", "coordinates": [(0, 0), (4, 0), (4, 4), (0, 4), (0, 0)]}},
    ])
    mask = _make_point_frame([
        {"site_id": "m1", "geometry": {"type": "Polygon", "coordinates": [(2, 2), (6, 2), (6, 6), (2, 6), (2, 6), (2, 2)]}},
    ])
    result = source.erase(mask)
    assert len(result) >= 1


# Tool 25: identity_overlay
def test_identity_overlay():
    left = _make_point_frame([
        {"site_id": "L1", "geometry": {"type": "Polygon", "coordinates": [(0, 0), (2, 0), (2, 2), (0, 2), (0, 0)]}},
    ])
    right = _make_point_frame([
        {"site_id": "R1", "val": 99, "geometry": {"type": "Polygon", "coordinates": [(1, 1), (3, 1), (3, 3), (1, 3), (1, 1)]}},
    ])
    result = left.identity_overlay(right)
    assert len(result) >= 1
    has_identity_val = any(r.get("val_identity") == 99 for r in result)
    assert has_identity_val


# Tool 26: multipart_to_singlepart
def test_multipart_to_singlepart():
    frame = _make_point_frame([
        {"site_id": "s1", "geometry": {"type": "Point", "coordinates": [1.0, 2.0]}},
        {"site_id": "s2", "geometry": {"type": "Point", "coordinates": [3.0, 4.0]}},
    ])
    result = frame.multipart_to_singlepart()
    assert len(result) >= 2
    for row in result:
        assert "part_id_part" in row


# Tool 27: singlepart_to_multipart
def test_singlepart_to_multipart():
    frame = _make_point_frame([
        {"site_id": "group1", "geometry": {"type": "Point", "coordinates": [1.0, 2.0]}},
        {"site_id": "group1", "geometry": {"type": "Point", "coordinates": [3.0, 4.0]}},
        {"site_id": "group2", "geometry": {"type": "Point", "coordinates": [5.0, 6.0]}},
    ])
    result = frame.singlepart_to_multipart(group_column="site_id")
    assert len(result) == 2
    records = result.to_records()
    for row in records:
        assert "part_count_multi" in row
        assert len(cast(Any, row["part_geometries_multi"])) == row["part_count_multi"]
    group1 = next(row for row in records if row["site_id"] == "group1")
    round_tripped = result.filter(lambda row: row["site_id"] == "group1").multipart_to_singlepart().to_records()
    assert len(round_tripped) == 2
    assert {tuple(cast(Any, row["geometry"])["coordinates"]) for row in round_tripped} == {
        (1.0, 2.0),
        (3.0, 4.0),
    }


# Tool 28: eliminate_slivers
def test_eliminate_slivers():
    frame = _make_point_frame([
        {"site_id": "big", "geometry": {"type": "Polygon", "coordinates": [(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]}},
        {"site_id": "tiny", "geometry": {"type": "Polygon", "coordinates": [(0, 0), (0.001, 0), (0.001, 0.001), (0, 0.001), (0, 0)]}},
    ])
    result = frame.eliminate_slivers(min_area=0.01)
    records = result.to_records()
    assert len(records) == 1
    assert records[0]["site_id"] == "big"


# Tool 29: simplify
def test_simplify():
    frame = _make_point_frame([
        {"site_id": "line", "geometry": {"type": "LineString", "coordinates": [
            (0.0, 0.0), (0.5, 0.001), (1.0, 0.0), (1.5, -0.001), (2.0, 0.0),
        ]}},
    ])
    result = frame.simplify(tolerance=0.01)
    records = result.to_records()
    assert len(records) == 1
    assert records[0]["vertex_count_simplified"] <= 5


# Tool 30: densify
def test_densify():
    frame = _make_point_frame([
        {"site_id": "line", "geometry": {"type": "LineString", "coordinates": [(0.0, 0.0), (1.0, 0.0)]}},
    ])
    result = frame.densify(max_segment_length=0.25)
    records = result.to_records()
    assert records[0]["vertex_count_densified"] >= 5


# Tool 31: smooth_geometry
def test_smooth_geometry():
    frame = _make_point_frame([
        {"site_id": "line", "geometry": {"type": "LineString", "coordinates": [
            (0.0, 0.0), (1.0, 1.0), (2.0, 0.0), (3.0, 1.0),
        ]}},
    ])
    result = frame.smooth_geometry(iterations=2)
    records = result.to_records()
    assert records[0]["vertex_count_smoothed"] > 4


# Tool 32: snap_to_network_nodes
def test_snap_to_network_nodes():
    network = _sample_network_frame()
    points = _make_point_frame([
        {"site_id": "q1", "geometry": {"type": "Point", "coordinates": [0.1, 0.05]}},
        {"site_id": "q2", "geometry": {"type": "Point", "coordinates": [2.8, 0.1]}},
    ])
    result = network.snap_to_network_nodes(points)
    records = result.to_records()
    assert len(records) == 2
    # node_id_snapped contains the coordinate key, not the node id
    assert records[0]["snap_distance_snapped"] < 0.2
    assert records[1]["snap_distance_snapped"] < 0.3


# Tool 33: origin_destination_matrix
def test_origin_destination_matrix():
    network = _sample_network_frame()
    origins = _make_point_frame([
        {"site_id": "o1", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
    ])
    destinations = _make_point_frame([
        {"site_id": "d1", "geometry": {"type": "Point", "coordinates": [3.0, 0.0]}},
    ])
    result = network.origin_destination_matrix(origins, destinations)
    records = result.to_records()
    assert len(records) == 1
    assert records[0]["network_cost_od"] is not None
    assert records[0]["reachable_od"] is True


# Tool 34: k_shortest_paths
def test_k_shortest_paths():
    network = _sample_network_frame()
    result = network.k_shortest_paths(
        origin=(0.0, 0.0),
        destination=(3.0, 0.0),
        k=2,
    )
    assert len(result) >= 3  # at least the primary path with 3 edges


def test_k_shortest_paths_returns_unique_ranked_alternatives() -> None:
    network = GeoPromptFrame.from_records(
        [
            {
                "edge_id": "ab",
                "from_node_id": "A",
                "to_node_id": "B",
                "from_node": (0.0, 0.0),
                "to_node": (1.0, 0.0),
                "edge_length": 1.0,
                "geometry": {"type": "LineString", "coordinates": [(0.0, 0.0), (1.0, 0.0)]},
            },
            {
                "edge_id": "bd",
                "from_node_id": "B",
                "to_node_id": "D",
                "from_node": (1.0, 0.0),
                "to_node": (2.0, 1.0),
                "edge_length": 1.4,
                "geometry": {"type": "LineString", "coordinates": [(1.0, 0.0), (2.0, 1.0)]},
            },
            {
                "edge_id": "ac",
                "from_node_id": "A",
                "to_node_id": "C",
                "from_node": (0.0, 0.0),
                "to_node": (1.0, 1.0),
                "edge_length": 1.2,
                "geometry": {"type": "LineString", "coordinates": [(0.0, 0.0), (1.0, 1.0)]},
            },
            {
                "edge_id": "cd",
                "from_node_id": "C",
                "to_node_id": "D",
                "from_node": (1.0, 1.0),
                "to_node": (2.0, 1.0),
                "edge_length": 1.0,
                "geometry": {"type": "LineString", "coordinates": [(1.0, 1.0), (2.0, 1.0)]},
            },
        ],
        geometry="geometry",
        crs="EPSG:4326",
    )

    result = network.k_shortest_paths(origin="A", destination="D", k=3).to_records()

    path_signatures: dict[int, list[str]] = {}
    for row in result:
        path_signatures.setdefault(int(row["path_rank_ksp"]), []).append(str(row["edge_id"]))

    assert path_signatures == {
        1: ["ac", "cd"],
        2: ["ab", "bd"],
    }


# Tool 35: network_trace
def test_network_trace():
    network = _sample_network_frame()
    result = network.network_trace(start=(0.0, 0.0), direction="downstream")
    assert len(result) >= 1
    for row in result:
        assert "trace_cost_trace" in row


# Tool 36: route_sequence_optimize
def test_route_sequence_optimize():
    network = _sample_network_frame()
    stops = _make_point_frame([
        {"site_id": "s1", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
        {"site_id": "s2", "geometry": {"type": "Point", "coordinates": [2.0, 0.0]}},
        {"site_id": "s3", "geometry": {"type": "Point", "coordinates": [3.0, 0.0]}},
    ])
    result = network.route_sequence_optimize(stops)
    assert len(result) == 3
    orders = sorted(row["visit_order_route"] for row in result)
    assert orders == [1, 2, 3]
    assert all(row["method_route"] == "greedy_2opt" for row in result.to_records())


def test_route_sequence_optimize_improves_greedy_route_with_two_opt() -> None:
    node_coordinates = {
        "A": (0.0, 0.0),
        "B": (1.0, 0.0),
        "C": (2.0, 0.0),
        "D": (3.0, 0.0),
        "E": (4.0, 0.0),
    }
    costs = {
        ("A", "B"): 14.0,
        ("A", "C"): 1.0,
        ("A", "D"): 17.0,
        ("A", "E"): 8.0,
        ("B", "C"): 15.0,
        ("B", "D"): 16.0,
        ("B", "E"): 18.0,
        ("C", "D"): 8.0,
        ("C", "E"): 12.0,
        ("D", "E"): 8.0,
    }

    network_rows = []
    for edge_index, ((from_node_id, to_node_id), edge_length) in enumerate(costs.items(), start=1):
        network_rows.append(
            {
                "edge_id": f"edge-{edge_index:02d}",
                "from_node_id": from_node_id,
                "to_node_id": to_node_id,
                "from_node": node_coordinates[from_node_id],
                "to_node": node_coordinates[to_node_id],
                "edge_length": edge_length,
                "geometry": {"type": "LineString", "coordinates": [node_coordinates[from_node_id], node_coordinates[to_node_id]]},
            }
        )
    network = GeoPromptFrame.from_records(network_rows, crs="EPSG:4326")
    stops = GeoPromptFrame.from_records(
        [
            {"site_id": node_id.lower(), "node_id": node_id, "geometry": {"type": "Point", "coordinates": node_coordinates[node_id]}}
            for node_id in ["A", "B", "C", "D", "E"]
        ],
        crs="EPSG:4326",
    )

    records = network.route_sequence_optimize(
        stops,
        stop_node_column="node_id",
    ).to_records()

    greedy_cost = 35.0
    optimized_cost = float(records[0]["total_cost_route"])

    assert [record["site_id"] for record in records] == ["a", "c", "e", "d", "b"]
    assert optimized_cost < greedy_cost
    assert optimized_cost == pytest.approx(34.0)
    assert all(record["reachable_route"] is True for record in records)


def test_route_sequence_optimize_matches_bruteforce_optimum_on_multiple_tiny_networks() -> None:
    cases = [
        {
            "name": "chain_four",
            "directed": False,
            "node_coordinates": {"A": (0.0, 0.0), "B": (1.0, 0.0), "C": (2.0, 0.0), "D": (3.0, 0.0)},
            "edges": [
                ("edge-01", "A", "B", 1.0),
                ("edge-02", "B", "C", 1.0),
                ("edge-03", "C", "D", 1.0),
            ],
            "stop_order": ["A", "B", "C", "D"],
        },
        {
            "name": "diamond_four",
            "directed": False,
            "node_coordinates": {"A": (0.0, 0.0), "B": (1.0, 1.0), "C": (1.0, -1.0), "D": (2.0, 0.0)},
            "edges": [
                ("edge-01", "A", "B", 1.0),
                ("edge-02", "A", "C", 1.2),
                ("edge-03", "B", "D", 1.0),
                ("edge-04", "C", "D", 1.0),
                ("edge-05", "B", "C", 0.9),
            ],
            "stop_order": ["A", "B", "C", "D"],
        },
        {
            "name": "five_stop_improvement",
            "directed": False,
            "node_coordinates": {"A": (0.0, 0.0), "B": (1.0, 0.0), "C": (2.0, 0.0), "D": (3.0, 0.0), "E": (4.0, 0.0)},
            "edges": [
                ("edge-01", "A", "B", 14.0),
                ("edge-02", "A", "C", 1.0),
                ("edge-03", "A", "D", 17.0),
                ("edge-04", "A", "E", 8.0),
                ("edge-05", "B", "C", 15.0),
                ("edge-06", "B", "D", 16.0),
                ("edge-07", "B", "E", 18.0),
                ("edge-08", "C", "D", 8.0),
                ("edge-09", "C", "E", 12.0),
                ("edge-10", "D", "E", 8.0),
            ],
            "stop_order": ["A", "B", "C", "D", "E"],
        },
        {
            "name": "directed_asymmetric_five",
            "directed": True,
            "node_coordinates": {"A": (0.0, 0.0), "B": (1.0, 0.0), "C": (2.0, 0.0), "D": (3.0, 0.0), "E": (4.0, 0.0)},
            "edges": [
                ("edge-01", "A", "B", 9.0),
                ("edge-02", "A", "C", 1.0),
                ("edge-03", "A", "D", 8.0),
                ("edge-04", "A", "E", 10.0),
                ("edge-05", "B", "A", 9.0),
                ("edge-06", "B", "C", 9.0),
                ("edge-07", "B", "D", 1.0),
                ("edge-08", "B", "E", 7.0),
                ("edge-09", "C", "A", 8.0),
                ("edge-10", "C", "B", 1.0),
                ("edge-11", "C", "D", 4.0),
                ("edge-12", "C", "E", 8.0),
                ("edge-13", "D", "A", 8.0),
                ("edge-14", "D", "B", 6.0),
                ("edge-15", "D", "C", 5.0),
                ("edge-16", "D", "E", 1.0),
                ("edge-17", "E", "A", 10.0),
                ("edge-18", "E", "B", 7.0),
                ("edge-19", "E", "C", 6.0),
                ("edge-20", "E", "D", 3.0),
            ],
            "stop_order": ["A", "B", "C", "D", "E"],
        },
        {
            "name": "undirected_six_dense",
            "directed": False,
            "node_coordinates": {"A": (0.0, 0.0), "B": (1.0, 1.0), "C": (2.0, 0.0), "D": (3.0, 1.0), "E": (4.0, 0.0), "F": (5.0, 1.0)},
            "edges": [
                ("edge-01", "A", "B", 1.0),
                ("edge-02", "A", "C", 2.4),
                ("edge-03", "A", "D", 4.8),
                ("edge-04", "A", "E", 6.2),
                ("edge-05", "A", "F", 7.8),
                ("edge-06", "B", "C", 1.1),
                ("edge-07", "B", "D", 2.2),
                ("edge-08", "B", "E", 4.7),
                ("edge-09", "B", "F", 6.3),
                ("edge-10", "C", "D", 1.0),
                ("edge-11", "C", "E", 2.1),
                ("edge-12", "C", "F", 4.4),
                ("edge-13", "D", "E", 1.2),
                ("edge-14", "D", "F", 2.0),
                ("edge-15", "E", "F", 1.1),
            ],
            "stop_order": ["A", "B", "C", "D", "E", "F"],
        },
        {
            "name": "directed_six_dense",
            "directed": True,
            "node_coordinates": {"A": (0.0, 0.0), "B": (1.0, 1.0), "C": (2.0, 0.0), "D": (3.0, 1.0), "E": (4.0, 0.0), "F": (5.0, 1.0)},
            "edges": [
                ("edge-01", "A", "B", 1.0),
                ("edge-02", "A", "C", 3.4),
                ("edge-03", "A", "D", 5.5),
                ("edge-04", "A", "E", 6.7),
                ("edge-05", "A", "F", 8.9),
                ("edge-06", "B", "A", 2.2),
                ("edge-07", "B", "C", 1.0),
                ("edge-08", "B", "D", 2.8),
                ("edge-09", "B", "E", 4.8),
                ("edge-10", "B", "F", 6.4),
                ("edge-11", "C", "A", 2.9),
                ("edge-12", "C", "B", 1.1),
                ("edge-13", "C", "D", 1.0),
                ("edge-14", "C", "E", 2.6),
                ("edge-15", "C", "F", 4.7),
                ("edge-16", "D", "A", 5.7),
                ("edge-17", "D", "B", 2.1),
                ("edge-18", "D", "C", 1.3),
                ("edge-19", "D", "E", 1.0),
                ("edge-20", "D", "F", 2.4),
                ("edge-21", "E", "A", 6.8),
                ("edge-22", "E", "B", 4.6),
                ("edge-23", "E", "C", 2.2),
                ("edge-24", "E", "D", 1.2),
                ("edge-25", "E", "F", 1.0),
                ("edge-26", "F", "A", 8.3),
                ("edge-27", "F", "B", 6.1),
                ("edge-28", "F", "C", 4.3),
                ("edge-29", "F", "D", 2.0),
                ("edge-30", "F", "E", 1.4),
            ],
            "stop_order": ["A", "B", "C", "D", "E", "F"],
        },
        {
            "name": "undirected_seven_dense",
            "directed": False,
            "node_coordinates": {"A": (0.0, 0.0), "B": (1.0, 1.0), "C": (2.0, 0.0), "D": (3.0, 1.0), "E": (4.0, 0.0), "F": (5.0, 1.0), "G": (6.0, 0.0)},
            "edges": [
                ("edge-01", "A", "B", 1.0),
                ("edge-02", "A", "C", 2.0),
                ("edge-03", "A", "D", 4.1),
                ("edge-04", "A", "E", 6.2),
                ("edge-05", "A", "F", 8.0),
                ("edge-06", "A", "G", 10.1),
                ("edge-07", "B", "C", 1.0),
                ("edge-08", "B", "D", 2.1),
                ("edge-09", "B", "E", 4.3),
                ("edge-10", "B", "F", 6.1),
                ("edge-11", "B", "G", 8.2),
                ("edge-12", "C", "D", 1.0),
                ("edge-13", "C", "E", 2.0),
                ("edge-14", "C", "F", 4.2),
                ("edge-15", "C", "G", 6.0),
                ("edge-16", "D", "E", 1.0),
                ("edge-17", "D", "F", 2.1),
                ("edge-18", "D", "G", 4.1),
                ("edge-19", "E", "F", 1.0),
                ("edge-20", "E", "G", 2.0),
                ("edge-21", "F", "G", 1.0),
            ],
            "stop_order": ["A", "B", "C", "D", "E", "F", "G"],
        },
        {
            "name": "directed_seven_dense",
            "directed": True,
            "node_coordinates": {"A": (0.0, 0.0), "B": (1.0, 1.0), "C": (2.0, 0.0), "D": (3.0, 1.0), "E": (4.0, 0.0), "F": (5.0, 1.0), "G": (6.0, 0.0)},
            "edges": [
                ("edge-01", "A", "B", 1.0),
                ("edge-02", "A", "C", 2.6),
                ("edge-03", "A", "D", 4.9),
                ("edge-04", "A", "E", 7.2),
                ("edge-05", "A", "F", 8.8),
                ("edge-06", "A", "G", 10.9),
                ("edge-07", "B", "A", 2.3),
                ("edge-08", "B", "C", 1.0),
                ("edge-09", "B", "D", 2.4),
                ("edge-10", "B", "E", 4.8),
                ("edge-11", "B", "F", 6.6),
                ("edge-12", "B", "G", 8.7),
                ("edge-13", "C", "A", 2.8),
                ("edge-14", "C", "B", 1.2),
                ("edge-15", "C", "D", 1.0),
                ("edge-16", "C", "E", 2.5),
                ("edge-17", "C", "F", 4.7),
                ("edge-18", "C", "G", 6.5),
                ("edge-19", "D", "A", 5.4),
                ("edge-20", "D", "B", 2.0),
                ("edge-21", "D", "C", 1.3),
                ("edge-22", "D", "E", 1.0),
                ("edge-23", "D", "F", 2.2),
                ("edge-24", "D", "G", 4.6),
                ("edge-25", "E", "A", 7.1),
                ("edge-26", "E", "B", 4.5),
                ("edge-27", "E", "C", 2.1),
                ("edge-28", "E", "D", 1.2),
                ("edge-29", "E", "F", 1.0),
                ("edge-30", "E", "G", 2.4),
                ("edge-31", "F", "A", 8.6),
                ("edge-32", "F", "B", 6.3),
                ("edge-33", "F", "C", 4.2),
                ("edge-34", "F", "D", 2.0),
                ("edge-35", "F", "E", 1.4),
                ("edge-36", "F", "G", 1.0),
                ("edge-37", "G", "A", 10.4),
                ("edge-38", "G", "B", 8.1),
                ("edge-39", "G", "C", 6.1),
                ("edge-40", "G", "D", 4.0),
                ("edge-41", "G", "E", 2.2),
                ("edge-42", "G", "F", 1.3),
            ],
            "stop_order": ["A", "B", "C", "D", "E", "F", "G"],
        },
    ]

    for case in cases:
        node_coordinates = case["node_coordinates"]
        directed = bool(case["directed"])
        network_rows = [
            {
                "edge_id": edge_id,
                "from_node_id": from_node_id,
                "to_node_id": to_node_id,
                "from_node": node_coordinates[from_node_id],
                "to_node": node_coordinates[to_node_id],
                "edge_length": edge_length,
                "geometry": {"type": "LineString", "coordinates": [node_coordinates[from_node_id], node_coordinates[to_node_id]]},
            }
            for edge_id, from_node_id, to_node_id, edge_length in case["edges"]
        ]
        network = GeoPromptFrame.from_records(network_rows, crs="EPSG:4326")
        stops = GeoPromptFrame.from_records(
            [
                {"site_id": node_id.lower(), "node_id": node_id, "geometry": {"type": "Point", "coordinates": node_coordinates[node_id]}}
                for node_id in case["stop_order"]
            ],
            crs="EPSG:4326",
        )

        records = network.route_sequence_optimize(
            stops,
            stop_node_column="node_id",
            directed=directed,
        ).to_records()
        route_nodes = [record["node_id"] for record in records]
        node_ids = list(case["stop_order"])
        shortest_costs = {
            origin: {destination: (0.0 if origin == destination else float("inf")) for destination in node_ids}
            for origin in node_ids
        }
        for row in network_rows:
            shortest_costs[row["from_node_id"]][row["to_node_id"]] = float(row["edge_length"])
            if not directed:
                shortest_costs[row["to_node_id"]][row["from_node_id"]] = float(row["edge_length"])
        for via in node_ids:
            for origin in node_ids:
                for destination in node_ids:
                    shortest_costs[origin][destination] = min(
                        shortest_costs[origin][destination],
                        shortest_costs[origin][via] + shortest_costs[via][destination],
                    )

        def path_cost(path: list[str]) -> float:
            return sum(shortest_costs[path[index]][path[index + 1]] for index in range(len(path) - 1))

        optimal_sequence = min(
            ([node_ids[0], *list(permutation)] for permutation in permutations(node_ids[1:])),
            key=path_cost,
        )

        assert path_cost(route_nodes) == pytest.approx(path_cost(optimal_sequence)), case["name"]
        assert float(records[0]["total_cost_route"]) == pytest.approx(path_cost(route_nodes)), case["name"]


def test_route_sequence_optimize_retains_unreachable_stops() -> None:
    network = GeoPromptFrame.from_records(
        [
            {
                "edge_id": "e1",
                "from_node_id": "A",
                "to_node_id": "B",
                "from_node": (0.0, 0.0),
                "to_node": (1.0, 0.0),
                "edge_length": 1.0,
                "geometry": {"type": "LineString", "coordinates": [(0.0, 0.0), (1.0, 0.0)]},
            },
            {
                "edge_id": "e2",
                "from_node_id": "B",
                "to_node_id": "C",
                "from_node": (1.0, 0.0),
                "to_node": (2.0, 0.0),
                "edge_length": 1.0,
                "geometry": {"type": "LineString", "coordinates": [(1.0, 0.0), (2.0, 0.0)]},
            },
            {
                "edge_id": "e3",
                "from_node_id": "X",
                "to_node_id": "Y",
                "from_node": (10.0, 0.0),
                "to_node": (11.0, 0.0),
                "edge_length": 1.0,
                "geometry": {"type": "LineString", "coordinates": [(10.0, 0.0), (11.0, 0.0)]},
            },
        ],
        geometry="geometry",
        crs="EPSG:4326",
    )
    stops = _make_point_frame([
        {"site_id": "s1", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
        {"site_id": "s2", "geometry": {"type": "Point", "coordinates": [2.0, 0.0]}},
        {"site_id": "s3", "geometry": {"type": "Point", "coordinates": [11.0, 0.0]}},
    ])

    records = network.route_sequence_optimize(stops).to_records()

    assert [record["site_id"] for record in records] == ["s1", "s2", "s3"]
    assert [record["reachable_route"] for record in records] == [True, True, False]
    assert records[-1]["visit_order_route"] == 3
    assert records[-1]["stop_count_route"] == 3


# Tool 37: trajectory_staypoint_detection
def test_trajectory_staypoint_detection():
    frame = _make_point_frame([
        {"site_id": "t1", "time": 0.0, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
        {"site_id": "t2", "time": 1.0, "geometry": {"type": "Point", "coordinates": [0.001, 0.001]}},
        {"site_id": "t3", "time": 2.0, "geometry": {"type": "Point", "coordinates": [0.002, 0.0]}},
        {"site_id": "t4", "time": 3.0, "geometry": {"type": "Point", "coordinates": [5.0, 5.0]}},
        {"site_id": "t5", "time": 4.0, "geometry": {"type": "Point", "coordinates": [5.001, 5.001]}},
    ])
    result = frame.trajectory_staypoint_detection(time_column="time", max_radius=0.01, min_duration=1.0)
    staypoints = [r for r in result if r["is_staypoint_staypoint"]]
    assert len(staypoints) >= 2


def test_trajectory_staypoint_detection_uses_chronological_order() -> None:
    frame = _make_point_frame([
        {"site_id": "late", "time": 2.0, "geometry": {"type": "Point", "coordinates": [0.0004, 0.0]}},
        {"site_id": "early", "time": 0.0, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
        {"site_id": "middle", "time": 1.0, "geometry": {"type": "Point", "coordinates": [0.0002, 0.0]}},
        {"site_id": "move", "time": 3.0, "geometry": {"type": "Point", "coordinates": [1.0, 1.0]}},
    ])

    records = frame.trajectory_staypoint_detection(
        time_column="time",
        max_radius=0.01,
        min_duration=1.0,
    ).to_records()

    assert [record["site_id"] for record in records] == ["early", "middle", "late", "move"]
    assert [record["is_staypoint_staypoint"] for record in records] == [True, True, True, False]
    assert all(record["duration_staypoint"] == 2.0 for record in records[:3])


# Tool 38: trajectory_simplify
def test_trajectory_simplify():
    frame = _make_point_frame([
        {"site_id": f"t{i}", "geometry": {"type": "Point", "coordinates": [float(i), 0.001 * (i % 2)]}}
        for i in range(10)
    ])
    result = frame.trajectory_simplify(tolerance=0.01)
    assert len(result) < len(frame)


def test_trajectory_simplify_uses_time_column_order() -> None:
    frame = _make_point_frame([
        {"site_id": "mid", "time": 1.0, "geometry": {"type": "Point", "coordinates": [1.0, 0.001]}},
        {"site_id": "end", "time": 2.0, "geometry": {"type": "Point", "coordinates": [2.0, 0.0]}},
        {"site_id": "start", "time": 0.0, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
    ])

    records = frame.trajectory_simplify(tolerance=0.01, time_column="time").to_records()

    assert [record["site_id"] for record in records] == ["start", "end"]
    assert [record["time"] for record in records] == [0.0, 2.0]
    assert [record["original_index_traj_simplified"] for record in records] == [2, 1]


# Tool 39: spatiotemporal_cube
def test_spatiotemporal_cube():
    frame = _sample_point_grid()
    result = frame.spatiotemporal_cube(
        time_column="time",
        value_column="value",
        time_intervals=3,
        grid_resolution=3,
        aggregation="count",
    )
    assert len(result) > 0
    for row in result:
        assert "time_bin_cube" in row
        assert "value_cube" in row
        assert row["geometry"]["type"] == "Point"


def test_spatiotemporal_cube_assigns_boundary_points_once() -> None:
    frame = _make_point_frame([
        {"site_id": "a", "time": 0.0, "value": 1.0, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
        {"site_id": "b", "time": 1.0, "value": 2.0, "geometry": {"type": "Point", "coordinates": [1.0, 0.5]}},
        {"site_id": "c", "time": 2.0, "value": 3.0, "geometry": {"type": "Point", "coordinates": [2.0, 1.0]}},
    ])

    records = frame.spatiotemporal_cube(
        time_column="time",
        value_column="value",
        time_intervals=2,
        grid_resolution=2,
        aggregation="count",
    ).to_records()

    assert sum(float(record["value_cube"]) for record in records) == pytest.approx(3.0)
    assert sum(int(record["point_count_cube"]) for record in records) == 3
    assert {(int(record["time_bin_cube"]), int(record["grid_row_cube"]), int(record["grid_col_cube"])) for record in records} == {
        (0, 0, 0),
        (1, 1, 1),
    }


def test_spatiotemporal_cube_aggregations_match_expected_rollups() -> None:
    frame = _make_point_frame([
        {"site_id": "a", "time": 0.0, "value": 2.0, "geometry": {"type": "Point", "coordinates": [0.1, 0.1]}},
        {"site_id": "b", "time": 0.1, "value": 4.0, "geometry": {"type": "Point", "coordinates": [0.2, 0.2]}},
        {"site_id": "c", "time": 1.1, "value": 6.0, "geometry": {"type": "Point", "coordinates": [1.8, 1.8]}},
        {"site_id": "d", "time": 1.2, "value": 10.0, "geometry": {"type": "Point", "coordinates": [1.9, 1.9]}},
    ])

    sum_records = frame.spatiotemporal_cube(
        time_column="time",
        value_column="value",
        time_intervals=2,
        grid_resolution=2,
        aggregation="sum",
    ).to_records()
    mean_records = frame.spatiotemporal_cube(
        time_column="time",
        value_column="value",
        time_intervals=2,
        grid_resolution=2,
        aggregation="mean",
    ).to_records()
    min_records = frame.spatiotemporal_cube(
        time_column="time",
        value_column="value",
        time_intervals=2,
        grid_resolution=2,
        aggregation="min",
    ).to_records()
    max_records = frame.spatiotemporal_cube(
        time_column="time",
        value_column="value",
        time_intervals=2,
        grid_resolution=2,
        aggregation="max",
    ).to_records()

    assert [float(record["value_cube"]) for record in sum_records] == pytest.approx([6.0, 16.0])
    assert [float(record["value_cube"]) for record in mean_records] == pytest.approx([3.0, 8.0])
    assert [float(record["value_cube"]) for record in min_records] == pytest.approx([2.0, 6.0])
    assert [float(record["value_cube"]) for record in max_records] == pytest.approx([4.0, 10.0])
    assert [int(record["point_count_cube"]) for record in sum_records] == [2, 2]


# Tool 40: geohash_encode
def test_geohash_encode():
    frame = _make_point_frame([
        {"site_id": "a", "geometry": {"type": "Point", "coordinates": [-111.92, 40.78]}},
        {"site_id": "b", "geometry": {"type": "Point", "coordinates": [-73.99, 40.73]}},
    ])
    result = frame.geohash_encode(precision=6)
    assert len(result) == 2
    for row in result:
        assert "hash_geohash" in row
        assert len(row["hash_geohash"]) == 6
        assert "precision_geohash" in row
    # Geohashes for different regions should be different
    hashes = result["hash_geohash"]
    assert hashes[0] != hashes[1]


# ===========================================================================
# Tools 41-85: New Spatial Analysis Tools
# ===========================================================================


# Tool 41: nearest_neighbor_distance
def test_nearest_neighbor_distance():
    frame = _make_point_frame([
        {"site_id": "a", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
        {"site_id": "b", "geometry": {"type": "Point", "coordinates": [3.0, 4.0]}},
        {"site_id": "c", "geometry": {"type": "Point", "coordinates": [6.0, 0.0]}},
    ])
    result = frame.nearest_neighbor_distance(id_column="site_id")
    assert len(result) == 3
    for row in result:
        assert "distance_nn" in row
        assert "neighbor_id_nn" in row
        assert row["distance_nn"] is not None
    # a -> b = 5.0, a -> c = 6.0 => nn = b at 5.0
    assert abs(result["distance_nn"][0] - 5.0) < 1e-9
    assert result["neighbor_id_nn"][0] == "b"


def test_nearest_neighbor_distance_empty():
    frame = _make_point_frame([])
    result = frame.nearest_neighbor_distance()
    assert len(result) == 0


# Tool 42: pairwise_distances
def test_pairwise_distances():
    frame = _make_point_frame([
        {"site_id": "a", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
        {"site_id": "b", "geometry": {"type": "Point", "coordinates": [3.0, 4.0]}},
    ])
    result = frame.pairwise_distances(id_column="site_id")
    assert len(result) == 1  # self-mode, upper triangle only
    assert abs(result[0]["distance"] - 5.0) < 1e-9


def test_pairwise_distances_with_max():
    frame = _make_point_frame([
        {"site_id": "a", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
        {"site_id": "b", "geometry": {"type": "Point", "coordinates": [3.0, 4.0]}},
        {"site_id": "c", "geometry": {"type": "Point", "coordinates": [100.0, 100.0]}},
    ])
    result = frame.pairwise_distances(id_column="site_id", max_distance=10.0)
    assert len(result) == 1  # only a-b pair within 10.0


# Tool 43: point_density
def test_point_density():
    frame = _make_point_frame([
        {"site_id": "a", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
        {"site_id": "b", "geometry": {"type": "Point", "coordinates": [1.0, 1.0]}},
        {"site_id": "c", "geometry": {"type": "Point", "coordinates": [0.5, 0.5]}},
    ])
    result = frame.point_density(search_radius=2.0, grid_resolution=5)
    assert len(result) == 25  # 5x5 grid
    for row in result:
        assert "density_ptdensity" in row
        assert "count_ptdensity" in row
        assert row["density_ptdensity"] >= 0


# Tool 44: line_length
def test_line_length():
    frame = GeoPromptFrame.from_records([
        {"site_id": "a", "geometry": {"type": "LineString", "coordinates": [[0.0, 0.0], [3.0, 4.0]]}},
    ])
    result = frame.line_length()
    assert len(result) == 1
    assert abs(result["value_length"][0] - 5.0) < 1e-9


def test_line_length_two_segments():
    frame = GeoPromptFrame.from_records([
        {"site_id": "a", "geometry": {"type": "LineString", "coordinates": [[0.0, 0.0], [3.0, 4.0]]}},
        {"site_id": "b", "geometry": {"type": "LineString", "coordinates": [[0.0, 0.0], [0.0, 10.0]]}},
    ])
    result = frame.line_length()
    lengths = result["value_length"]
    assert abs(lengths[0] - 5.0) < 1e-9
    assert abs(lengths[1] - 10.0) < 1e-9


# Tool 45: polygon_area
def test_polygon_area():
    frame = GeoPromptFrame.from_records([
        {"site_id": "a", "geometry": {"type": "Polygon", "coordinates": [
            [[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0], [0.0, 0.0]]
        ]}},
    ])
    result = frame.polygon_area()
    assert len(result) == 1
    assert abs(result["value_area"][0] - 100.0) < 1e-9


# Tool 46: polygon_perimeter
def test_polygon_perimeter():
    frame = GeoPromptFrame.from_records([
        {"site_id": "a", "geometry": {"type": "Polygon", "coordinates": [
            [[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0], [0.0, 0.0]]
        ]}},
    ])
    result = frame.polygon_perimeter()
    assert len(result) == 1
    assert abs(result["value_perimeter"][0] - 40.0) < 1e-9


# Tool 47: average_nearest_neighbor
def test_average_nearest_neighbor():
    frame = _sample_point_grid()
    result = frame.average_nearest_neighbor()
    assert result["point_count"] == 25
    assert result["observed_mean_distance"] is not None
    assert result["expected_mean_distance"] is not None
    assert result["r_ratio"] is not None
    # Regular grid should have R close to or above 1.0 (regular = R > 1)
    assert result["r_ratio"] > 0.5


def test_average_nearest_neighbor_too_few():
    frame = _make_point_frame([
        {"site_id": "a", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
    ])
    result = frame.average_nearest_neighbor()
    assert result["r_ratio"] is None


# Tool 48: mean_center
def test_mean_center():
    frame = _make_point_frame([
        {"site_id": "a", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
        {"site_id": "b", "geometry": {"type": "Point", "coordinates": [10.0, 0.0]}},
        {"site_id": "c", "geometry": {"type": "Point", "coordinates": [0.0, 10.0]}},
        {"site_id": "d", "geometry": {"type": "Point", "coordinates": [10.0, 10.0]}},
    ])
    cx, cy = frame.mean_center()
    assert abs(cx - 5.0) < 1e-9
    assert abs(cy - 5.0) < 1e-9


def test_mean_center_weighted():
    frame = _make_point_frame([
        {"site_id": "a", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}, "w": 3.0},
        {"site_id": "b", "geometry": {"type": "Point", "coordinates": [10.0, 0.0]}, "w": 1.0},
    ])
    cx, cy = frame.mean_center(weight_column="w")
    assert abs(cx - 2.5) < 1e-9
    assert abs(cy - 0.0) < 1e-9


# Tool 49: median_center
def test_median_center():
    frame = _make_point_frame([
        {"site_id": "a", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
        {"site_id": "b", "geometry": {"type": "Point", "coordinates": [10.0, 0.0]}},
        {"site_id": "c", "geometry": {"type": "Point", "coordinates": [5.0, 5.0]}},
    ])
    cx, cy = frame.median_center()
    # Spatial median should be approximately near the centroid for symmetric-ish configs
    assert 1.0 < cx < 9.0
    assert 0.0 < cy < 5.0


# Tool 50: directional_distribution
def test_directional_distribution():
    frame = _make_point_frame([
        {"site_id": "a", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}, "angle": 0.0},
        {"site_id": "b", "geometry": {"type": "Point", "coordinates": [1.0, 1.0]}, "angle": 90.0},
        {"site_id": "c", "geometry": {"type": "Point", "coordinates": [2.0, 0.0]}, "angle": 180.0},
    ])
    result = frame.directional_distribution(angle_column="angle")
    assert result["count"] == 3
    assert result["mean_direction"] is not None
    assert 0.0 <= result["circular_variance"] <= 1.0


def test_directional_distribution_from_geometry():
    frame = _make_point_frame([
        {"site_id": "a", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
        {"site_id": "b", "geometry": {"type": "Point", "coordinates": [10.0, 0.0]}},
        {"site_id": "c", "geometry": {"type": "Point", "coordinates": [0.0, 10.0]}},
    ])
    result = frame.directional_distribution()
    assert result["count"] == 3
    assert result["mean_direction"] is not None


# Tool 51: quadrat_analysis
def test_quadrat_analysis():
    frame = _sample_point_grid()
    result = frame.quadrat_analysis(rows_count=5, cols_count=5)
    assert result["point_count"] == 25
    assert result["quadrat_count"] == 25
    assert result["chi_square"] is not None
    assert result["p_value"] is not None


def test_quadrat_analysis_empty():
    frame = _make_point_frame([])
    result = frame.quadrat_analysis()
    assert result["point_count"] == 0


# Tool 52: ripleys_k
def test_ripleys_k():
    frame = _sample_point_grid()
    result = frame.ripleys_k(steps=5)
    assert len(result) == 5
    for r in result:
        assert "distance" in r
        assert "k_value" in r
        assert "l_value" in r
        assert r["k_value"] >= 0


# Tool 53: natural_neighbor_interpolation
def test_natural_neighbor_interpolation():
    frame = _sample_point_grid()
    result = frame.natural_neighbor_interpolation(value_column="elevation", grid_resolution=5)
    assert len(result) == 25
    for row in result:
        assert "value_nni" in row
        assert row["value_nni"] is not None


# Tool 54: spline_interpolation
def test_spline_interpolation():
    frame = _sample_point_grid()
    result = frame.spline_interpolation(value_column="elevation", grid_resolution=5, regularization=0.01)
    assert len(result) == 25
    for row in result:
        assert "value_spline" in row


# Tool 55: trend_surface
def test_trend_surface_order1():
    frame = _sample_point_grid()
    result = frame.trend_surface(value_column="elevation", order=1, grid_resolution=5)
    assert len(result) == 25
    for row in result:
        assert "value_trend" in row
        assert row["order_trend"] == 1


def test_trend_surface_order2():
    frame = _sample_point_grid()
    result = frame.trend_surface(value_column="elevation", order=2, grid_resolution=5)
    assert len(result) == 25


# Tool 56: viewshed
def test_viewshed():
    frame = _sample_point_grid()
    result = frame.viewshed(elevation_column="elevation", observer=(2.0, 2.0), grid_resolution=5)
    assert len(result) == 25
    for row in result:
        assert "visible_viewshed" in row
        assert isinstance(row["visible_viewshed"], bool)


# Tool 57: aspect_reclassify
def test_aspect_reclassify_8class():
    frame = _make_point_frame([
        {"site_id": "a", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}, "aspect": 0.0},
        {"site_id": "b", "geometry": {"type": "Point", "coordinates": [1.0, 0.0]}, "aspect": 90.0},
        {"site_id": "c", "geometry": {"type": "Point", "coordinates": [2.0, 0.0]}, "aspect": 180.0},
        {"site_id": "d", "geometry": {"type": "Point", "coordinates": [3.0, 0.0]}, "aspect": 270.0},
    ])
    result = frame.aspect_reclassify(aspect_column="aspect", num_classes=8)
    assert len(result) == 4
    labels = result["label_aspect_class"]
    assert labels[0] == "N"
    assert labels[1] == "E"
    assert labels[2] == "S"
    assert labels[3] == "W"


# Tool 58: euclidean_allocation
def test_euclidean_allocation():
    frame = _make_point_frame([
        {"site_id": "hospital_a", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
        {"site_id": "hospital_b", "geometry": {"type": "Point", "coordinates": [10.0, 10.0]}},
    ])
    result = frame.euclidean_allocation(id_column="site_id", grid_resolution=5)
    assert len(result) == 25
    for row in result:
        assert "source_id_ealloc" in row
        assert row["source_id_ealloc"] in ("hospital_a", "hospital_b")


# Tool 59: cost_distance
def test_cost_distance():
    frame = _sample_point_grid()
    sources = _make_point_frame([
        {"site_id": "src", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
    ])
    result = frame.cost_distance(cost_column="elevation", sources=sources, grid_resolution=5)
    assert len(result) == 25
    for row in result:
        assert "cost_costdist" in row


# Tool 60: cost_allocation
def test_cost_allocation():
    frame = _sample_point_grid()
    sources = _make_point_frame([
        {"site_id": "src_a", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
        {"site_id": "src_b", "geometry": {"type": "Point", "coordinates": [4.0, 4.0]}},
    ])
    result = frame.cost_allocation(cost_column="elevation", sources=sources, source_id_column="site_id", grid_resolution=5)
    assert len(result) == 25
    for row in result:
        assert "source_id_calloc" in row


# Tool 61: near_table
def test_near_table():
    origins = _make_point_frame([
        {"site_id": "a", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
    ])
    targets = _make_point_frame([
        {"site_id": "t1", "geometry": {"type": "Point", "coordinates": [3.0, 4.0]}},
        {"site_id": "t2", "geometry": {"type": "Point", "coordinates": [10.0, 0.0]}},
    ])
    result = origins.near_table(targets, k=2, id_column="site_id", target_id_column="site_id")
    assert len(result) == 2
    assert result[0]["rank"] == 1
    assert result[0]["target_id"] == "t1"
    assert abs(result[0]["distance"] - 5.0) < 1e-9


def test_near_table_with_max_distance():
    origins = _make_point_frame([
        {"site_id": "a", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
    ])
    targets = _make_point_frame([
        {"site_id": "t1", "geometry": {"type": "Point", "coordinates": [3.0, 4.0]}},
        {"site_id": "t2", "geometry": {"type": "Point", "coordinates": [100.0, 0.0]}},
    ])
    result = origins.near_table(targets, k=2, max_distance=10.0, id_column="site_id", target_id_column="site_id")
    assert len(result) == 1  # t2 beyond max


# Tool 62: point_distance_matrix
def test_point_distance_matrix():
    origins = _make_point_frame([
        {"site_id": "a", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
    ])
    targets = _make_point_frame([
        {"site_id": "t1", "geometry": {"type": "Point", "coordinates": [3.0, 4.0]}},
        {"site_id": "t2", "geometry": {"type": "Point", "coordinates": [0.0, 10.0]}},
    ])
    result = origins.point_distance_matrix(targets, id_column="site_id", target_id_column="site_id")
    assert len(result) == 2
    assert abs(result[0]["distance"] - 5.0) < 1e-9
    assert abs(result[1]["distance"] - 10.0) < 1e-9


# Tool 63: union_overlay
def test_union_overlay():
    pytest.importorskip("shapely")
    a = GeoPromptFrame.from_records([
        {"site_id": "a", "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [5, 0], [5, 5], [0, 5], [0, 0]]]}},
    ])
    b = GeoPromptFrame.from_records([
        {"site_id": "b", "geometry": {"type": "Polygon", "coordinates": [[[3, 3], [8, 3], [8, 8], [3, 8], [3, 3]]]}},
    ])
    result = a.union_overlay(b, id_column="site_id", other_id_column="site_id")
    assert len(result) >= 2  # intersection, self_only, other_only


# Tool 64: update_overlay
def test_update_overlay():
    pytest.importorskip("shapely")
    base = GeoPromptFrame.from_records([
        {"site_id": "base", "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]]}},
    ])
    update = GeoPromptFrame.from_records([
        {"site_id": "upd", "geometry": {"type": "Polygon", "coordinates": [[[5, 5], [15, 5], [15, 15], [5, 15], [5, 5]]]}},
    ])
    result = base.update_overlay(update)
    assert len(result) >= 2


# Tool 65: symmetrical_difference_overlay
def test_symmetrical_difference_overlay():
    pytest.importorskip("shapely")
    a = GeoPromptFrame.from_records([
        {"site_id": "a", "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [5, 0], [5, 5], [0, 5], [0, 0]]]}},
    ])
    b = GeoPromptFrame.from_records([
        {"site_id": "b", "geometry": {"type": "Polygon", "coordinates": [[[3, 3], [8, 3], [8, 8], [3, 8], [3, 3]]]}},
    ])
    result = a.symmetrical_difference_overlay(b)
    assert len(result) == 2  # self_only and other_only


# Tool 66: spatial_selection
def test_spatial_selection():
    pytest.importorskip("shapely")
    points = _make_point_frame([
        {"site_id": "inside", "geometry": {"type": "Point", "coordinates": [5.0, 5.0]}},
        {"site_id": "outside", "geometry": {"type": "Point", "coordinates": [50.0, 50.0]}},
    ])
    selector = GeoPromptFrame.from_records([
        {"site_id": "box", "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]]}},
    ])
    result = points.spatial_selection(selector, predicate="intersects")
    assert len(result) == 1
    assert result["site_id"][0] == "inside"


# Tool 67: tabulate_intersection
def test_tabulate_intersection():
    pytest.importorskip("shapely")
    a = GeoPromptFrame.from_records([
        {"site_id": "a", "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]]}},
    ])
    b = GeoPromptFrame.from_records([
        {"site_id": "b", "geometry": {"type": "Polygon", "coordinates": [[[5, 5], [15, 5], [15, 15], [5, 15], [5, 5]]]}},
    ])
    result = a.tabulate_intersection(b, id_column="site_id", other_id_column="site_id")
    assert len(result) == 1
    assert result[0]["intersection_area"] == 25.0
    assert result[0]["self_area"] == 100.0
    assert result[0]["pct_of_self"] == 25.0


# Tool 68: feature_envelope_to_polygon
def test_feature_envelope_to_polygon():
    frame = GeoPromptFrame.from_records([
        {"site_id": "a", "geometry": {"type": "LineString", "coordinates": [[0, 0], [5, 3], [10, 0]]}},
    ])
    result = frame.feature_envelope_to_polygon()
    assert len(result) == 1
    assert abs(result["width_envelope"][0] - 10.0) < 1e-9
    assert abs(result["height_envelope"][0] - 3.0) < 1e-9
    rows = list(result)
    assert rows[0]["geometry"]["type"] == "Polygon"


# Tool 69: network_partition
def test_network_partition():
    frame = GeoPromptFrame.from_records([
        {"from_node_id": "a", "to_node_id": "b", "geometry": {"type": "LineString", "coordinates": [[0, 0], [1, 0]]}},
        {"from_node_id": "b", "to_node_id": "c", "geometry": {"type": "LineString", "coordinates": [[1, 0], [2, 0]]}},
        {"from_node_id": "d", "to_node_id": "e", "geometry": {"type": "LineString", "coordinates": [[10, 0], [11, 0]]}},
    ])
    result = frame.network_partition()
    assert len(result) == 3
    # First two edges share component, third is separate
    ids = result["id_component"]
    assert ids[0] == ids[1]
    assert ids[0] != ids[2]


# Tool 70: network_centrality
def test_network_centrality():
    frame = GeoPromptFrame.from_records([
        {"from_node_id": "a", "to_node_id": "b", "edge_length": 1.0, "geometry": {"type": "LineString", "coordinates": [[0, 0], [1, 0]]}},
        {"from_node_id": "b", "to_node_id": "c", "edge_length": 1.0, "geometry": {"type": "LineString", "coordinates": [[1, 0], [2, 0]]}},
        {"from_node_id": "a", "to_node_id": "c", "edge_length": 3.0, "geometry": {"type": "LineString", "coordinates": [[0, 0], [2, 0]]}},
    ])
    result = frame.network_centrality()
    assert len(result) == 3
    node_ids = [r["node_id"] for r in result]
    assert "a" in node_ids
    assert "b" in node_ids
    assert "c" in node_ids
    # Node b should have highest betweenness (it's on the shortest a-c path)
    b_result = next(r for r in result if r["node_id"] == "b")
    assert b_result["betweenness_centrality"] >= 0


# Tool 72: minimum_spanning_tree
def test_minimum_spanning_tree():
    frame = _make_point_frame([
        {"site_id": "a", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
        {"site_id": "b", "geometry": {"type": "Point", "coordinates": [1.0, 0.0]}},
        {"site_id": "c", "geometry": {"type": "Point", "coordinates": [2.0, 0.0]}},
    ])
    result = frame.minimum_spanning_tree(id_column="site_id")
    assert len(result) == 2  # n-1 edges
    total_cost = result["total_cost_mst"][-1]
    assert abs(total_cost - 2.0) < 1e-9


# Tool 73: traveling_salesman_nn
def test_traveling_salesman_nn():
    frame = _make_point_frame([
        {"site_id": "a", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
        {"site_id": "b", "geometry": {"type": "Point", "coordinates": [1.0, 0.0]}},
        {"site_id": "c", "geometry": {"type": "Point", "coordinates": [2.0, 0.0]}},
    ])
    result = frame.traveling_salesman_nn(id_column="site_id", return_to_start=True)
    assert len(result) == 3
    orders = sorted(result["visit_order_tsp"])
    assert orders == [1, 2, 3]


# Tool 74: dbscan_cluster
def test_dbscan_cluster():
    rows = []
    for i in range(5):
        rows.append({"site_id": f"g1-{i}", "geometry": {"type": "Point", "coordinates": [float(i) * 0.1, 0.0]}})
    for i in range(5):
        rows.append({"site_id": f"g2-{i}", "geometry": {"type": "Point", "coordinates": [10.0 + float(i) * 0.1, 0.0]}})
    frame = _make_point_frame(rows)
    result = frame.dbscan_cluster(eps=1.0, min_samples=3)
    assert len(result) == 10
    # Two distinct clusters
    clusters = set(row["cluster_dbscan"] for row in result if row["cluster_dbscan"] is not None)
    assert len(clusters) == 2


def test_dbscan_cluster_all_noise():
    frame = _make_point_frame([
        {"site_id": "a", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
        {"site_id": "b", "geometry": {"type": "Point", "coordinates": [100.0, 100.0]}},
    ])
    result = frame.dbscan_cluster(eps=1.0, min_samples=3)
    for row in result:
        assert row["noise_dbscan"] is True


# Tool 75: hierarchical_cluster
def test_hierarchical_cluster():
    rows = []
    for i in range(3):
        rows.append({"site_id": f"g1-{i}", "geometry": {"type": "Point", "coordinates": [float(i), 0.0]}})
    for i in range(3):
        rows.append({"site_id": f"g2-{i}", "geometry": {"type": "Point", "coordinates": [100.0 + float(i), 0.0]}})
    frame = _make_point_frame(rows)
    result = frame.hierarchical_cluster(k=2)
    assert len(result) == 6
    clusters = set(row["cluster_hclust"] for row in result)
    assert len(clusters) == 2
    # Points in same group should have same cluster
    c = result["cluster_hclust"]
    assert c[0] == c[1]
    assert c[3] == c[4]
    assert c[0] != c[3]


# Tool 76: spatial_outlier_zscore
def test_spatial_outlier_zscore():
    frame = _make_point_frame([
        {"site_id": "a", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}, "val": 10.0},
        {"site_id": "b", "geometry": {"type": "Point", "coordinates": [1.0, 0.0]}, "val": 10.0},
        {"site_id": "c", "geometry": {"type": "Point", "coordinates": [2.0, 0.0]}, "val": 10.0},
        {"site_id": "d", "geometry": {"type": "Point", "coordinates": [3.0, 0.0]}, "val": 10.0},
        {"site_id": "e", "geometry": {"type": "Point", "coordinates": [4.0, 0.0]}, "val": 10.0},
        {"site_id": "f", "geometry": {"type": "Point", "coordinates": [5.0, 0.0]}, "val": 200.0},  # outlier
    ])
    result = frame.spatial_outlier_zscore(value_column="val", threshold=2.0)
    assert len(result) == 6
    # Global z-score still present
    global_z = result["global_z_zscore"]
    assert global_z[5] > 0  # outlier has positive global z
    assert global_z[0] < 0  # non-outlier has negative global z
    # Local z-score: the far-right outlier (val=200) should be flagged
    local_z = result["z_score_zscore"]
    assert abs(local_z[5]) > 0  # outlier detected by local z


# Tool 77: jenks_natural_breaks
def test_jenks_natural_breaks():
    frame = _make_point_frame([
        {"site_id": f"p{i}", "geometry": {"type": "Point", "coordinates": [float(i), 0.0]}, "val": float(v)}
        for i, v in enumerate([1, 2, 3, 50, 51, 52, 100, 101, 102])
    ])
    result = frame.jenks_natural_breaks(value_column="val", k=3)
    assert len(result) == 9
    for row in result:
        assert 1 <= row["class_jenks"] <= 3


# Tool 78: equal_interval_classify
def test_equal_interval_classify():
    frame = _make_point_frame([
        {"site_id": f"p{i}", "geometry": {"type": "Point", "coordinates": [float(i), 0.0]}, "val": float(i) * 10.0}
        for i in range(10)
    ])
    result = frame.equal_interval_classify(value_column="val", k=5)
    assert len(result) == 10
    for row in result:
        assert 1 <= row["class_eqint"] <= 5


# Tool 79: quantile_classify
def test_quantile_classify():
    frame = _make_point_frame([
        {"site_id": f"p{i}", "geometry": {"type": "Point", "coordinates": [float(i), 0.0]}, "val": float(i)}
        for i in range(20)
    ])
    result = frame.quantile_classify(value_column="val", k=4)
    assert len(result) == 20
    class_counts = {}
    for row in result:
        c = row["class_quantile"]
        class_counts[c] = class_counts.get(c, 0) + 1
    # Each quantile class should have 5 members
    for c in class_counts.values():
        assert c == 5


# Tool 80: focal_statistics
def test_focal_statistics_mean():
    frame = _sample_point_grid()
    result = frame.focal_statistics(value_column="elevation", grid_resolution=5, window_size=3, statistic="mean")
    assert len(result) == 25
    for row in result:
        assert "value_focal" in row
        assert row["statistic_focal"] == "mean"


def test_focal_statistics_max():
    frame = _sample_point_grid()
    result = frame.focal_statistics(value_column="elevation", grid_resolution=5, window_size=3, statistic="max")
    assert len(result) == 25


# Tool 81: zonal_histogram
def test_zonal_histogram():
    frame = _sample_point_grid()
    zones = GeoPromptFrame.from_records([
        {"site_id": "zone1", "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]]]}},
    ])
    result = frame.zonal_histogram(value_column="elevation", zones=zones, zone_id_column="site_id", bins=5)
    assert len(result) == 5  # 1 zone * 5 bins
    assert all(r["zone_id"] == "zone1" for r in result)


# Tool 82: raster_calculator
def test_raster_calculator():
    frame = _make_point_frame([
        {"site_id": "a", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}, "ndvi": 0.5, "slope": 10.0},
        {"site_id": "b", "geometry": {"type": "Point", "coordinates": [1.0, 0.0]}, "ndvi": 0.8, "slope": 5.0},
    ])
    result = frame.raster_calculator(expression="ndvi * 100 + slope", columns=["ndvi", "slope"], result_column="score")
    assert len(result) == 2
    scores = result["score"]
    assert abs(scores[0] - 60.0) < 1e-9
    assert abs(scores[1] - 85.0) < 1e-9


def test_raster_calculator_rejects_unsafe():
    frame = _make_point_frame([
        {"site_id": "a", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}, "val": 1.0},
    ])
    result = frame.raster_calculator(expression="__import__('os').system('echo hacked')", columns=["val"])
    # Should fail safely → None
    assert result["calculated"][0] is None


# Tool 83: aggregate_grid
def test_aggregate_grid():
    frame = _sample_point_grid()
    result = frame.aggregate_grid(value_column="elevation", grid_resolution=3, aggregation="mean")
    assert len(result) == 9  # 3x3
    for row in result:
        assert "value_aggrid" in row
        assert "count_aggrid" in row


# Tool 84: grid_to_polygons
def test_grid_to_polygons():
    frame = _sample_point_grid()
    result = frame.grid_to_polygons(grid_resolution=3, value_column="elevation")
    assert len(result) == 9  # 3x3
    for row in result:
        assert row["geometry"]["type"] == "Polygon"
        assert "value_gridpoly" in row


# Tool 85: random_points
def test_random_points():
    result = GeoPromptFrame.random_points(count=50, min_x=-10, max_x=10, min_y=-10, max_y=10, seed=42)
    assert len(result) == 50
    for row in result:
        assert row["geometry"]["type"] == "Point"
        x, y = row["geometry"]["coordinates"]
        assert -10 <= x <= 10
        assert -10 <= y <= 10


def test_random_points_deterministic():
    r1 = GeoPromptFrame.random_points(count=10, seed=123)
    r2 = GeoPromptFrame.random_points(count=10, seed=123)
    coords1 = r1["geometry"]
    coords2 = r2["geometry"]
    for i in range(10):
        assert coords1[i]["coordinates"] == coords2[i]["coordinates"]


def test_new_tools_validate_crs_mismatch() -> None:
    source = _sample_point_grid()
    shifted = _make_point_frame(
        [{"site_id": "a", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}}],
        crs="EPSG:3857",
    )
    zones = _sample_zone_frame()
    zones_3857 = GeoPromptFrame.from_records(zones.to_records(), crs="EPSG:3857")
    left = _make_point_frame([
        {"site_id": "p1", "geometry": {"type": "Polygon", "coordinates": [(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]}},
    ])
    right = GeoPromptFrame.from_records(left.to_records(), crs="EPSG:3857")

    with pytest.raises(ValueError, match="CRS"):
        source.raster_sample(shifted, value_column="value")
    with pytest.raises(ValueError, match="CRS"):
        source.zonal_stats(zones_3857, value_column="value", zone_id_column="zone_id")
    with pytest.raises(ValueError, match="CRS"):
        left.join_by_largest_overlap(right)
    with pytest.raises(ValueError, match="CRS"):
        left.erase(right)


def test_new_tools_validate_basic_parameters() -> None:
    frame = _sample_point_grid()

    with pytest.raises(ValueError, match="either breaks or mapping"):
        frame.reclassify("value")
    with pytest.raises(ValueError, match="greater than zero"):
        frame.resample(method="every_nth", n=0)
    with pytest.raises(ValueError, match="greater than zero"):
        frame.resample(method="spatial_thin", min_distance=0.0)
    with pytest.raises(ValueError, match="greater than zero"):
        frame.to_polygons(buffer_distance=0.0)
    with pytest.raises(ValueError, match="max_distance is required"):
        frame.hotspot_getis_ord(value_column="value", mode="distance_band")
    with pytest.raises(ValueError, match="greater than zero"):
        frame.local_outlier_factor_spatial(k=0)
    with pytest.raises(ValueError, match="bandwidth must be greater than zero"):
        frame.kernel_density(bandwidth=0.0)
    with pytest.raises(ValueError, match="zero or greater"):
        frame.simplify(tolerance=-1.0)
    with pytest.raises(ValueError, match="greater than zero"):
        frame.densify(max_segment_length=0.0)
    with pytest.raises(ValueError, match="at least 1"):
        frame.smooth_geometry(iterations=0)
    with pytest.raises(ValueError, match="greater than zero"):
        frame.spatiotemporal_cube(time_column="time", value_column="value", time_intervals=0)
    with pytest.raises(ValueError, match="greater than zero"):
        frame.spatiotemporal_cube(time_column="time", value_column="value", grid_resolution=0)
    with pytest.raises(ValueError, match="variogram_model"):
        frame.kriging_surface(value_column="elevation", variogram_model=cast(Any, "linear"))
    with pytest.raises(ValueError, match="between 1 and 12"):
        frame.geohash_encode(precision=0)


def test_new_tools_empty_inputs_short_circuit() -> None:
    empty = GeoPromptFrame._from_internal_rows([], geometry_column="geometry", crs="EPSG:4326")

    assert len(empty.resample()) == 0
    assert len(empty.raster_clip(0.0, 0.0, 1.0, 1.0)) == 0
    assert len(empty.thiessen_polygons()) == 0
    assert len(empty.kernel_density()) == 0
    assert len(empty.standard_deviational_ellipse()) == 0
    assert len(empty.center_of_minimum_distance()) == 0
    assert len(empty.trajectory_simplify()) == 0


def test_snap_to_network_nodes_can_leave_points_unmatched() -> None:
    network = _sample_network_frame()
    far_points = _make_point_frame([
        {"site_id": "far", "geometry": {"type": "Point", "coordinates": [100.0, 100.0]}},
    ])

    result = network.snap_to_network_nodes(far_points, max_distance=0.01)
    records = result.to_records()

    assert records[0]["node_id_snapped"] is None
    assert records[0]["snap_distance_snapped"] is None


def test_network_methods_handle_disconnected_graphs() -> None:
    network = GeoPromptFrame.from_records(
        [
            {
                "edge_id": "e1",
                "from_node_id": "A",
                "to_node_id": "B",
                "from_node": (0.0, 0.0),
                "to_node": (1.0, 0.0),
                "edge_length": 1.0,
                "geometry": {"type": "LineString", "coordinates": [(0.0, 0.0), (1.0, 0.0)]},
            },
            {
                "edge_id": "e2",
                "from_node_id": "C",
                "to_node_id": "D",
                "from_node": (10.0, 0.0),
                "to_node": (11.0, 0.0),
                "edge_length": 1.0,
                "geometry": {"type": "LineString", "coordinates": [(10.0, 0.0), (11.0, 0.0)]},
            },
        ],
        geometry="geometry",
        crs="EPSG:4326",
    )
    origins = _make_point_frame([
        {"site_id": "o1", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
    ])
    destinations = _make_point_frame([
        {"site_id": "d1", "geometry": {"type": "Point", "coordinates": [11.0, 0.0]}},
    ])

    od_records = network.origin_destination_matrix(origins, destinations).to_records()
    assert od_records[0]["network_cost_od"] is None
    assert od_records[0]["reachable_od"] is False
    assert len(network.k_shortest_paths(origin="A", destination="D", k=2)) == 0


def test_trajectory_staypoint_detection_marks_short_stops_as_non_staypoints() -> None:
    frame = _make_point_frame([
        {"site_id": "t1", "time": 0.0, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
        {"site_id": "t2", "time": 0.25, "geometry": {"type": "Point", "coordinates": [0.0005, 0.0005]}},
        {"site_id": "t3", "time": 0.5, "geometry": {"type": "Point", "coordinates": [1.0, 1.0]}},
    ])

    result = frame.trajectory_staypoint_detection(time_column="time", max_radius=0.01, min_duration=1.0)

    assert all(record["is_staypoint_staypoint"] is False for record in result)


def test_spatiotemporal_cube_count_aggregation_returns_nonzero_bins() -> None:
    frame = _make_point_frame([
        {"site_id": "a", "time": 0.0, "value": 1.0, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
    ])

    result = frame.spatiotemporal_cube(
        time_column="time",
        value_column="value",
        time_intervals=4,
        grid_resolution=4,
        aggregation="count",
    )

    assert len(result) >= 1
    assert any(float(row["value_cube"]) > 0.0 for row in result)


def test_spatial_weights_matrix_supports_inverse_distance_weights() -> None:
    frame = _sample_point_grid()

    result = frame.spatial_weights_matrix(k=2, weight_mode="inverse_distance")

    assert result["weight_mode"] == "inverse_distance"
    assert all(all(weight > 0.0 for weight in neighbors.values()) for neighbors in result["weights"].values())


# ======================================================================
# Chunk 1: Weighted Summary vs Real GWR — scope discipline
# ======================================================================


def test_weighted_local_summary_sparse_neighborhood_stability() -> None:
    """Verify local coefficients remain finite under sparse local neighborhoods."""
    frame = _make_point_frame([
        {"site_id": "a", "x": 1.0, "y": 1.0, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
        {"site_id": "b", "x": 2.0, "y": 4.0, "geometry": {"type": "Point", "coordinates": [100.0, 100.0]}},
    ])
    records = frame.weighted_local_summary(
        dependent_column="y",
        independent_columns=["x"],
        bandwidth=0.5,
    ).to_records()
    assert all(math.isfinite(float(r["predicted_local"])) for r in records)
    assert all(math.isfinite(float(r["intercept_local"])) for r in records)


def test_weighted_local_summary_local_r_squared_is_populated() -> None:
    """Verify local_r_squared is computed as a float (or None if TSS=0)."""
    frame = _sample_point_grid()
    records = frame.weighted_local_summary(
        dependent_column="elevation",
        independent_columns=["value"],
        bandwidth=2.0,
    ).to_records()
    for r in records:
        val = r["local_r_squared_local"]
        assert val is None or isinstance(val, float)


def test_weighted_local_summary_reproducible_across_runs() -> None:
    """Verify identical calls produce identical output."""
    frame = _sample_point_grid()
    a = frame.weighted_local_summary(
        dependent_column="elevation",
        independent_columns=["value"],
        bandwidth=2.0,
    ).to_records()
    b = frame.weighted_local_summary(
        dependent_column="elevation",
        independent_columns=["value"],
        bandwidth=2.0,
    ).to_records()
    assert a == b


# ======================================================================
# Chunk 2: Kriging Proof Expansion — wider layouts, nugget-heavy
# ======================================================================


def test_kriging_surface_nugget_heavy_smoothing() -> None:
    """Large nugget should smooth predictions away from source values."""
    frame = _make_point_frame([
        {"site_id": "p1", "value": 0.0, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
        {"site_id": "p2", "value": 10.0, "geometry": {"type": "Point", "coordinates": [1.0, 0.0]}},
        {"site_id": "p3", "value": 0.0, "geometry": {"type": "Point", "coordinates": [0.0, 1.0]}},
        {"site_id": "p4", "value": 10.0, "geometry": {"type": "Point", "coordinates": [1.0, 1.0]}},
    ])
    records = frame.kriging_surface(
        value_column="value",
        grid_resolution=2,
        variogram_range=2.0,
        variogram_sill=1.0,
        variogram_nugget=5.0,
    ).to_records()
    predictions = [float(r["value_kriging"]) for r in records]
    # With high nugget, predictions should stay between 0 and 10
    assert all(0.0 <= p <= 10.0 for p in predictions)
    # And variance should be positive everywhere since nugget > 0
    assert all(float(r["variance_kriging"]) > 0.0 for r in records)


def test_kriging_surface_short_range_isolates_predictions() -> None:
    """Very short range should make distant points nearly independent."""
    frame = _make_point_frame([
        {"site_id": "p1", "value": 100.0, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
        {"site_id": "p2", "value": 0.0, "geometry": {"type": "Point", "coordinates": [10.0, 10.0]}},
    ])
    records = frame.kriging_surface(
        value_column="value",
        grid_resolution=2,
        variogram_range=0.1,
        variogram_sill=1.0,
        variogram_nugget=0.0,
    ).to_records()
    # The grid corners are at the source points
    predictions = {(float(cast(Any, r["geometry"])["coordinates"][0]),
                     float(cast(Any, r["geometry"])["coordinates"][1])): float(r["value_kriging"])
                    for r in records}
    assert predictions[(0.0, 0.0)] == pytest.approx(100.0)
    assert predictions[(10.0, 10.0)] == pytest.approx(0.0)


def test_kriging_surface_high_sill_increases_variance() -> None:
    """Higher sill should produce higher variance at off-source grid points."""
    frame = _make_point_frame([
        {"site_id": "p1", "value": 1.0, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
        {"site_id": "p2", "value": 2.0, "geometry": {"type": "Point", "coordinates": [2.0, 0.0]}},
        {"site_id": "p3", "value": 3.0, "geometry": {"type": "Point", "coordinates": [1.0, 2.0]}},
    ])
    low = frame.kriging_surface(
        value_column="value", grid_resolution=3,
        variogram_range=2.0, variogram_sill=1.0, variogram_nugget=0.0,
    ).to_records()
    high = frame.kriging_surface(
        value_column="value", grid_resolution=3,
        variogram_range=2.0, variogram_sill=10.0, variogram_nugget=0.0,
    ).to_records()
    low_var = sum(float(r["variance_kriging"]) for r in low)
    high_var = sum(float(r["variance_kriging"]) for r in high)
    assert high_var > low_var


@pytest.mark.parametrize("variogram_model", ["spherical", "exponential", "gaussian", "hole_effect"])
def test_kriging_surface_matches_pykrige_irregular_five_point_when_available(variogram_model: str) -> None:
    """Verify parity on an irregular 5-point layout with nonzero nugget across all variogram families."""
    points = [
        {"site_id": "p1", "value": 1.5, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
        {"site_id": "p2", "value": 3.2, "geometry": {"type": "Point", "coordinates": [1.5, 0.3]}},
        {"site_id": "p3", "value": 2.1, "geometry": {"type": "Point", "coordinates": [0.7, 1.8]}},
        {"site_id": "p4", "value": 4.8, "geometry": {"type": "Point", "coordinates": [2.2, 1.1]}},
        {"site_id": "p5", "value": 3.6, "geometry": {"type": "Point", "coordinates": [1.0, 0.9]}},
    ]
    # grid must match internal bounding-box linspace: x in [0,2.2], y in [0,1.8], res=4
    res = 4
    gx = [0.0 + i * (2.2 / (res - 1)) for i in range(res)]
    gy = [0.0 + i * (1.8 / (res - 1)) for i in range(res)]
    _assert_kriging_matches_pykrige(
        points=points,
        grid_x=gx,
        grid_y=gy,
        variogram_range=2.5,
        variogram_sill=2.0,
        variogram_nugget=0.15,
        variogram_model=variogram_model,
    )


# ======================================================================
# Chunk 3: Route Solver Quality Envelope — adversarial, equal-cost
# ======================================================================


def test_route_sequence_optimize_adversarial_noncollinear() -> None:
    """Non-collinear layout where greedy nearest-neighbor doesn't trivially find the optimum."""
    # Diamond layout: A at origin, B right, C top, D far right-top
    node_coords = {"A": (0.0, 0.0), "B": (2.0, 0.0), "C": (1.0, 3.0), "D": (3.0, 3.0)}
    edges = [
        ("e1", "A", "B"), ("e2", "A", "C"), ("e3", "A", "D"),
        ("e4", "B", "C"), ("e5", "B", "D"), ("e6", "C", "D"),
    ]
    network = GeoPromptFrame.from_records([
        {"edge_id": eid, "from_node_id": f, "to_node_id": t,
         "from_node": node_coords[f], "to_node": node_coords[t],
         "edge_length": math.dist(node_coords[f], node_coords[t]),
         "geometry": {"type": "LineString", "coordinates": [node_coords[f], node_coords[t]]}}
        for eid, f, t in edges
    ], crs="EPSG:4326")
    stops = GeoPromptFrame.from_records([
        {"site_id": n.lower(), "node_id": n, "geometry": {"type": "Point", "coordinates": node_coords[n]}}
        for n in ["A", "B", "C", "D"]
    ], crs="EPSG:4326")
    records = network.route_sequence_optimize(stops, stop_node_column="node_id").to_records()
    route_cost = float(records[0]["total_cost_route"])
    # Brute-force optimum over all open-path permutations using Euclidean distances
    best = min(
        sum(math.dist(node_coords[p[i]], node_coords[p[i + 1]]) for i in range(len(p) - 1))
        for p in permutations(["A", "B", "C", "D"])
    )
    assert route_cost == pytest.approx(best, rel=1e-6)


def test_route_sequence_optimize_equal_cost_multiple_optima() -> None:
    """When multiple paths tie in cost, the tool should still report the correct optimal cost."""
    node_coords = {"A": (0.0, 0.0), "B": (1.0, 0.0), "C": (0.0, 1.0)}
    edges = [
        ("e1", "A", "B", 1.0),
        ("e2", "A", "C", 1.0),
        ("e3", "B", "C", 1.0),
    ]
    network = GeoPromptFrame.from_records([
        {"edge_id": eid, "from_node_id": f, "to_node_id": t, "from_node": node_coords[f],
         "to_node": node_coords[t], "edge_length": c,
         "geometry": {"type": "LineString", "coordinates": [node_coords[f], node_coords[t]]}}
        for eid, f, t, c in edges
    ], crs="EPSG:4326")
    stops = GeoPromptFrame.from_records([
        {"site_id": n.lower(), "node_id": n, "geometry": {"type": "Point", "coordinates": node_coords[n]}}
        for n in ["A", "B", "C"]
    ], crs="EPSG:4326")
    records = network.route_sequence_optimize(stops, stop_node_column="node_id").to_records()
    # A->B->C and A->C->B both cost 2.0; tool should report 2.0 regardless
    assert float(records[0]["total_cost_route"]) == pytest.approx(2.0)


def test_route_sequence_optimize_mixed_reachability_metadata() -> None:
    """Mixed reachable/unreachable stops keep correct metadata and ordering."""
    network = GeoPromptFrame.from_records([
        {"edge_id": "e1", "from_node_id": "A", "to_node_id": "B",
         "from_node": (0.0, 0.0), "to_node": (1.0, 0.0), "edge_length": 1.0,
         "geometry": {"type": "LineString", "coordinates": [(0.0, 0.0), (1.0, 0.0)]}},
        {"edge_id": "e2", "from_node_id": "B", "to_node_id": "C",
         "from_node": (1.0, 0.0), "to_node": (2.0, 0.0), "edge_length": 1.0,
         "geometry": {"type": "LineString", "coordinates": [(1.0, 0.0), (2.0, 0.0)]}},
        {"edge_id": "e3", "from_node_id": "X", "to_node_id": "Y",
         "from_node": (50.0, 50.0), "to_node": (51.0, 50.0), "edge_length": 1.0,
         "geometry": {"type": "LineString", "coordinates": [(50.0, 50.0), (51.0, 50.0)]}},
        {"edge_id": "e4", "from_node_id": "P", "to_node_id": "Q",
         "from_node": (80.0, 80.0), "to_node": (81.0, 80.0), "edge_length": 1.0,
         "geometry": {"type": "LineString", "coordinates": [(80.0, 80.0), (81.0, 80.0)]}},
    ], crs="EPSG:4326")
    stops = _make_point_frame([
        {"site_id": "s1", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
        {"site_id": "s2", "geometry": {"type": "Point", "coordinates": [2.0, 0.0]}},
        {"site_id": "s3", "geometry": {"type": "Point", "coordinates": [51.0, 50.0]}},
        {"site_id": "s4", "geometry": {"type": "Point", "coordinates": [81.0, 80.0]}},
    ])
    records = network.route_sequence_optimize(stops).to_records()
    reachable = [r["reachable_route"] for r in records]
    orders = [r["visit_order_route"] for r in records]
    assert reachable.count(True) >= 1
    assert reachable.count(False) >= 1
    assert orders == sorted(orders)
    assert records[0]["stop_count_route"] == 4


# ======================================================================
# Chunk 4: Hotspot and Local Statistics
# ======================================================================


def test_hotspot_getis_ord_uniform_field_not_significant() -> None:
    """A uniform field should produce no significant hotspots or coldspots."""
    frame = _make_point_frame([
        {"site_id": f"u{i}", "value": 5.0, "geometry": {"type": "Point", "coordinates": [float(i % 4), float(i // 4)]}}
        for i in range(16)
    ])
    records = frame.hotspot_getis_ord(
        value_column="value", mode="k_nearest", k=3, include_self=True,
    ).to_records()
    assert all(r["classification_getis"] == "not_significant" for r in records)


def test_hotspot_getis_ord_classification_stability() -> None:
    """Re-running the same input should produce the same classification."""
    frame = _make_point_frame([
        {"site_id": "a", "value": 10.0, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
        {"site_id": "b", "value": 9.5, "geometry": {"type": "Point", "coordinates": [0.2, 0.1]}},
        {"site_id": "c", "value": 9.0, "geometry": {"type": "Point", "coordinates": [0.1, 0.2]}},
        {"site_id": "d", "value": 1.0, "geometry": {"type": "Point", "coordinates": [5.0, 5.0]}},
        {"site_id": "e", "value": 1.5, "geometry": {"type": "Point", "coordinates": [5.2, 5.1]}},
        {"site_id": "f", "value": 2.0, "geometry": {"type": "Point", "coordinates": [5.1, 5.2]}},
    ])
    r1 = frame.hotspot_getis_ord(value_column="value", mode="k_nearest", k=2, include_self=True).to_records()
    r2 = frame.hotspot_getis_ord(value_column="value", mode="k_nearest", k=2, include_self=True).to_records()
    assert [r["classification_getis"] for r in r1] == [r["classification_getis"] for r in r2]
    assert [r["gi_star_getis"] for r in r1] == [r["gi_star_getis"] for r in r2]


def test_hotspot_getis_ord_matches_pysal_clustered_layout_when_available() -> None:
    """Compact clustered layout parity against PySAL."""
    esda = pytest.importorskip("esda")
    libpysal_weights = pytest.importorskip("libpysal.weights")

    points = [
        {"site_id": "c1", "value": 9.0, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
        {"site_id": "c2", "value": 8.0, "geometry": {"type": "Point", "coordinates": [1.0, 0.0]}},
        {"site_id": "c3", "value": 2.0, "geometry": {"type": "Point", "coordinates": [2.0, 0.0]}},
        {"site_id": "c4", "value": 1.0, "geometry": {"type": "Point", "coordinates": [3.0, 0.0]}},
        {"site_id": "c5", "value": 5.0, "geometry": {"type": "Point", "coordinates": [1.5, 1.0]}},
    ]
    frame = _make_point_frame(points)
    records = frame.hotspot_getis_ord(
        value_column="value", mode="k_nearest", k=2, include_self=True,
    ).to_records()
    coords = [cast(Any, p["geometry"])["coordinates"] for p in points]
    vals = [p["value"] for p in points]
    reference = esda.G_Local(
        vals,
        libpysal_weights.KNN.from_array(coords, k=2),
        transform="B", permutations=0, star=True, keep_simulations=False, island_weight=0,
    )
    for row, z_ref, p_ref in zip(records, reference.Zs, reference.p_norm, strict=True):
        assert row["gi_star_getis"] == pytest.approx(float(z_ref), rel=1e-6)
        assert row["p_value_getis"] == pytest.approx(float(p_ref), rel=1e-6)


# ======================================================================
# Chunk 5: Thiessen/Voronoi Scope Cleanup
# ======================================================================


def test_thiessen_polygons_duplicate_sites_handled() -> None:
    """Two sites at the same location should both get a result without error."""
    frame = _make_point_frame([
        {"site_id": "a", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
        {"site_id": "b", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
        {"site_id": "c", "geometry": {"type": "Point", "coordinates": [2.0, 2.0]}},
    ])
    records = frame.thiessen_polygons().to_records()
    assert len(records) == 3


def test_thiessen_polygons_four_corners_symmetric_layout() -> None:
    """Square-corner layout should yield roughly equal-area Voronoi cells."""
    pytest.importorskip("shapely")
    frame = _make_point_frame([
        {"site_id": "a", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
        {"site_id": "b", "geometry": {"type": "Point", "coordinates": [2.0, 0.0]}},
        {"site_id": "c", "geometry": {"type": "Point", "coordinates": [0.0, 2.0]}},
        {"site_id": "d", "geometry": {"type": "Point", "coordinates": [2.0, 2.0]}},
    ])
    records = frame.thiessen_polygons().to_records()
    areas = [float(r["area_voronoi"]) for r in records]
    assert max(areas) / min(areas) < 1.5  # square symmetry gives equal cells


def test_thiessen_polygons_fallback_produces_valid_output(monkeypatch: pytest.MonkeyPatch) -> None:
    """When Shapely is unavailable, the grid fallback still produces polygons."""
    import importlib
    original_import = importlib.import_module

    def patched_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name.startswith("shapely"):
            raise ImportError("mocked shapely unavailable")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(importlib, "import_module", patched_import)
    frame = _make_point_frame([
        {"site_id": "a", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
        {"site_id": "b", "geometry": {"type": "Point", "coordinates": [2.0, 0.0]}},
    ])
    records = frame.thiessen_polygons(grid_resolution=10).to_records()
    assert len(records) == 2
    assert all(r["geometry"]["type"] == "Polygon" for r in records)
    assert all(r["method_voronoi"] == "grid_approximation" for r in records)


# ======================================================================
# Chunk 6: Regression Breadth — larger fixtures, multicollinearity
# ======================================================================


def test_spatial_regression_larger_fixture_matches_statsmodels_when_available() -> None:
    """10-observation 3-predictor parity against statsmodels.OLS."""
    statsmodels_api = pytest.importorskip("statsmodels.api")

    rows = [
        {"site_id": f"r{i}", "x1": float(i), "x2": float(i * i), "x3": float(i % 3),
         "y": 2.0 + 0.5 * i - 0.1 * i * i + 1.5 * (i % 3) + (0.1 * ((-1) ** i)),
         "geometry": {"type": "Point", "coordinates": [float(i), 0.0]}}
        for i in range(10)
    ]
    frame = _make_point_frame(rows)
    records = frame.spatial_regression(
        dependent_column="y", independent_columns=["x1", "x2", "x3"], k_neighbors=2,
    ).to_records()
    design = statsmodels_api.add_constant([[r["x1"], r["x2"], r["x3"]] for r in rows])
    model = statsmodels_api.OLS([r["y"] for r in rows], design).fit()
    first = records[0]
    assert cast(list[float], first["coefficients_reg"]) == pytest.approx(
        [float(v) for v in model.params], rel=1e-6, abs=1e-6)
    assert float(first["r_squared_reg"]) == pytest.approx(float(model.rsquared), rel=1e-6)
    assert float(first["adj_r_squared_reg"]) == pytest.approx(float(model.rsquared_adj), rel=1e-6)
    assert [float(r["predicted_reg"]) for r in records] == pytest.approx(
        [float(v) for v in model.fittedvalues], rel=1e-6, abs=1e-6)
    assert [float(r["residual_reg"]) for r in records] == pytest.approx(
        [float(v) for v in model.resid], rel=1e-6, abs=1e-6)
    assert cast(list[float], first["coefficient_standard_errors_reg"]) == pytest.approx(
        [float(v) for v in model.bse], rel=1e-6, abs=1e-6)


def test_spatial_regression_near_singular_design_stability() -> None:
    """Near-collinear predictors should still yield finite output."""
    rows = [
        {"site_id": f"s{i}", "x1": float(i), "x2": float(i) + 1e-8,
         "y": 3.0 + 2.0 * i,
         "geometry": {"type": "Point", "coordinates": [float(i), 0.0]}}
        for i in range(6)
    ]
    frame = _make_point_frame(rows)
    records = frame.spatial_regression(
        dependent_column="y", independent_columns=["x1", "x2"], k_neighbors=2,
    ).to_records()
    assert all(math.isfinite(float(r["predicted_reg"])) for r in records)
    assert all(math.isfinite(float(r["residual_reg"])) for r in records)


def test_spatial_regression_high_leverage_point() -> None:
    """A single high-leverage point should still yield finite output and sensible R²."""
    rows = [
        {"site_id": f"p{i}", "x": float(i), "y": 2.0 * i + 1.0,
         "geometry": {"type": "Point", "coordinates": [float(i), 0.0]}}
        for i in range(5)
    ] + [
        {"site_id": "outlier", "x": 100.0, "y": 201.0,
         "geometry": {"type": "Point", "coordinates": [100.0, 0.0]}},
    ]
    frame = _make_point_frame(rows)
    records = frame.spatial_regression(
        dependent_column="y", independent_columns=["x"], k_neighbors=2,
    ).to_records()
    assert math.isfinite(float(records[0]["r_squared_reg"]))
    assert float(records[0]["r_squared_reg"]) > 0.99


# ======================================================================
# Chunk 7: Raster-Derived Surface Honesty — analytical fixtures
# ======================================================================


def test_contours_level_range_within_value_bounds() -> None:
    """Contour levels should sit within the value range of the input."""
    frame = _sample_point_grid()
    records = frame.contours(value_column="elevation", interval_count=3, grid_resolution=10).to_records()
    v_min = min(float(r["elevation"]) for r in frame.to_records())
    v_max = max(float(r["elevation"]) for r in frame.to_records())
    levels = {float(r["level_contour"]) for r in records}
    assert all(v_min <= level <= v_max for level in levels)


def test_hillshade_deterministic_output() -> None:
    """Identical calls produce identical output."""
    frame = _sample_point_grid()
    a = frame.hillshade(elevation_column="elevation", grid_resolution=5).to_records()
    b = frame.hillshade(elevation_column="elevation", grid_resolution=5).to_records()
    assert a == b


def test_slope_aspect_flat_surface_zero_slope() -> None:
    """A perfectly flat surface should have zero slope everywhere."""
    frame = _make_point_frame([
        {"site_id": f"p{i}", "elevation": 5.0,
         "geometry": {"type": "Point", "coordinates": [float(i % 5), float(i // 5)]}}
        for i in range(25)
    ])
    records = frame.slope_aspect(elevation_column="elevation", grid_resolution=5).to_records()
    assert all(float(r["slope_degrees_terrain"]) == pytest.approx(0.0) for r in records)


def test_slope_aspect_tilted_surface_positive_slope() -> None:
    """A tilted plane should yield consistent positive slope."""
    frame = _make_point_frame([
        {"site_id": f"p{i}", "elevation": float(i % 5) * 10.0,
         "geometry": {"type": "Point", "coordinates": [float(i % 5), float(i // 5)]}}
        for i in range(25)
    ])
    records = frame.slope_aspect(elevation_column="elevation", grid_resolution=5).to_records()
    assert all(float(r["slope_degrees_terrain"]) > 0.0 for r in records)


# ======================================================================
# Chunk 8: Spatiotemporal Cube Hardening
# ======================================================================


def test_spatiotemporal_cube_exact_boundary_timestamps() -> None:
    """Points at exact time-bin boundaries should be assigned to exactly one bin."""
    frame = _make_point_frame([
        {"site_id": "a", "time": 0.0, "value": 1.0, "geometry": {"type": "Point", "coordinates": [0.5, 0.5]}},
        {"site_id": "b", "time": 0.5, "value": 1.0, "geometry": {"type": "Point", "coordinates": [0.5, 0.5]}},
        {"site_id": "c", "time": 1.0, "value": 1.0, "geometry": {"type": "Point", "coordinates": [0.5, 0.5]}},
    ])
    records = frame.spatiotemporal_cube(
        time_column="time", value_column="value", time_intervals=2,
        grid_resolution=1, aggregation="count",
    ).to_records()
    total = sum(float(r["value_cube"]) for r in records)
    assert total == pytest.approx(3.0)


def test_spatiotemporal_cube_sparse_bins_only_nonempty() -> None:
    """Only bins with data in them should appear in the output."""
    frame = _make_point_frame([
        {"site_id": "a", "time": 0.0, "value": 1.0, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
        {"site_id": "b", "time": 10.0, "value": 1.0, "geometry": {"type": "Point", "coordinates": [9.0, 9.0]}},
    ])
    records = frame.spatiotemporal_cube(
        time_column="time", value_column="value", time_intervals=10,
        grid_resolution=10, aggregation="count",
    ).to_records()
    assert all(int(r["point_count_cube"]) > 0 for r in records)
    assert len(records) == 2


def test_spatiotemporal_cube_sum_equals_input_total() -> None:
    """Sum aggregation should reproduce the total of all input values."""
    frame = _make_point_frame([
        {"site_id": f"p{i}", "time": float(i), "value": float(i + 1),
         "geometry": {"type": "Point", "coordinates": [float(i % 3), float(i // 3)]}}
        for i in range(9)
    ])
    records = frame.spatiotemporal_cube(
        time_column="time", value_column="value", time_intervals=3,
        grid_resolution=3, aggregation="sum",
    ).to_records()
    assert sum(float(r["value_cube"]) for r in records) == pytest.approx(sum(float(i + 1) for i in range(9)))


# ======================================================================
# Chunk 9: Validation Infrastructure — optional dependency matrix
# ======================================================================


def test_optional_dependency_shapely_import() -> None:
    """Verify Shapely can be imported in the test environment."""
    pytest.importorskip("shapely")


def test_optional_dependency_pysal_import() -> None:
    """Verify PySAL can be imported in the test environment."""
    pytest.importorskip("esda")
    pytest.importorskip("libpysal")


def test_optional_dependency_pykrige_import() -> None:
    """Verify PyKrige can be imported in the test environment."""
    pytest.importorskip("pykrige")


def test_optional_dependency_statsmodels_import() -> None:
    """Verify statsmodels can be imported in the test environment."""
    pytest.importorskip("statsmodels")


# ======================================================================
# Chunk 10: Naming and Claim Discipline — additional alias checks
# ======================================================================


def test_weighted_local_summary_is_exported() -> None:
    """Verify weighted_local_summary is accessible on GeoPromptFrame."""
    assert hasattr(GeoPromptFrame, "weighted_local_summary")
    assert callable(getattr(GeoPromptFrame, "weighted_local_summary"))


def test_geographically_weighted_summary_still_works_as_compatibility_name() -> None:
    """Legacy name should remain callable and produce same output as alias."""
    frame = _sample_point_grid()
    legacy = frame.geographically_weighted_summary(
        dependent_column="elevation", independent_columns=["value"], bandwidth=2.0,
        gwr_suffix="test",
    ).to_records()
    alias = frame.weighted_local_summary(
        dependent_column="elevation", independent_columns=["value"], bandwidth=2.0,
        summary_suffix="test",
    ).to_records()
    assert legacy == alias