import json
from pathlib import Path

from geoprompt.compare import _stress_feature_records, _stress_region_records
from geoprompt import GeoPromptFrame, geometry_centroid, geometry_convex_hull, geometry_envelope, gravity_model, accessibility_index
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
    assert records[0]["total_weight_autocorr"] == 6.0


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
    report = build_demo_report(
        input_path=PROJECT_ROOT / "data" / "sample_features.json",
        output_dir=tmp_path,
    )

    assert report["package"] == "geoprompt"
    assert len(report["records"]) == 6
    assert len(report["top_interactions"]) == 5
    assert len(report["top_area_similarity"]) == 5
    assert len(report["top_nearest_neighbors"]) == 6
    assert len(report["top_geographic_neighbors"]) == 6
    assert report["summary"]["geometry_types"] == ["LineString", "Point", "Polygon"]
    assert report["summary"]["crs"] == "EPSG:4326"
    assert report["summary"]["projected_bounds_3857"]["min_x"] < -12000000
    assert report["summary"]["valley_window_feature_count"] == 3
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
    envelope = geometry_envelope(polygon)
    assert envelope["type"] == "Polygon"
    coords = list(envelope["coordinates"])
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
    hull = geometry_convex_hull(polygon)
    assert hull["type"] == "Polygon"
    hull_coords = list(hull["coordinates"])
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


def test_comparison_report_benchmarks_new_methods() -> None:
    import geoprompt.compare as compare

    original_benchmark = compare._benchmark
    compare._benchmark = lambda operation, func, repeats=20: ({"operation": operation, "repeats": 1}, func())
    try:
        report = compare.build_comparison_report()
    finally:
        compare._benchmark = original_benchmark

    benchmark_ops = {
        benchmark["operation"]
        for dataset in report["datasets"]
        for benchmark in dataset["benchmarks"]
    }
    assert all("performance" in dataset for dataset in report["datasets"])
    assert all("query_bounds_pruning_ratio" in dataset["performance"] for dataset in report["datasets"])
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
    assert "benchmark.geoprompt.line_split" in benchmark_ops
    assert "benchmark.geoprompt.polygon_split" in benchmark_ops
    assert "benchmark.geoprompt.trajectory_match" in benchmark_ops
    assert "benchmark.geoprompt.summarize_trajectory_segments" in benchmark_ops
    assert "benchmark.geoprompt.score_trajectory_segments" in benchmark_ops
    assert "benchmark.geoprompt.shortest_path" in benchmark_ops
    assert "benchmark.geoprompt.service_area" in benchmark_ops
    assert "benchmark.geoprompt.location_allocate" in benchmark_ops