# Runbook

## Purpose

Use the blueprint to validate schema design, publication views, and seed-SQL generation before promoting the design into a live service.

## Local Workflow

```bash
pip install -e .[dev]
python -m postgis_service_blueprint.blueprint --output-dir outputs --export-seed-sql
```

Docker path:

```bash
docker compose up --build
```

## Verification

- Confirm `postgis_service_blueprint.json` is generated.
- Confirm seed SQL is generated and contains geometry inserts.
- Review publication-view fields before handing off to an API layer.

## Promotion Checklist

- Freeze collection IDs and query patterns.
- Confirm SRID assumptions and geometry types.
- Validate the seed SQL against a disposable PostGIS instance.