import json
import os
from pathlib import Path

import pytest

from geoprompt.compare import _stress_feature_records, _stress_region_records
from geoprompt import GeoPromptFrame, geometry_centroid
from geoprompt.demo import build_demo_report
from geoprompt.equations import area_similarity, corridor_strength, directional_alignment, euclidean_distance, haversine_distance, prompt_decay, prompt_interaction
from geoprompt.io import (
    frame_to_geojson,
    get_workload_preset,
    iter_csv_points,
    iter_data,
    iter_data_with_preset,
    read_csv_points,
    read_data,
    read_data_with_preset,
    read_features,
    read_geojson,
    read_points,
    read_table,
    write_data,
    write_geojson,
)


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


def test_read_data_supports_limit_rows_and_sampling() -> None:
    frame = read_data(
        PROJECT_ROOT / "data" / "sample_points.json",
        limit_rows=3,
        sample_step=2,
    )
    assert len(frame) == 3


def test_read_table_csv_points_and_write_data_csv(tmp_path: Path) -> None:
    csv_path = tmp_path / "points.csv"
    csv_path.write_text(
        "site_id,x,y,demand\n"
        "a,-111.95,40.70,10\n"
        "b,-111.96,40.71,20\n"
        "c,-111.97,40.72,30\n",
        encoding="utf-8",
    )

    frame = read_table(
        csv_path,
        x_column="x",
        y_column="y",
        use_columns=["site_id", "demand", "x", "y"],
        limit_rows=2,
    )
    assert len(frame) == 2
    assert frame.geometry_types() == ["Point", "Point"]

    output_csv = tmp_path / "points_out.csv"
    written = write_data(output_csv, frame)
    assert written.exists()
    assert "geometry" in written.read_text(encoding="utf-8")


def test_read_data_csv_requires_geometry_hints(tmp_path: Path) -> None:
    csv_path = tmp_path / "bad.csv"
    csv_path.write_text("site_id,demand\na,10\n", encoding="utf-8")

    try:
        read_data(csv_path)
    except ValueError as exc:
        assert "x_column/y_column or geometry_column" in str(exc)
    else:
        raise AssertionError("read_data should require geometry hints for CSV")


def test_iter_data_csv_chunks(tmp_path: Path) -> None:
    csv_path = tmp_path / "points_big.csv"
    csv_path.write_text(
        "site_id,x,y\n"
        "a,-111.95,40.70\n"
        "b,-111.96,40.71\n"
        "c,-111.97,40.72\n"
        "d,-111.98,40.73\n"
        "e,-111.99,40.74\n",
        encoding="utf-8",
    )

    chunks = list(
        iter_data(
            csv_path,
            x_column="x",
            y_column="y",
            chunk_size=2,
        )
    )

    assert [len(chunk) for chunk in chunks] == [2, 2, 1]
    assert chunks[0].geometry_types() == ["Point", "Point"]


def test_iter_data_json_chunks() -> None:
    chunks = list(
        iter_data(
            PROJECT_ROOT / "data" / "sample_points.json",
            chunk_size=2,
            limit_rows=5,
        )
    )
    assert [len(chunk) for chunk in chunks] == [2, 2, 1]


def test_iter_data_progress_callback(tmp_path: Path) -> None:
    csv_path = tmp_path / "points_progress.csv"
    csv_path.write_text(
        "site_id,x,y\n"
        "a,-111.95,40.70\n"
        "b,-111.96,40.71\n"
        "c,-111.97,40.72\n",
        encoding="utf-8",
    )

    events: list[dict[str, object]] = []
    chunks = list(
        iter_data(
            csv_path,
            x_column="x",
            y_column="y",
            chunk_size=2,
            progress_callback=events.append,
        )
    )

    assert [len(chunk) for chunk in chunks] == [2, 1]
    assert len(events) == 2
    assert events[0]["event"] == "chunk"
    assert events[0]["chunk_rows"] == 2
    assert events[1]["rows_emitted"] == 3


