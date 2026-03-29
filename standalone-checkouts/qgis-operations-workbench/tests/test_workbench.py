from pathlib import Path
import sqlite3

from qgis_operations_workbench.workbench import build_workbench_pack, export_geopackage, export_workbench_pack, load_inspection_routes, load_station_features


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_load_station_features() -> None:
    features = load_station_features(PROJECT_ROOT / "data" / "station_review_points.geojson")

    assert len(features) == 4
    assert features[0].feature_id == "station-west-air-001"
    assert {feature.region for feature in features} == {"West", "Central", "East"}


def test_load_inspection_routes() -> None:
    routes = load_inspection_routes(PROJECT_ROOT / "data" / "inspection_routes.csv")

    assert len(routes) == 3
    assert routes[0].layout_name == "West Daily Review"
    assert routes[1].map_scale == 35000


def test_build_workbench_pack() -> None:
    pack = build_workbench_pack(PROJECT_ROOT)

    assert pack["projectName"] == "QGIS Operations Workbench"
    assert pack["summary"]["station_count"] == 4
    assert pack["summary"]["categories"]["air_quality"] == 1
    assert pack["summary"]["statuses"]["alert"] == 2
    assert pack["bookmarks"][0]["name"] == "Central Operations"
    assert pack["layoutJobs"][0]["layoutName"] == "West Daily Review"
    assert pack["reviewTasks"][0]["stationName"] == "Cascade Smoke Watch"
    assert pack["notes"][0].startswith("Designed as a public-safe")


def test_export_workbench_pack(tmp_path: Path) -> None:
    output_path = export_workbench_pack(tmp_path, project_name="Desktop GIS Review Pack")

    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert "Desktop GIS Review Pack" in content
    assert "qgis_workbench_pack.json" in str(output_path)


def test_export_geopackage(tmp_path: Path) -> None:
    output_path = export_geopackage(tmp_path / "review_bundle.gpkg", project_root=PROJECT_ROOT)

    assert output_path.exists()

    with sqlite3.connect(output_path) as connection:
        contents = dict(connection.execute("SELECT table_name, data_type FROM gpkg_contents").fetchall())
        station_count = connection.execute("SELECT COUNT(*) FROM station_review_points").fetchone()[0]
        route_count = connection.execute("SELECT COUNT(*) FROM inspection_routes").fetchone()[0]

    assert contents["station_review_points"] == "features"
    assert contents["inspection_routes"] == "attributes"
    assert station_count == 4
    assert route_count == 3
