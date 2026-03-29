# Publishing Guide

## Recommended Standalone Repository Name

- qgis-operations-workbench

## Recommended Description

- QGIS-oriented Python project for packaging desktop GIS review workflows, bookmarks, and route-based layout jobs.

## Suggested Topics

- qgis
- pyqgis
- python
- gdal
- geopackage
- gis
- geospatial

## Split Steps

1. Create a new empty repository named `qgis-operations-workbench`.
2. Copy this project folder into the new repository root.
3. Preserve `data/`, `src/`, `tests/`, and `pyproject.toml`.
4. Use [assets/workbench-preview.svg](assets/workbench-preview.svg) as the initial visual preview.
5. Reference [docs/architecture.md](docs/architecture.md) and [docs/demo-storyboard.md](docs/demo-storyboard.md) from the README when polishing the public pitch.

## First Public Polish Pass

- Add one exported JSON example or QGIS screenshot from a local workstation run
- Include the generated GeoPackage in the walkthrough notes and optionally add a PyQGIS automation script for project or layout export
- Link this repository back to the API and warehouse repos as the desktop GIS companion lane