def test_iter_data_progress_callback_event_schema(tmp_path: Path) -> None:
    csv_path = tmp_path / "points_progress_schema.csv"
    csv_path.write_text(
        "site_id,x,y\n"
        "a,-111.95,40.70\n"
        "b,-111.96,40.71\n",
        encoding="utf-8",
    )

    events: list[dict[str, object]] = []
    list(
        iter_data(
            csv_path,
            x_column="x",
            y_column="y",
            chunk_size=1,
            progress_callback=events.append,
        )
    )

    assert events
    expected_keys = {"event", "path", "chunk_index", "chunk_rows", "rows_emitted"}
    assert set(events[0].keys()) == expected_keys


def test_workload_preset_wrappers_and_validation(tmp_path: Path) -> None:
    csv_path = tmp_path / "points_preset.csv"
    csv_path.write_text(
        "site_id,x,y\n"
        "a,-111.95,40.70\n"
        "b,-111.96,40.71\n"
        "c,-111.97,40.72\n"
        "d,-111.98,40.73\n",
        encoding="utf-8",
    )

    preset = get_workload_preset("large")
    assert preset["chunk_size"] >= 50000

    frame = read_data_with_preset(
        csv_path,
        preset="small",
        x_column="x",
        y_column="y",
        limit_rows=2,
    )
    assert len(frame) == 2

    frame_csv = read_csv_points(csv_path, x_column="x", y_column="y", limit_rows=3)
    assert len(frame_csv) == 3

    chunks = list(
        iter_data_with_preset(
            csv_path,
            preset="small",
            x_column="x",
            y_column="y",
            chunk_size=2,
        )
    )
    assert [len(chunk) for chunk in chunks] == [2, 2]

    chunks_csv = list(iter_csv_points(csv_path, x_column="x", y_column="y", chunk_size=3))
    assert [len(chunk) for chunk in chunks_csv] == [3, 1]

    with pytest.raises(ValueError, match="unknown workload preset"):
        get_workload_preset("not-a-real-preset")


def test_frame_batch_equation_wrappers() -> None:
    frame = GeoPromptFrame.from_records(
        [
            {
                "site_id": "a",
                "supply_1": 100.0,
                "supply_2": 40.0,
                "cost_1": 0.5,
                "cost_2": 1.2,
                "origin_mass": 10.0,
                "destination_mass": 5.0,
                "generalized_cost": 1.5,
                "pressure": 0.8,
                "redundancy": 0.4,
                "geometry": {"type": "Point", "coordinates": (-111.9, 40.7)},
            },
            {
                "site_id": "b",
                "supply_1": 80.0,
                "supply_2": 25.0,
                "cost_1": 0.4,
                "cost_2": 0.9,
                "origin_mass": 8.0,
                "destination_mass": 4.0,
                "generalized_cost": 2.0,
                "pressure": 0.6,
                "redundancy": 0.7,
                "geometry": {"type": "Point", "coordinates": (-112.0, 40.8)},
            },
        ],
        crs="EPSG:4326",
    )

    accessibility = frame.batch_accessibility_scores(
        supply_columns=["supply_1", "supply_2"],
        travel_cost_columns=["cost_1", "cost_2"],
        decay_method="exponential",
        rate=0.7,
    )
    gravity = frame.gravity_interaction_series("origin_mass", "destination_mass", "generalized_cost", gamma=1.2)
    service_probability = frame.service_probability_series(
        predictor_columns=["pressure", "redundancy"],
        coefficients={"pressure": 1.1, "redundancy": 0.6},
        intercept=-0.4,
    )

    assert len(accessibility) == len(frame)
    assert len(gravity) == len(frame)
    assert len(service_probability) == len(frame)
    assert all(value > 0 for value in accessibility)
    assert all(0.0 < value < 1.0 for value in service_probability)


