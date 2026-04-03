from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt


PROJECT_ROOT = Path(__file__).resolve().parents[1]
POINTS_PATH = PROJECT_ROOT / "data" / "station_review_points.geojson"
ROUTES_PATH = PROJECT_ROOT / "data" / "inspection_routes.csv"
OUTPUT_PATH = PROJECT_ROOT / "assets" / "qgis-review-preview.png"

STATUS_COLORS = {
    "alert": "#c84c2f",
    "normal": "#4f7f45",
    "offline": "#56636e",
}


def _load_points() -> list[dict[str, object]]:
    payload = json.loads(POINTS_PATH.read_text(encoding="utf-8"))
    return payload["features"]


def _load_routes() -> list[dict[str, str]]:
    rows = ROUTES_PATH.read_text(encoding="utf-8").strip().splitlines()
    headers = rows[0].split(",")
    return [dict(zip(headers, row.split(","), strict=True)) for row in rows[1:]]


def main() -> None:
    points = _load_points()
    routes = _load_routes()
    figure, axis = plt.subplots(figsize=(11, 7))
    axis.set_facecolor("#f5f1e8")

    for feature in points:
        properties = feature["properties"]
        longitude, latitude = feature["geometry"]["coordinates"]
        color = STATUS_COLORS.get(properties["status"], "#56636e")
        axis.scatter(longitude, latitude, s=140, color=color, edgecolors="#162028", linewidths=1.2, zorder=3)
        axis.text(longitude + 0.35, latitude + 0.15, properties["name"], fontsize=9, color="#162028")

    feature_lookup = {feature["properties"]["featureId"]: feature for feature in points}
    for route in routes:
        station_ids = route["stationIds"].split("|")
        coordinates = [feature_lookup[station_id]["geometry"]["coordinates"] for station_id in station_ids if station_id in feature_lookup]
        if len(coordinates) < 2:
            continue
        x_values = [coordinate[0] for coordinate in coordinates]
        y_values = [coordinate[1] for coordinate in coordinates]
        axis.plot(x_values, y_values, linestyle="--", linewidth=2, color="#2b6f95", alpha=0.9, zorder=2)

    axis.set_title("QGIS Review Bundle Preview", fontsize=18, color="#162028", pad=18)
    axis.text(
        0.01,
        0.02,
        "Desktop review preview generated from the packaged GeoJSON points and inspection routes.",
        transform=axis.transAxes,
        fontsize=10,
        color="#33424d",
    )
    axis.set_xlabel("Longitude")
    axis.set_ylabel("Latitude")
    axis.grid(color="#d5c8b6", linestyle=":", linewidth=0.8)
    figure.tight_layout()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(OUTPUT_PATH, dpi=180)
    plt.close(figure)


if __name__ == "__main__":
    main()