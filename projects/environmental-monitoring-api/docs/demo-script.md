# Demo Script

## Goal

Show the project as an applied backend and GIS portfolio piece in under three minutes.

## Flow

1. Open the dashboard at `/dashboard` and point out readiness, backend, and current alert status.
2. Use the map section to explain that the service is exposing monitoring stations as geospatial features, not just rows in a database.
3. Call out the alert card and describe how the API supports operational triage.
4. Open `/docs` and show the typed endpoints for health, metadata, filtering, and summaries.
5. Mention that the repository supports both local file-backed mode and PostGIS-backed deployment through Docker.

## Talking Points

- Backend service design with FastAPI and typed schemas
- GIS-aware data exposure through feature geometry and regional filtering
- Optional PostGIS integration for realistic deployment
- Readiness checks, CI, and integration-test scaffolding

## Best Demo URLs

- `/dashboard`
- `/docs`
- `/api/v1/features?status=alert`
- `/api/v1/features/summary`