def test_frame_batch_tables_and_spatial_index() -> None:
    frame = read_features(PROJECT_ROOT / "data" / "sample_features.json", crs="EPSG:4326")

    indexed = frame.build_spatial_index()
    direct = frame.query_bounds(-111.97, 40.68, -111.84, 40.79, mode="intersects")
    indexed_result = frame.query_bounds_indexed(-111.97, 40.68, -111.84, 40.79, mode="intersects", spatial_index=indexed)

    metric_frame = GeoPromptFrame.from_records(
        [
            {
                "site_id": "a",
                "supply_1": 100.0,
                "supply_2": 40.0,
                "cost_1": 0.5,
                "cost_2": 1.2,
                "origin_mass": 10.0,
                "destination_mass": 5.0,
                "generalized_cost": 1.5,
                "pressure": 0.8,
                "redundancy": 0.4,
                "geometry": {"type": "Point", "coordinates": (-111.9, 40.7)},
            },
            {
                "site_id": "b",
                "supply_1": 80.0,
                "supply_2": 25.0,
                "cost_1": 0.4,
                "cost_2": 0.9,
                "origin_mass": 8.0,
                "destination_mass": 4.0,
                "generalized_cost": 2.0,
                "pressure": 0.6,
                "redundancy": 0.7,
                "geometry": {"type": "Point", "coordinates": (-112.0, 40.8)},
            },
        ],
        crs="EPSG:4326",
    )

    accessibility_table = metric_frame.batch_accessibility_table(
        supply_columns=["supply_1", "supply_2"],
        travel_cost_columns=["cost_1", "cost_2"],
        decay_method="exponential",
        rate=0.7,
    )
    gravity_table = metric_frame.gravity_interaction_table("origin_mass", "destination_mass", "generalized_cost")
    service_table = metric_frame.service_probability_table(
        predictor_columns=["pressure", "redundancy"],
        coefficients={"pressure": 1.1, "redundancy": 0.6},
        intercept=-0.4,
    )

    assert direct.to_records() == indexed_result.to_records()
    assert indexed.query(-111.97, 40.68, -111.84, 40.79)
    assert accessibility_table.head(1)[0]["site_id"] == "a"
    assert "gravity_interaction" in gravity_table.columns
    assert "service_probability" in service_table.columns


def test_indexed_join_paths_match_existing_results() -> None:
    regions = read_features(PROJECT_ROOT / "data" / "benchmark_regions.json", crs="EPSG:4326")
    assets = read_features(PROJECT_ROOT / "data" / "benchmark_features.json", crs="EPSG:4326")

    direct_proximity = regions.proximity_join(assets, max_distance=0.08, use_spatial_index=False)
    direct_nearest = regions.nearest_join(assets, k=2, use_spatial_index=False)
    direct_spatial = regions.spatial_join(assets, predicate="intersects", use_spatial_index=False)

    indexed_proximity = regions.proximity_join(assets, max_distance=0.08, use_spatial_index=True)
    indexed_nearest = regions.nearest_join(assets, k=2, use_spatial_index=True)
    indexed_spatial = regions.spatial_join(assets, predicate="intersects", use_spatial_index=True)

    assert direct_proximity.to_records() == indexed_proximity.to_records()
    assert direct_nearest.to_records() == indexed_nearest.to_records()
    assert direct_spatial.to_records() == indexed_spatial.to_records()


@pytest.mark.skipif(os.environ.get("GEOPROMPT_RUN_GEO_IO") != "1", reason="requires optional geospatial IO stack")
def test_geospatial_integration_parquet_round_trip(tmp_path: Path) -> None:
    gpd = pytest.importorskip("geopandas")

    gdf = gpd.GeoDataFrame(
        {
            "site_id": ["a", "b"],
            "demand": [10.0, 20.0],
        },
        geometry=gpd.points_from_xy([-111.95, -111.96], [40.70, 40.71]),
        crs="EPSG:4326",
    )

    parquet_path = tmp_path / "points.parquet"
    gdf.to_parquet(parquet_path)

    frame = read_data(parquet_path, use_columns=["site_id", "demand", "geometry"])
    assert len(frame) == 2
    assert frame.geometry_types() == ["Point", "Point"]

    out_path = tmp_path / "points_out.parquet"
    write_data(out_path, frame)
    assert out_path.exists()


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


