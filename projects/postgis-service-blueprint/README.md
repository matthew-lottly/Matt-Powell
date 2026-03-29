# PostGIS Service Blueprint

Open-stack GIS portfolio project for shaping how PostGIS-backed layers become publishable spatial services.

![Service blueprint preview](assets/service-preview.svg)

## Snapshot

- Lane: Spatial services and data publishing
- Domain: PostGIS-first service design
- Stack: Python, SQL, GeoJSON, PostgreSQL/PostGIS planning
- Includes: sample spatial layers, SQL schema, publication views, exported blueprint artifact, PostGIS seed SQL, tests

## Overview

This project starts the next open spatial service lane after the desktop QGIS workbench. It focuses on the service-design side of geospatial engineering: what gets stored in PostGIS, which views are safe to publish, and how a service contract should look before a delivery layer is built.

The current implementation stays lightweight and public-safe. It exports a JSON blueprint artifact and includes SQL for schema and publication views so the project is useful before a full API or PostgREST deployment is added.

It also includes a local PostGIS stack and a generated seed SQL file so the sample collections can be loaded into a real database without inventing setup steps later.

## What It Demonstrates

- Clear separation between source tables and publication-ready views
- PostGIS-oriented indexing and collection planning
- Spatial service contract design for bbox and attribute filters
- Seed-data generation for a local PostGIS container
- A bridge between sample spatial data and future delivery through FastAPI, PostgREST, or OGC API Features

## Project Structure

```text
postgis-service-blueprint/
|-- data/
|   `-- service_layers.geojson
|-- docker-compose.yml
|-- sql/
|   |-- schema.sql
|   |-- sample_seed.sql
|   `-- service_views.sql
|-- src/postgis_service_blueprint/
|   |-- __init__.py
|   `-- blueprint.py
|-- tests/
|   `-- test_blueprint.py
|-- assets/
|   `-- service-preview.svg
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
python -m postgis_service_blueprint.blueprint
python -m postgis_service_blueprint.blueprint --export-seed-sql
docker compose up -d database
```

Run tests:

```bash
pytest
```

Generate the blueprint with a custom service name:

```bash
python -m postgis_service_blueprint.blueprint --service-name "Regional Spatial Service"
```

## Current Output

The default command writes `outputs/postgis_service_blueprint.json` with:

- collection metadata grouped by layer
- service endpoints and query patterns
- publication-plan notes for PostGIS indexes and delivery options
- bounds and summary counts for the sample layers

With `--export-seed-sql`, the command also writes `outputs/sample_seed.sql`, which mirrors the sample GeoJSON into `INSERT` statements for the local PostGIS container.

See [docs/architecture.md](docs/architecture.md) for the design notes.
See [docs/demo-storyboard.md](docs/demo-storyboard.md) for the reviewer walkthrough.
See [docs/local-postgis-workflow.md](docs/local-postgis-workflow.md) for the container and seed flow.

## Publication

- License: [LICENSE](LICENSE)
- Standalone publishing notes: [PUBLISHING.md](PUBLISHING.md)
- Local CI workflow: [.github/workflows/ci.yml](.github/workflows/ci.yml)

## Repository Notes

This copy is intended to be publishable as its own repository.
