import json
from pathlib import Path

from geoprompt.compare import _stress_feature_records, _stress_region_records
from geoprompt import GeoPromptFrame, geometry_centroid, geometry_convex_hull, geometry_envelope, gravity_model, accessibility_index
from geoprompt.demo import build_demo_report
from geoprompt.equations import area_similarity, corridor_strength, directional_alignment, euclidean_distance, haversine_distance, prompt_decay, prompt_interaction
from geoprompt.io import frame_to_geojson, read_features, read_geojson, read_points, write_geojson


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


def test_gravity_model_equation() -> None:
    g = gravity_model(10.0, 20.0, distance_value=5.0, friction=2.0)
    assert round(g, 2) == 8.0

    g_zero = gravity_model(10.0, 20.0, distance_value=0.0)
    assert g_zero == float("inf")


def test_accessibility_index_equation() -> None:
    score = accessibility_index(
        weights=[10.0, 20.0],
        distances=[1.0, 2.0],
        friction=2.0,
    )
    assert round(score, 2) == 15.0


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