# ---------------------[ Edge Case Tests ]---------------------

def test_empty_frame_operations() -> None:
    """Test frame operations on empty (zero-row) frames."""
    empty = GeoPromptFrame(rows=[], geometry_column="geometry")
    
    assert len(empty) == 0
    assert empty.columns == []
    assert empty.geometry_types() == []
    assert empty.geometry_lengths() == []
    assert empty.geometry_areas() == []
    assert empty.distance_matrix() == []
    

def test_single_row_frame_operations() -> None:
    """Test frame operations on single-row frames."""
    single = GeoPromptFrame(
        rows=[{
            "site_id": "point-a",
            "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}
        }],
        geometry_column="geometry"
    )
    
    assert len(single) == 1
    assert single.centroid() == (0.0, 0.0)
    bounds = single.bounds()
    assert bounds.min_x == 0.0 and bounds.min_y == 0.0 and bounds.max_x == 0.0 and bounds.max_y == 0.0
    assert single.distance_matrix() == [[0.0]]
    assert single.nearest_neighbors() == []  # No neighbors to itself


def test_none_geometry_raises_error() -> None:
    """Test that None geometries are rejected during frame construction."""
    try:
        GeoPromptFrame(
            rows=[
                {"site_id": "a", "geometry": None},  # None not allowed
            ],
            geometry_column="geometry"
        )
        assert False, "Should raise TypeError"
    except TypeError as e:
        assert "geometry must be" in str(e)
    

def test_degenerate_geometries() -> None:
    """Test frame with degenerate geometries (point as line, etc)."""
    degenerate = GeoPromptFrame(
        rows=[
            {"site_id": "degen-line", "geometry": {"type": "LineString", "coordinates": [[0.0, 0.0], [0.0, 0.0]]}},
            {"site_id": "degen-poly", "geometry": {"type": "Polygon", "coordinates": [[[0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0]]]}},
        ],
        geometry_column="geometry"
    )
    
    assert len(degenerate) == 2
    lengths = degenerate.geometry_lengths()
    assert all(length == 0.0 for length in lengths)
    

def test_join_with_no_matches() -> None:
    """Test spatial joins where no rows match (empty result)."""
    frame1 = GeoPromptFrame(
        rows=[{"site_id": "a", "x": 0, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}}],
        geometry_column="geometry"
    )
    frame2 = GeoPromptFrame(
        rows=[{"site_id": "b", "y": 1, "geometry": {"type": "Point", "coordinates": [100.0, 100.0]}}],
        geometry_column="geometry"
    )
    
    # Nearest join with very small max_distance should have no matches
    result = frame1.nearest_join(frame2, max_distance=1.0, how="inner")
    assert len(result) == 0
    
    # With how="left", should keep left rows with null right columns
    result_left = frame1.nearest_join(frame2, max_distance=1.0, how="left")
    assert len(result_left) == 1
    assert result_left._rows[0]["site_id"] == "a"
    assert result_left._rows[0]["y"] is None


def test_with_column_mismatched_length() -> None:
    """Test with_column validation for length mismatch."""
    frame = GeoPromptFrame(
        rows=[{"site_id": "a", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}}],
        geometry_column="geometry"
    )
    
    try:
        frame.with_column("new_col", [1, 2, 3])  # Length mismatch
        assert False, "Should raise ValueError"
    except ValueError as e:
        assert "column length must match" in str(e)


