from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt

from .geometry import geometry_centroid, geometry_type, geometry_vertices
from .io import read_features, write_geojson, write_json


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_PATH = PROJECT_ROOT / "data" / "sample_features.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs"
DEFAULT_ASSET_PATH = PROJECT_ROOT / "assets" / "neighborhood-pressure-review-live.png"


def export_pressure_plot(records: list[dict[str, object]], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure, axis = plt.subplots(figsize=(10, 6))
    figure.patch.set_facecolor("#f4f2eb")
    axis.set_facecolor("#f4f2eb")

    centroids = [geometry_centroid(record["geometry"]) for record in records]
    geometry_kinds = [geometry_type(record["geometry"]) for record in records]
    vertices_by_record = [geometry_vertices(record["geometry"]) for record in records]
    xs = [centroid[0] for centroid in centroids]
    ys = [centroid[1] for centroid in centroids]
    pressures = [float(record["neighborhood_pressure"]) for record in records]
    sizes = [200 + pressure * 220 for pressure in pressures]

    for record, centroid, geometry_kind, vertices in zip(records, centroids, geometry_kinds, vertices_by_record, strict=True):
        geometry = record["geometry"]
        if geometry_kind == "LineString":
            axis.plot([coord[0] for coord in vertices], [coord[1] for coord in vertices], color="#557a95", linewidth=2.0, alpha=0.8)
        elif geometry_kind == "Polygon":
            axis.fill([coord[0] for coord in vertices], [coord[1] for coord in vertices], color="#bdd7c6", alpha=0.45, edgecolor="#557a65", linewidth=1.5)

    scatter = axis.scatter(
        xs,
        ys,
        s=sizes,
        c=pressures,
        cmap="YlOrRd",
        edgecolors="#23343b",
        linewidths=0.8,
    )

    for record, centroid in zip(records, centroids, strict=True):
        axis.annotate(
            record["name"],
            xy=centroid,
            xytext=(6, 6),
            textcoords="offset points",
            fontsize=8,
            color="#23343b",
        )

    axis.set_title("GeoPrompt Neighborhood Pressure", fontsize=16, color="#23343b")
    axis.set_xlabel("Longitude")
    axis.set_ylabel("Latitude")
    axis.grid(color="#d6cec2", linewidth=0.7, alpha=0.8)
    colorbar = figure.colorbar(scatter, ax=axis)
    colorbar.set_label("Neighborhood pressure")
    figure.tight_layout()
    figure.savefig(output_path, dpi=120, bbox_inches="tight")
    plt.close(figure)
    return output_path


def build_demo_report(input_path: Path = DEFAULT_INPUT_PATH, output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, object]:
    frame = read_features(input_path, crs="EPSG:4326")
    projected_frame = frame.to_crs("EPSG:3857")
    valley_window = frame.query_bounds(min_x=-111.97, min_y=40.68, max_x=-111.84, max_y=40.79)
    pressure = frame.neighborhood_pressure(weight_column="demand_index", scale=0.14, power=1.6)
    anchor = frame.anchor_influence(
        weight_column="priority_index",
        anchor="north-hub-point",
        scale=0.14,
        power=1.4,
    )
    corridor = frame.corridor_accessibility(
        weight_column="capacity_index",
        anchor="north-hub-point",
        scale=0.18,
        power=1.4,
    )
    enriched = frame.assign(
        neighborhood_pressure=pressure,
        anchor_influence=anchor,
        corridor_accessibility=corridor,
        geometry_type=frame.geometry_types(),
        geometry_length=frame.geometry_lengths(),
        geometry_area=frame.geometry_areas(),
    )
    enriched_records = enriched.to_records()
    top_interactions = sorted(
        enriched.interaction_table(
            origin_weight="capacity_index",
            destination_weight="demand_index",
            scale=0.16,
            power=1.5,
            preferred_bearing=135.0,
        ),
        key=lambda item: float(item["interaction"]),
        reverse=True,
    )[:5]
    top_area_similarity = sorted(
        enriched.area_similarity_table(scale=0.2, power=1.2),
        key=lambda item: float(item["area_similarity"]),
        reverse=True,
    )[:5]
    top_nearest_neighbors = enriched.nearest_neighbors(k=1)
    top_geographic_neighbors = enriched.nearest_neighbors(k=1, distance_method="haversine")
    geometry_types = sorted({str(record["geometry_type"]) for record in enriched_records})

    chart_dir = output_dir / "charts"
    chart_path = export_pressure_plot(enriched_records, chart_dir / "neighborhood-pressure-review.png")

    return {
        "package": "geoprompt",
        "equations": {
            "prompt_decay": "1 / (1 + distance / scale) ^ power",
            "prompt_influence": "weight * prompt_decay(distance, scale, power)",
            "prompt_interaction": "origin_weight * destination_weight * prompt_decay(distance, scale, power)",
            "corridor_strength": "weight * log(1 + corridor_length) * prompt_decay(distance, scale, power)",
            "area_similarity": "min(area_a, area_b) / max(area_a, area_b) * prompt_decay(distance, scale, power)",
        },
        "summary": {
            "feature_count": len(enriched),
            "crs": enriched.crs,
            "centroid": enriched.centroid(),
            "bounds": enriched.bounds().__dict__,
            "projected_bounds_3857": projected_frame.bounds().__dict__,
            "geometry_types": geometry_types,
            "valley_window_feature_count": len(valley_window),
        },
        "top_interactions": top_interactions,
        "top_area_similarity": top_area_similarity,
        "top_nearest_neighbors": top_nearest_neighbors,
        "top_geographic_neighbors": top_geographic_neighbors,
        "records": enriched_records,
        "outputs": {
            "chart": str(chart_path),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate the GeoPrompt demo report and review plot.")
    parser.add_argument("--input-path", type=Path, default=DEFAULT_INPUT_PATH, help="Input JSON feature fixture.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Output directory for report and charts.")
    parser.add_argument("--asset-path", type=Path, default=DEFAULT_ASSET_PATH, help="Committed asset path for the review plot.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_demo_report(input_path=args.input_path, output_dir=args.output_dir)
    report_path = write_json(args.output_dir / "geoprompt_demo_report.json", report)
    enriched_frame = read_features(args.input_path, crs="EPSG:4326").assign(
        neighborhood_pressure=[record["neighborhood_pressure"] for record in report["records"]],
        anchor_influence=[record["anchor_influence"] for record in report["records"]],
        corridor_accessibility=[record["corridor_accessibility"] for record in report["records"]],
        geometry_type=[record["geometry_type"] for record in report["records"]],
        geometry_length=[record["geometry_length"] for record in report["records"]],
        geometry_area=[record["geometry_area"] for record in report["records"]],
    )
    geojson_path = write_geojson(args.output_dir / "geoprompt_demo_features.geojson", enriched_frame)
    export_pressure_plot(report["records"], args.asset_path)
    print(f"Wrote GeoPrompt report to {report_path}")
    print(f"Wrote GeoPrompt GeoJSON to {geojson_path}")
    print(f"Wrote GeoPrompt asset to {args.asset_path}")


__all__ = ["build_demo_report", "export_pressure_plot", "main"]


if __name__ == "__main__":
    main()