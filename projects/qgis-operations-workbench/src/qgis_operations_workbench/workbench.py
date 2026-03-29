from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import struct
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POINTS_PATH = PROJECT_ROOT / "data" / "station_review_points.geojson"
DEFAULT_ROUTES_PATH = PROJECT_ROOT / "data" / "inspection_routes.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs"
DEFAULT_GEOPACKAGE_PATH = DEFAULT_OUTPUT_DIR / "qgis_review_bundle.gpkg"


@dataclass(frozen=True)
class StationFeature:
    feature_id: str
    name: str
    category: str
    region: str
    priority: str
    status: str
    owner: str
    coordinates: tuple[float, float]


@dataclass(frozen=True)
class InspectionRoute:
    route_id: str
    region: str
    map_scale: int
    layout_name: str
    station_ids: tuple[str, ...]


def _build_bounds(features: list[StationFeature]) -> dict[str, float]:
    longitudes = [feature.coordinates[0] for feature in features]
    latitudes = [feature.coordinates[1] for feature in features]
    return {
        "min_x": round(min(longitudes), 6),
        "min_y": round(min(latitudes), 6),
        "max_x": round(max(longitudes), 6),
        "max_y": round(max(latitudes), 6),
    }


def load_station_features(points_path: Path = DEFAULT_POINTS_PATH) -> list[StationFeature]:
    payload = json.loads(points_path.read_text(encoding="utf-8"))
    features: list[StationFeature] = []
    for entry in payload["features"]:
        properties = entry["properties"]
        coordinates = entry["geometry"]["coordinates"]
        features.append(
            StationFeature(
                feature_id=properties["featureId"],
                name=properties["name"],
                category=properties["category"],
                region=properties["region"],
                priority=properties["priority"],
                status=properties["status"],
                owner=properties["owner"],
                coordinates=(float(coordinates[0]), float(coordinates[1])),
            )
        )
    return features


def load_inspection_routes(routes_path: Path = DEFAULT_ROUTES_PATH) -> list[InspectionRoute]:
    routes: list[InspectionRoute] = []
    with routes_path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            station_ids = tuple(part.strip() for part in row["stationIds"].split("|") if part.strip())
            routes.append(
                InspectionRoute(
                    route_id=row["routeId"],
                    region=row["region"],
                    map_scale=int(row["mapScale"]),
                    layout_name=row["layoutName"],
                    station_ids=station_ids,
                )
            )
    return routes


def _build_layer_summary(features: list[StationFeature]) -> dict[str, Any]:
    category_counts = Counter(feature.category for feature in features)
    status_counts = Counter(feature.status for feature in features)
    region_counts = Counter(feature.region for feature in features)
    return {
        "station_count": len(features),
        "categories": dict(sorted(category_counts.items())),
        "statuses": dict(sorted(status_counts.items())),
        "regions": dict(sorted(region_counts.items())),
    }


def _build_map_themes(features: list[StationFeature]) -> list[dict[str, Any]]:
    category_groups = defaultdict(list)
    for feature in features:
        category_groups[feature.category].append(feature.feature_id)

    themes = [
        {
            "name": "Alert Review",
            "description": "Highlights high-priority or alert stations for the morning analyst pass.",
            "featureIds": [
                feature.feature_id for feature in features if feature.status == "alert" or feature.priority == "high"
            ],
        },
        {
            "name": "Field Readiness",
            "description": "Shows stations due for inspection in route-oriented groups.",
            "featureIds": [feature.feature_id for feature in features if feature.status != "offline"],
        },
    ]

    for category, category_feature_ids in sorted(category_groups.items()):
        themes.append(
            {
                "name": f"{category.replace('_', ' ').title()} Review",
                "description": f"Focus theme for {category.replace('_', ' ')} operations.",
                "featureIds": category_feature_ids,
            }
        )

    return themes


def _build_bookmarks(features: list[StationFeature]) -> list[dict[str, Any]]:
    grouped: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for feature in features:
        grouped[feature.region].append(feature.coordinates)

    bookmarks = []
    for region, coordinates in sorted(grouped.items()):
        longitudes = [coordinate[0] for coordinate in coordinates]
        latitudes = [coordinate[1] for coordinate in coordinates]
        bookmarks.append(
            {
                "name": f"{region} Operations",
                "center": {
                    "longitude": round(sum(longitudes) / len(longitudes), 4),
                    "latitude": round(sum(latitudes) / len(latitudes), 4),
                },
                "extentPadding": 0.35,
                "featureCount": len(coordinates),
            }
        )
    return bookmarks


