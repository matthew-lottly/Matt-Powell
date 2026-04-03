# Rollback Guide

Procedures for reverting the PostGIS service blueprint to a known-good state.

## Database Rollback

If a schema change corrupts the PostGIS data:

```bash
# Stop the service
docker compose down

# Drop and recreate from seed data
docker compose down -v
docker compose up -d --build
```

This reloads the schema and seed scripts from scratch.

For production environments, restore from a backup:

```bash
pg_restore --clean --if-exists -d spatial_blueprint backup_file.dump
```

## Configuration Reset

Restore environment variables to defaults:

```bash
copy .env.example .env
docker compose up -d --build
```

## View and Publication Rollback

If a publication view change breaks downstream consumers:

1. Revert the SQL view definition to the previous version
2. Restart the service to reload views
3. Verify downstream clients receive the expected payload shape

## Post-Rollback Verification

- Confirm the health endpoint returns HTTP 200
- Verify seed data is accessible through the API
- Run the test suite to confirm baseline behavior
- Check that publication views return the expected column set
