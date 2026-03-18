# Spatial Data API

Backend service for browsing and summarizing geospatial data through a clean, typed API.

## Overview

This project is a fresh showcase starter for a geospatial backend. It loads a sample GeoJSON dataset for local development, supports an optional PostGIS-backed repository for standalone deployment, and exposes a typed API for health checks, metadata, filtering, and feature lookup.

The implementation is intentionally small, but it now includes the wiring needed to run as a standalone service with Docker, environment-based configuration, and a PostGIS container.

## Why This Project Exists

Geospatial work often stops at files and scripts. This project demonstrates the next step: turning spatial data into an application service with a stable interface that other tools, analysts, and products can consume.

## Current Features

- FastAPI application with versioned API routes
- Typed response models for features and metadata
- File-backed repository for local development
- Optional PostGIS-backed repository for standalone deployment
- Filtering by category and region
- Summary endpoint for quick portfolio demos
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

## Project Structure

```text
projects/spatial-data-api/
|-- src/spatial_data_api/
|   |-- api/
|   |-- core/
|   |-- data/
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

This gives the project a ready-to-run spatial table and seed dataset for local container use.

## Next Steps

- Add an ingestion pipeline for new datasets
- Add authentication and access control
- Expand tests around filtering and data validation
- Add CI and image publishing