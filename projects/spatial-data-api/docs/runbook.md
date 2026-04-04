# Runbook

## Purpose

Run the spatial API locally, verify map-facing endpoints, and confirm the service is ready for dashboard clients.

## Local Startup

```bash
pip install -e .[dev]
uvicorn spatial_data_api.main:app --reload
```

Docker path:

```bash
docker compose up --build
```

## Verification

Check:

- `GET /health`
- `GET /docs`
- `GET /api/v1/metadata`
- `GET /api/v1/features`

## Query Validation

- Confirm bbox filters return only the expected features.
- Confirm category and status filters behave consistently with the dashboard.
- Verify `openapi.json` is available before publishing.

## Operational Notes

- Keep file-backed sample data stable for local review.
- Re-run API tests after route, schema, or repository changes.
- Validate dashboard compatibility whenever the response shape changes.