def test_assign_with_scalar_and_callable() -> None:
    """Test assign with scalar and callable column definitions."""
    frame = GeoPromptFrame(
        rows=[
            {"site_id": "a", "value": 10, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
            {"site_id": "b", "value": 20, "geometry": {"type": "Point", "coordinates": [1.0, 1.0]}},
        ],
        geometry_column="geometry"
    )
    
    # Mix of scalar broadcast and callable
    result = frame.assign(
        status="active",
        double_value=lambda f: [row["value"] * 2 for row in f._rows],
    )
    
    assert len(result) == 2
    assert result._rows[0]["status"] == "active"
    assert result._rows[0]["double_value"] == 20


def test_neighborhood_pressure_no_self() -> None:
    """Test neighborhood_pressure excludes self by default."""
    frame = GeoPromptFrame(
        rows=[
            {"site_id": "a", "weight": 1.0, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
            {"site_id": "b", "weight": 1.0, "geometry": {"type": "Point", "coordinates": [1.0, 0.0]}},
        ],
        geometry_column="geometry"
    )
    
    pressure = frame.neighborhood_pressure(weight_column="weight", scale=1.0, power=2.0)
    
    assert len(pressure) == 2
    # Each point should have pressure only from the other point
    assert pressure[0] > 0  # Point a influenced by point b
    assert pressure[1] > 0  # Point b influenced by point a


def test_distance_matrix_large_frame_guard() -> None:
    """Test that distance_matrix raises MemoryError for huge frames."""
    # Create a frame that would exceed the 100K limit
    large_rows = [
        {"id": i, "geometry": {"type": "Point", "coordinates": [float(i), float(i)]}}
        for i in range(100001)
    ]
    large_frame = GeoPromptFrame(rows=large_rows, geometry_column="geometry")
    
    try:
        large_frame.distance_matrix()
        assert False, "Should raise MemoryError"
    except MemoryError as e:
        assert "Distance matrix requires" in str(e)


def test_normalize_crs_parameter() -> None:
    """Test frame CRS parameter preservation across operations."""
    frame = GeoPromptFrame(
        rows=[{"site_id": "a", "geometry": {"type": "Point", "coordinates": [-111.92, 40.78]}}],
        geometry_column="geometry",
        crs="EPSG:4326"
    )
    
    assert frame.crs == "EPSG:4326"
    
    new_frame = frame.with_column("test", [1])
    assert new_frame.crs == "EPSG:4326"


# ---------------------[ End Edge Case Tests ]---------------------

# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------


def test_nearest_join_empty_right_frame_left_mode() -> None:
    origins = GeoPromptFrame.from_records(
        [
            {"site_id": "a", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
            {"site_id": "b", "geometry": {"type": "Point", "coordinates": [1.0, 0.0]}},
        ],
        crs="EPSG:4326",
    )
    empty = GeoPromptFrame.from_records([], crs="EPSG:4326")

    result = origins.nearest_join(empty, k=1, how="left")
    assert len(result) == 2
    for row in result.to_records():
        assert row["distance_right"] is None
        assert row["nearest_rank_right"] is None


def test_summarize_assignments_no_assignments_left_mode() -> None:
    origins = GeoPromptFrame.from_records(
        [
            {"site_id": "origin-a", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
            {"site_id": "origin-b", "geometry": {"type": "Point", "coordinates": [50.0, 0.0]}},
        ],
        crs="EPSG:4326",
    )
    targets = GeoPromptFrame.from_records(
        [
            {"target_id": "t1", "geometry": {"type": "Point", "coordinates": [0.5, 0.0]}},
        ],
        crs="EPSG:4326",
    )

    # max_distance=1 means origin-b gets no assignments; how="left" keeps it
    summary = origins.summarize_assignments(
        targets,
        origin_id_column="site_id",
        target_id_column="target_id",
        max_distance=1.0,
        how="left",
    )
    records = sorted(summary.to_records(), key=lambda r: r["site_id"])

    assert records[0]["site_id"] == "origin-a"
    assert records[0]["count_assigned"] == 1
    assert records[1]["site_id"] == "origin-b"
    assert records[1]["count_assigned"] == 0
    assert records[1]["target_ids_assigned"] == []
    assert records[1]["distance_min_assigned"] is None


def test_spatial_join_within_predicate() -> None:
    container = GeoPromptFrame.from_records(
        [
            {
                "zone_id": "z1",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0.0, 0.0], [2.0, 0.0], [2.0, 2.0], [0.0, 2.0]]],
                },
            }
        ],
        crs="EPSG:4326",
    )
    points = GeoPromptFrame.from_records(
        [
            {"pt_id": "inside", "geometry": {"type": "Point", "coordinates": [1.0, 1.0]}},
            {"pt_id": "outside", "geometry": {"type": "Point", "coordinates": [5.0, 5.0]}},
        ],
        crs="EPSG:4326",
    )

    result = points.spatial_join(container, predicate="within", how="inner")
    ids = [row["pt_id"] for row in result.to_records()]

    assert "inside" in ids
    assert "outside" not in ids


