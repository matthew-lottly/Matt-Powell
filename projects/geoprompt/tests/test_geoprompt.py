import json
from pathlib import Path

from geoprompt.compare import _stress_feature_records, _stress_region_records
from geoprompt import GeoPromptFrame, geometry_centroid
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


def test_accessibility_analysis_namespace_and_method_equivalent() -> None:
    frame = read_features(PROJECT_ROOT / "data" / "sample_features.json")

    via_namespace = frame.analysis.accessibility(
        opportunities="demand_index",
        id_column="site_id",
        friction=1.0,
    )
    via_method = frame.accessibility_analysis(
        opportunities="demand_index",
        id_column="site_id",
        friction=1.0,
    )

    assert len(via_namespace) == len(frame)
    assert via_namespace == via_method
    assert all(float(row["accessibility_score"]) >= 0.0 for row in via_namespace)


def test_gravity_flow_analysis_returns_od_pairs() -> None:
    frame = read_features(PROJECT_ROOT / "data" / "sample_features.json")
    rows = frame.gravity_flow_analysis(
        origin_weight="capacity_index",
        destination_weight="demand_index",
        id_column="site_id",
        beta=2.0,
        offset=1e-6,
    )

    expected = len(frame) * (len(frame) - 1)
    assert len(rows) == expected
    assert all("origin" in row and "destination" in row for row in rows)
    assert all(float(row["gravity_flow"]) >= 0.0 for row in rows)


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


# ---- Nearest-neighbor parity tests (merged from test_neighbors.py) ----


def test_euclidean_and_haversine_neighbors_same_k() -> None:
    """Both methods should return same number of neighbors with k=1."""
    frame = read_features(PROJECT_ROOT / "data" / "sample_features.json", crs="EPSG:4326")
    euclidean = frame.nearest_neighbors(k=1, distance_method="euclidean")
    haversine = frame.nearest_neighbors(k=1, distance_method="haversine")
    assert len(euclidean) == len(haversine)
    assert len(euclidean) == len(frame)


def test_haversine_distances_are_reasonable() -> None:
    """Haversine distances should be in km range for geographic coords."""
    frame = read_features(PROJECT_ROOT / "data" / "sample_features.json", crs="EPSG:4326")
    neighbors = frame.nearest_neighbors(k=1, distance_method="haversine")
    for n in neighbors:
        assert n["distance"] > 0
        assert n["distance"] < 100


def test_euclidean_vs_haversine_ordering_consistency() -> None:
    """For nearby points, both methods should generally agree on nearest neighbor identity."""
    frame = read_features(PROJECT_ROOT / "data" / "sample_features.json", crs="EPSG:4326")
    euc = frame.nearest_neighbors(k=1, distance_method="euclidean")
    hav = frame.nearest_neighbors(k=1, distance_method="haversine")
    euc_pairs = {(n["origin"], n["neighbor"]) for n in euc}
    hav_pairs = {(n["origin"], n["neighbor"]) for n in hav}
    overlap = euc_pairs & hav_pairs
    assert len(overlap) >= 1