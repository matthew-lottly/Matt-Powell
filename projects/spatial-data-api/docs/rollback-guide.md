# Rollback Guide

Procedures for reverting the spatial data API to a known-good state after a failed deploy or breaking change.

## Container Rollback

If the latest container image introduces a regression:

```bash
# Pull the previous known-good tag
docker pull ghcr.io/matthew-lottly/environmental-monitoring-api:previous-tag

# Stop the current container
docker compose down

# Update docker-compose.yml to pin the image tag, then restart
docker compose up -d
```

When CI publishes to `ghcr.io`, each push to `main` overwrites `:latest`. Pin to a specific commit SHA tag or version tag for production stability.

## Database Rollback

If a schema migration causes data issues with the PostGIS backend:

1. Stop the API to prevent further writes
2. Restore from the most recent database backup
3. Verify the schema matches the expected version

```bash
docker compose down

# Restore from backup (example with pg_restore)
pg_restore --clean --if-exists -d spatial backup.dump

docker compose up -d
```

If no backup is available for the development environment, drop and recreate from the seed scripts:

```bash
docker compose down -v
docker compose up -d --build
```

This reloads `sql/postgis_schema.sql` and `sql/sample_seed.sql` from scratch.

## File-backed Mode Rollback

The file-backed repository reads from checked-in GeoJSON. To revert:

```bash
git checkout main -- src/spatial_data_api/data/sample_features.geojson
pip install -e .[dev]
uvicorn spatial_data_api.main:app --reload --app-dir src
```

## Configuration Rollback

If an environment variable change breaks the service:

1. Check `SPATIAL_DATA_API_REPOSITORY_BACKEND` — it must be `file` or `postgis`
2. Check `SPATIAL_DATA_API_DATABASE_URL` — it must match the running PostgreSQL instance
3. Restore `.env` from `.env.example` to reset to defaults

```bash
copy .env.example .env
docker compose up -d --build
```

## Verification After Rollback

After any rollback, run the verification checklist:

```bash
# Health check
curl http://localhost:8000/health

# Readiness check
curl http://localhost:8000/health/ready

# Metadata check
curl http://localhost:8000/api/v1/metadata

# Feature listing
curl http://localhost:8000/api/v1/features

# Run the test suite
pytest
```

All endpoints should return HTTP 200 with valid payloads.

## Prevention

- Run `pytest` before every deploy
- Validate `openapi.json` is available before publishing
- Pin container image tags in production instead of using `:latest`
- Keep `.env.example` current so it can serve as a reset baseline