def test_proximity_join_empty_matches_left_mode() -> None:
    origins = GeoPromptFrame.from_records(
        [
            {"site_id": "a", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
        ],
        crs="EPSG:4326",
    )
    far_targets = GeoPromptFrame.from_records(
        [
            {"target_id": "far", "geometry": {"type": "Point", "coordinates": [100.0, 0.0]}},
        ],
        crs="EPSG:4326",
    )

    result = origins.proximity_join(far_targets, max_distance=1.0, how="left")
    assert len(result) == 1
    assert result.head(1)[0]["distance_right"] is None
    assert result.head(1)[0]["target_id"] is None


def test_numeric_id_column_round_trip() -> None:
    frame = GeoPromptFrame.from_records(
        [
            {"site_id": 1, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
            {"site_id": 2, "geometry": {"type": "Point", "coordinates": [1.0, 0.0]}},
            {"site_id": 3, "geometry": {"type": "Point", "coordinates": [2.0, 0.0]}},
        ]
    )

    neighbors = frame.nearest_neighbors(id_column="site_id", k=1)
    assert all(isinstance(row["origin"], int) for row in neighbors)
    assert all(isinstance(row["neighbor"], int) for row in neighbors)
    assert len(neighbors) == 3


def test_query_radius_from_coordinate_tuple() -> None:
    frame = GeoPromptFrame.from_records(
        [
            {"site_id": "a", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
            {"site_id": "b", "geometry": {"type": "Point", "coordinates": [1.0, 0.0]}},
            {"site_id": "c", "geometry": {"type": "Point", "coordinates": [5.0, 0.0]}},
        ]
    )

    result = frame.query_radius(anchor=(0.0, 0.0), max_distance=2.0)
    ids = [row["site_id"] for row in result.to_records()]

    assert "a" in ids
    assert "b" in ids
    assert "c" not in ids
    # anchor_id column should NOT be present when anchor is a coordinate
    assert "anchor_id" not in result.to_records()[0]


def test_coverage_summary_empty_targets() -> None:
    zone = GeoPromptFrame.from_records(
        [
            {
                "zone_id": "z1",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]],
                },
            }
        ]
    )
    empty = GeoPromptFrame.from_records([])

    summary = zone.coverage_summary(empty, target_id_column="site_id")
    assert len(summary) == 1
    assert summary.head(1)[0]["count_covered"] == 0
    assert summary.head(1)[0]["site_ids_covered"] == []


def test_assign_with_callable() -> None:
    frame = GeoPromptFrame.from_records(
        [
            {"site_id": "a", "demand": 2.0, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
            {"site_id": "b", "demand": 4.0, "geometry": {"type": "Point", "coordinates": [1.0, 0.0]}},
        ]
    )

    result = frame.assign(
        demand_doubled=lambda f: [row["demand"] * 2 for row in f],
        label="fixed",
    )
    records = result.to_records()

    assert records[0]["demand_doubled"] == 4.0
    assert records[1]["demand_doubled"] == 8.0
    assert all(row["label"] == "fixed" for row in records)