# Local PostGIS Workflow

This project includes a lightweight local PostGIS stack for testing the blueprint against a real database.

## 1. Generate seed SQL

```bash
python -m postgis_service_blueprint.blueprint --export-seed-sql
```

This writes `outputs/sample_seed.sql`.

## 2. Copy the seed SQL into the init folder

```powershell
Copy-Item outputs/sample_seed.sql sql/sample_seed.sql -Force
```

## 3. Start the database

```bash
docker compose up -d database
```

The container starts with:

- `sql/schema.sql`
- `sql/service_views.sql`
- `sql/sample_seed.sql`

## 4. Inspect the published views

Example connection target:

```text
postgresql://spatial:spatial@localhost:5433/spatial_blueprint
```

Once connected, inspect:

- `monitoring_features`
- `published_monitoring_sites`
- `published_maintenance_zones`

This keeps the repo public-safe while still giving reviewers a real local PostGIS path.
