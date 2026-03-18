# Environmental Monitoring API

Production-style backend for monitoring stations, environmental observations, and spatial status reporting through a typed API.

![Dashboard preview](assets/dashboard-preview.svg)

## Snapshot

- Lane: Backend + GIS
- Domain: Environmental monitoring
- Stack: FastAPI, PostgreSQL, PostGIS, Docker, Python
- Includes: dashboard, health checks, typed API, optional PostGIS backend, tests

## Overview

This project shows how a geospatial monitoring dataset can be turned into an application service instead of remaining a collection of files and dashboards. It ships with a local file-backed dataset for fast startup, an optional PostGIS-backed repository for deployment, and a browser dashboard for quick operational review.

## Why This Project Exists

Environmental monitoring work often stops at spreadsheets, maps, and one-off scripts. This repository demonstrates the next layer: a stable backend interface that other tools, analysts, and applications can consume reliably.

## What It Includes

- FastAPI application with versioned API routes
- Typed response models for features and metadata
- File-backed repository for local development
- Optional PostGIS-backed repository for standalone deployment
- Filtering by category, region, and station status
- Summary endpoint for quick monitoring rollups
- Recent-observation and per-station observation-history endpoints
- Browser dashboard for quick visual review of service health, station status, alert locations, and recent readings
- Test coverage for the main endpoints
- Docker and docker-compose setup

## Tech Stack

- Python 3.11+
- FastAPI
- Pydantic and pydantic-settings
- SQLAlchemy
- PostgreSQL and PostGIS
- Pytest

## API Endpoints

- `GET /health`
- `GET /health/ready`
- `GET /api/v1/metadata`
- `GET /api/v1/features`
- `GET /api/v1/features/summary`
- `GET /api/v1/features/{feature_id}`
- `GET /api/v1/observations/recent`
- `GET /api/v1/features/{feature_id}/observations`

Observation endpoints accept optional `start_at` and `end_at` ISO timestamps for time-window filtering.

Example monitoring domains in the sample data:

- Hydrology
- Air quality
- Water quality

## Why It Is Useful In A Portfolio

- Shows backend engineering beyond CRUD by combining health checks, typed contracts, and deployment-ready configuration
- Demonstrates GIS fluency through coordinate data, map display, and PostGIS support
- Gives reviewers a fast path from API docs to a live dashboard and test suite

## Project Structure

```text
environmental-monitoring-api/
|-- src/spatial_data_api/
|   |-- api/
|   |-- core/
|   |-- data/
|   |-- dashboard/
|   |-- database.py
|   |-- main.py
|   |-- repository.py
|   `-- schemas.py
|-- sql/
|-- tests/
|-- docker-compose.yml
|-- Dockerfile
|-- pyproject.toml
`-- README.md
```

## Quick Start

### Local file-backed mode

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
uvicorn spatial_data_api.main:app --reload --app-dir src
```

Then open `http://127.0.0.1:8000/docs`.

For a visual demo, open `http://127.0.0.1:8000/dashboard`.

See [docs/demo-script.md](docs/demo-script.md) for a short presentation flow.
See [docs/architecture.md](docs/architecture.md) for the project structure overview.
See [docs/roadmap.md](docs/roadmap.md) for the next planned improvements.
See [docs/public-issues.md](docs/public-issues.md) for good first public follow-up tasks.

### Docker with PostGIS

```bash
copy .env.example .env
docker compose up --build
```

This starts:

- The API on `http://127.0.0.1:8000`
- Swagger UI on `http://127.0.0.1:8000/docs`
- PostgreSQL with PostGIS on `localhost:5432`

The default `.env.example` uses the PostGIS-backed repository when running in Docker.

## Validation

Run the unit tests:

```bash
pytest
```

Run the PostGIS integration tests after starting Docker:

```bash
copy .env.example .env
docker compose up -d --build
set SPATIAL_DATA_API_RUN_DB_TESTS=1
pytest tests/integration
```

The integration tests default to `postgresql+psycopg://spatial:spatial@localhost:5432/spatial`. Override that with `SPATIAL_DATA_API_INTEGRATION_DB_URL` if needed.

## Publication

- License: [LICENSE](LICENSE)
- Standalone publishing notes: [PUBLISHING.md](PUBLISHING.md)
- Local CI workflow: [.github/workflows/ci.yml](.github/workflows/ci.yml)

## Configuration

Key environment variables:

- `SPATIAL_DATA_API_APP_ENV`
- `SPATIAL_DATA_API_API_PREFIX`
- `SPATIAL_DATA_API_REPOSITORY_BACKEND`
- `SPATIAL_DATA_API_DATA_PATH`
- `SPATIAL_DATA_API_DATABASE_URL`

`SPATIAL_DATA_API_REPOSITORY_BACKEND` supports:

- `file` for local development using sample GeoJSON
- `postgis` for database-backed operation

## PostGIS Schema

The database container loads:

- [sql/postgis_schema.sql](sql/postgis_schema.sql)
- [sql/sample_seed.sql](sql/sample_seed.sql)

This gives the project a ready-to-run monitoring-station table and seed dataset for local container use.

## Next Steps

- Add category-level rollups for filtered observation-history queries
- Add an ingestion pipeline for new monitoring feeds
- Add authentication and access control
- Add container image publishing

## Repository Notes

This copy is intended to be publishable as its own repository. CI is included in [.github/workflows/ci.yml](.github/workflows/ci.yml).