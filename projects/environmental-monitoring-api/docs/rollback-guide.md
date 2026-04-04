# Rollback Guide

Procedures for reverting to a known-good state after a deployment regression.

## Container Rollback

The CI workflow publishes `ghcr.io/matthew-lottly/environmental-monitoring-api:latest` on pushes to `main`. If the latest image introduces a regression:

```bash
# Stop current deployment
docker compose down

# Pin to a specific commit SHA tag in docker-compose.yml
# image: ghcr.io/matthew-lottly/environmental-monitoring-api:sha-abc1234

docker compose up -d
```

For local development, rebuild from a known-good commit:

```bash
git checkout <known-good-commit>
docker compose up --build -d
```

## Database Rollback

If a schema change corrupts the PostGIS data:

```bash
# Stop the API
docker compose down

# Drop and recreate from seed scripts
docker compose down -v
docker compose up -d --build
```

This reloads `sql/postgis_schema.sql` and `sql/sample_seed.sql`.

For production, restore from a backup:

```bash
pg_restore --clean --if-exists -d spatial backup_file.dump
```

## File-backed Mode Rollback

The file-backed repository uses checked-in GeoJSON. Revert the data file to a known-good state:

```bash
git checkout main -- src/spatial_data_api/data/sample_features.geojson
```

## Configuration Reset

Restore all environment variables to defaults:

```bash
copy .env.example .env
docker compose up -d --build
```

Key variables to check:
- `SPATIAL_DATA_API_REPOSITORY_BACKEND` must be `file` or `postgis`
- `SPATIAL_DATA_API_DATABASE_URL` must point to the running PostgreSQL instance

## Post-Rollback Verification

```bash
curl http://localhost:8000/health
curl http://localhost:8000/health/ready
curl http://localhost:8000/api/v1/metadata
curl http://localhost:8000/api/v1/features
pytest
```

All checks should return HTTP 200 with valid payloads.

## Prevention Checklist

- Run `pytest` locally before every push to `main`
- Validate the OpenAPI schema before publishing
- Pin container image tags in production deployments
- Keep `.env.example` current as a reset baseline
- Run PostGIS integration tests when schema changes land
