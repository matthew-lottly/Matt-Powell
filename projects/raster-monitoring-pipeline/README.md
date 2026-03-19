# Raster Monitoring Pipeline

Open-stack GIS analysis project for comparing raster snapshots, flagging hotspots, and packaging change-detection output for downstream review.

![Raster pipeline preview](assets/raster-preview.svg)

## Snapshot

- Lane: Raster analysis and monitoring
- Domain: Change detection and hotspot review
- Stack: Python, JSON grid fixtures, raster workflow design
- Includes: sample raster grids, change report export, tile manifest, tests

## Overview

This project rounds out the current repo wave by adding a raster-first analysis lane. It compares a baseline grid to a later grid, calculates cell deltas, flags hotspots, and exports a change report that can later feed dashboards, alerts, or more realistic raster pipelines.

The current implementation is intentionally public-safe and runnable without GDAL or rasterio. It uses checked-in grid fixtures so the workflow is easy to review before adding GeoTIFF-backed processing.

## What It Demonstrates

- Repeatable raster change detection without notebook-only logic
- A handoff artifact for downstream review or alerting
- Tile manifest planning for larger raster workloads
- A clear extension path toward rasterio, GDAL, xarray, or parquet-backed summaries

## Project Structure

```text
raster-monitoring-pipeline/
|-- data/
|   |-- baseline_grid.json
|   `-- latest_grid.json
|-- src/raster_monitoring_pipeline/
|   |-- __init__.py
|   `-- pipeline.py
|-- tests/
|   `-- test_pipeline.py
|-- assets/
|   `-- raster-preview.svg
|-- docs/
|   |-- architecture.md
|   `-- demo-storyboard.md
|-- outputs/
|   `-- .gitkeep
|-- pyproject.toml
`-- README.md
```

## Quick Start

```bash
pip install -e .[dev]
python -m raster_monitoring_pipeline.pipeline
```

Run tests:

```bash
pytest
```

Generate the report with a custom pipeline name:

```bash
python -m raster_monitoring_pipeline.pipeline --pipeline-name "Heat Watch Pipeline"
```

## Current Output

The default command writes `outputs/raster_change_report.json` with:

- cell-by-cell delta summaries
- hotspot counts
- top-change ranking
- tile manifest metadata for downstream processing

See [docs/architecture.md](docs/architecture.md) for the design notes.
See [docs/demo-storyboard.md](docs/demo-storyboard.md) for the reviewer walkthrough.

## Publication

- License: [LICENSE](LICENSE)
- Standalone publishing notes: [PUBLISHING.md](PUBLISHING.md)
- Local CI workflow: [.github/workflows/ci.yml](.github/workflows/ci.yml)

## Repository Notes

This copy is intended to be publishable as its own repository.
