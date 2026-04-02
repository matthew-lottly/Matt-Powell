# Runbook

## Purpose

Run STRATA in its main review modes: library tests, API service, and dashboard diagnostics.

## Local Setup

```bash
pip install -e .[dev,api,dashboard]
pytest -q
```

## API Startup

```bash
uvicorn hetero_conformal.api:create_app --factory --reload
```

Verify:

- `GET /health`
- `GET /datasets`

## Dashboard Startup

```bash
streamlit run dashboard/app.py
```

## Operational Notes

- Use synthetic runs first before attempting heavier benchmark configurations.
- Confirm FastAPI extras are installed before using the API mode.
- Re-run the conformal and graph test suites after architecture changes.