# Publishing Guide

## Recommended Standalone Repository Name

- raster-monitoring-pipeline

## Recommended Description

- Python raster change-detection pipeline for hotspot review, tile planning, and monitoring summaries.

## Suggested Topics

- rasterio
- gdal
- python
- remote-sensing
- gis
- geospatial
- analytics

## Split Steps

1. Create a new empty repository named `raster-monitoring-pipeline`.
2. Copy this project folder into the new repository root.
3. Preserve `data/`, `src/`, `tests/`, and `pyproject.toml`.
4. Use [assets/raster-preview.svg](assets/raster-preview.svg) as the initial visual preview.
5. Reference [docs/architecture.md](docs/architecture.md) and [docs/demo-storyboard.md](docs/demo-storyboard.md) from the README when polishing the public pitch.

## First Public Polish Pass

- Replace JSON grid fixtures with GeoTIFF-backed sample data
- Add one raster plot or exported heatmap asset
- Link this repository back to the analytics and open web map repos as the raster analysis lane
