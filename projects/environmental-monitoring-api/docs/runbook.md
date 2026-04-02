# Runbook

## Purpose

Run the API locally, verify health, and switch between the file-backed and PostGIS-backed modes.

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
- `GET /health/ready`
- `GET /docs`
- `GET /dashboard`

## Backend Modes

- Default local mode uses the checked-in sample feature data.
- PostGIS mode should be enabled only after connection settings and schema are verified.

## Operational Notes

- Validate threshold update behavior before exposing write endpoints.
- Confirm dashboard rendering against the same backend mode used by the API.
- Run the API test suite after any repository or schema change.