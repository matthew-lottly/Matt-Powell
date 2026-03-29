# Publishing Guide

## Recommended Standalone Repository Name

- postgis-service-blueprint

## Recommended Description

- Open spatial service blueprint for publishing PostGIS-backed layers with collection metadata and query patterns.

## Suggested Topics

- postgis
- postgresql
- sql
- python
- ogc-api-features
- gis
- geospatial

## Split Steps

1. Create a new empty repository named `postgis-service-blueprint`.
2. Copy this project folder into the new repository root.
3. Preserve `data/`, `sql/`, `src/`, `tests/`, and `pyproject.toml`.
4. Use [assets/service-preview.svg](assets/service-preview.svg) as the initial visual preview.
5. Reference [docs/architecture.md](docs/architecture.md) and [docs/demo-storyboard.md](docs/demo-storyboard.md) from the README when polishing the public pitch.

## First Public Polish Pass

- Keep the local PostGIS seed script and Docker compose stack in sync with the sample layer fixture
- Add one concrete delivery layer example through FastAPI or PostgREST
- Link this repository back to the QGIS workbench and API repos as the open spatial publishing lane