def _build_layout_jobs(features: list[StationFeature], routes: list[InspectionRoute]) -> list[dict[str, Any]]:
    features_by_id = {feature.feature_id: feature for feature in features}
    layout_jobs = []
    for route in routes:
        stations = [features_by_id[station_id].name for station_id in route.station_ids if station_id in features_by_id]
        layout_jobs.append(
            {
                "layoutName": route.layout_name,
                "region": route.region,
                "mapScale": route.map_scale,
                "routeId": route.route_id,
                "stationNames": stations,
            }
        )
    return layout_jobs


def _encode_geopackage_point(longitude: float, latitude: float, srs_id: int = 4326) -> bytes:
    header = b"GP" + bytes([0, 1]) + struct.pack("<i", srs_id)
    wkb = struct.pack("<BI2d", 1, 1, longitude, latitude)
    return header + wkb


def _initialize_geopackage(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        PRAGMA application_id = 1196444487;
        PRAGMA user_version = 10300;

        CREATE TABLE gpkg_spatial_ref_sys (
            srs_name TEXT NOT NULL,
            srs_id INTEGER NOT NULL PRIMARY KEY,
            organization TEXT NOT NULL,
            organization_coordsys_id INTEGER NOT NULL,
            definition TEXT NOT NULL,
            description TEXT
        );

        CREATE TABLE gpkg_contents (
            table_name TEXT NOT NULL PRIMARY KEY,
            data_type TEXT NOT NULL,
            identifier TEXT UNIQUE,
            description TEXT DEFAULT '',
            last_change DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
            min_x DOUBLE,
            min_y DOUBLE,
            max_x DOUBLE,
            max_y DOUBLE,
            srs_id INTEGER,
            CONSTRAINT fk_gc_r_srs_id FOREIGN KEY (srs_id) REFERENCES gpkg_spatial_ref_sys(srs_id)
        );

        CREATE TABLE gpkg_geometry_columns (
            table_name TEXT NOT NULL,
            column_name TEXT NOT NULL,
            geometry_type_name TEXT NOT NULL,
            srs_id INTEGER NOT NULL,
            z TINYINT NOT NULL,
            m TINYINT NOT NULL,
            PRIMARY KEY (table_name, column_name),
            CONSTRAINT fk_gc_tn FOREIGN KEY (table_name) REFERENCES gpkg_contents(table_name),
            CONSTRAINT fk_gc_srs FOREIGN KEY (srs_id) REFERENCES gpkg_spatial_ref_sys(srs_id)
        );

        CREATE TABLE station_review_points (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            feature_id TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            region TEXT NOT NULL,
            priority TEXT NOT NULL,
            status TEXT NOT NULL,
            owner TEXT NOT NULL,
            geom BLOB NOT NULL
        );

        CREATE TABLE inspection_routes (
            route_id TEXT PRIMARY KEY,
            region TEXT NOT NULL,
            map_scale INTEGER NOT NULL,
            layout_name TEXT NOT NULL,
            station_ids TEXT NOT NULL
        );
        """
    )

    connection.executemany(
        "INSERT INTO gpkg_spatial_ref_sys (srs_name, srs_id, organization, organization_coordsys_id, definition, description) VALUES (?, ?, ?, ?, ?, ?)",
        [
            (
                "WGS 84 geodetic",
                4326,
                "EPSG",
                4326,
                "GEOGCS[\"WGS 84\",DATUM[\"World Geodetic System 1984\",SPHEROID[\"WGS 84\",6378137,298.257223563]],PRIMEM[\"Greenwich\",0],UNIT[\"degree\",0.0174532925199433]]",
                "longitude/latitude coordinates in decimal degrees on the WGS 84 spheroid",
            ),
            (
                "Undefined cartesian SRS",
                -1,
                "NONE",
                -1,
                "undefined",
                "undefined cartesian coordinate reference system",
            ),
        ],
    )


def export_geopackage(output_path: Path = DEFAULT_GEOPACKAGE_PATH, project_root: Path = PROJECT_ROOT) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()

    points_path = project_root / "data" / "station_review_points.geojson"
    routes_path = project_root / "data" / "inspection_routes.csv"
    features = load_station_features(points_path)
    routes = load_inspection_routes(routes_path)
    bounds = _build_bounds(features)
    last_change = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    with sqlite3.connect(output_path) as connection:
        _initialize_geopackage(connection)
        connection.execute(
            "INSERT INTO gpkg_contents (table_name, data_type, identifier, description, last_change, min_x, min_y, max_x, max_y, srs_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "station_review_points",
                "features",
                "station_review_points",
                "Sample monitoring points for desktop GIS review.",
                last_change,
                bounds["min_x"],
                bounds["min_y"],
                bounds["max_x"],
                bounds["max_y"],
                4326,
            ),
        )
        connection.execute(
            "INSERT INTO gpkg_geometry_columns (table_name, column_name, geometry_type_name, srs_id, z, m) VALUES (?, ?, ?, ?, ?, ?)",
            ("station_review_points", "geom", "POINT", 4326, 0, 0),
        )
        connection.execute(
            "INSERT INTO gpkg_contents (table_name, data_type, identifier, description, last_change, srs_id) VALUES (?, ?, ?, ?, ?, ?)",
            (
                "inspection_routes",
                "attributes",
                "inspection_routes",
                "Route definitions for QGIS review layouts.",
                last_change,
                -1,
            ),
        )

        connection.executemany(
            "INSERT INTO station_review_points (feature_id, name, category, region, priority, status, owner, geom) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    feature.feature_id,
                    feature.name,
                    feature.category,
                    feature.region,
                    feature.priority,
                    feature.status,
                    feature.owner,
                    sqlite3.Binary(_encode_geopackage_point(*feature.coordinates)),
                )
                for feature in features
            ],
        )
        connection.executemany(
            "INSERT INTO inspection_routes (route_id, region, map_scale, layout_name, station_ids) VALUES (?, ?, ?, ?, ?)",
            [
                (
                    route.route_id,
                    route.region,
                    route.map_scale,
                    route.layout_name,
                    "|".join(route.station_ids),
                )
                for route in routes
            ],
        )
        connection.commit()

    return output_path


def _build_review_tasks(features: list[StationFeature]) -> list[dict[str, Any]]:
    priority_rank = {"high": 0, "medium": 1, "low": 2}
    sorted_features = sorted(
        features,
        key=lambda feature: (priority_rank.get(feature.priority, 99), feature.status != "alert", feature.name),
    )
    tasks = []
    for feature in sorted_features:
        if feature.priority == "low" and feature.status == "normal":
            continue
        tasks.append(
            {
                "featureId": feature.feature_id,
                "stationName": feature.name,
                "region": feature.region,
                "category": feature.category,
                "priority": feature.priority,
                "status": feature.status,
                "recommendedAction": _recommended_action(feature),
            }
        )
    return tasks


def _recommended_action(feature: StationFeature) -> str:
    if feature.status == "alert":
        return f"Validate the latest {feature.category.replace('_', ' ')} readings and export a reviewer map for {feature.region}."
    if feature.status == "offline":
        return "Confirm device connectivity and flag the station for the next field route."
    return "Include in the next standard inspection packet and verify recent field notes."


def build_workbench_pack(project_root: Path = PROJECT_ROOT, project_name: str = "QGIS Operations Workbench") -> dict[str, Any]:
    points_path = project_root / "data" / "station_review_points.geojson"
    routes_path = project_root / "data" / "inspection_routes.csv"
    features = load_station_features(points_path)
    routes = load_inspection_routes(routes_path)
    return {
        "projectName": project_name,
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "summary": _build_layer_summary(features),
        "layers": [
            {
                "name": "station_review_points",
                "source": str(points_path.relative_to(project_root)).replace("\\", "/"),
                "geometryType": "Point",
            }
        ],
        "mapThemes": _build_map_themes(features),
        "bookmarks": _build_bookmarks(features),
        "layoutJobs": _build_layout_jobs(features, routes),
        "reviewTasks": _build_review_tasks(features),
        "notes": [
            "Designed as a public-safe QGIS-oriented operations pack.",
            "The checked-in data is sample monitoring content for repeatable portfolio review.",
            "The accompanying GeoPackage export can be loaded directly into QGIS as a starting review bundle.",
        ],
    }


def export_workbench_pack(output_dir: Path = DEFAULT_OUTPUT_DIR, project_name: str = "QGIS Operations Workbench") -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    pack = build_workbench_pack(PROJECT_ROOT, project_name=project_name)
    output_path = output_dir / "qgis_workbench_pack.json"
    output_path.write_text(json.dumps(pack, indent=2), encoding="utf-8")
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a sample QGIS operations workbench pack.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Directory for generated JSON output.")
    parser.add_argument("--project-name", default="QGIS Operations Workbench", help="Display name embedded in the output pack.")
    parser.add_argument(
        "--export-geopackage",
        action="store_true",
        help="Also create a GeoPackage with station points and inspection routes for QGIS review.",
    )
    parser.add_argument(
        "--geopackage-path",
        type=Path,
        default=DEFAULT_GEOPACKAGE_PATH,
        help="Output path for the generated GeoPackage.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_path = export_workbench_pack(args.output_dir, project_name=args.project_name)
    print(f"Wrote workbench pack to {output_path}")
    if args.export_geopackage:
        geopackage_path = export_geopackage(args.geopackage_path)
        print(f"Wrote GeoPackage bundle to {geopackage_path}")


if __name__ == "__main__":
    main()
