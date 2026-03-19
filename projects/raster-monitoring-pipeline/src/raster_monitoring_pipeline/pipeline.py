from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BASELINE_PATH = PROJECT_ROOT / "data" / "baseline_grid.json"
DEFAULT_LATEST_PATH = PROJECT_ROOT / "data" / "latest_grid.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs"
HOTSPOT_DELTA_THRESHOLD = 4


def load_grid(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _iter_cells(grid: list[list[int]]) -> list[tuple[int, int, int]]:
    cells: list[tuple[int, int, int]] = []
    for row_index, row in enumerate(grid):
        for column_index, value in enumerate(row):
            cells.append((row_index, column_index, value))
    return cells


def build_change_report(
    baseline_path: Path = DEFAULT_BASELINE_PATH,
    latest_path: Path = DEFAULT_LATEST_PATH,
    pipeline_name: str = "Raster Monitoring Pipeline",
) -> dict[str, Any]:
    baseline = load_grid(baseline_path)
    latest = load_grid(latest_path)

    baseline_cells = _iter_cells(baseline["grid"])
    latest_cells = _iter_cells(latest["grid"])
    changes = []
    hotspot_count = 0

    for (row_index, column_index, baseline_value), (_, _, latest_value) in zip(baseline_cells, latest_cells, strict=True):
        delta = latest_value - baseline_value
        if delta >= HOTSPOT_DELTA_THRESHOLD:
            hotspot_count += 1
        changes.append(
            {
                "row": row_index,
                "column": column_index,
                "baseline": baseline_value,
                "latest": latest_value,
                "delta": delta,
            }
        )

    changes.sort(key=lambda change: change["delta"], reverse=True)
    top_changes = changes[:5]
    max_latest = max(cell[2] for cell in latest_cells)
    avg_delta = round(sum(change["delta"] for change in changes) / len(changes), 2)

    return {
        "pipelineName": pipeline_name,
        "baselineRaster": baseline["rasterName"],
        "latestRaster": latest["rasterName"],
        "summary": {
            "cellCount": len(changes),
            "averageDelta": avg_delta,
            "hotspotCount": hotspot_count,
            "maxLatestValue": max_latest,
        },
        "topChanges": top_changes,
        "tileManifest": [
            {
                "tileId": "tile-northwest",
                "rows": [0, 1],
                "columns": [0, 1],
            },
            {
                "tileId": "tile-northeast",
                "rows": [0, 1],
                "columns": [2, 3],
            },
            {
                "tileId": "tile-southwest",
                "rows": [2, 3],
                "columns": [0, 1],
            },
            {
                "tileId": "tile-southeast",
                "rows": [2, 3],
                "columns": [2, 3],
            },
        ],
        "notes": [
            "Designed as a public-safe raster change-detection pipeline.",
            "The sample grids can later be replaced by GeoTIFF-backed workflows through rasterio or GDAL.",
            "The output report is intended as a handoff artifact for downstream visualization or alerting layers.",
        ],
    }


def export_change_report(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    pipeline_name: str = "Raster Monitoring Pipeline",
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    report = build_change_report(pipeline_name=pipeline_name)
    output_path = output_dir / "raster_change_report.json"
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a sample raster monitoring change report.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Directory for generated JSON output.")
    parser.add_argument("--pipeline-name", default="Raster Monitoring Pipeline", help="Display name embedded in the output report.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_path = export_change_report(args.output_dir, pipeline_name=args.pipeline_name)
    print(f"Wrote raster change report to {output_path}")


if __name__ == "__main__":
    main()
