# Architecture

## Overview

The Environmental Monitoring API is organized as a small service with three layers:

1. API layer in `api/routes.py`
2. configuration and infrastructure in `core/` and `database.py`
3. repository-backed data access in `repository.py`

## Runtime Modes

- `file` backend for lightweight local development and demos
- `postgis` backend for containerized or database-backed deployment

## Request Flow

1. A request enters FastAPI through a typed route.
2. The route resolves the active repository through configuration.
3. The repository returns validated feature models.
4. The API serializes those models as monitoring responses or summaries.

## Why It Works As A Portfolio Project

- Clear separation of concerns
- Swappable backends without changing the route layer
- User-facing dashboard plus API documentation
- Operational signals such as health, readiness, and alert summaries