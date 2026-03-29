# API Snapshot Contract

The analytics project accepts two input forms:

1. The default CSV dataset at `data/station_observations.csv`
2. A JSON snapshot bundle derived from the API project

## Supported JSON Shape

The JSON input can be a top-level object with:

- `features`: either the full `GET /api/v1/features` response object or its `features` array
- `observations`: either the full `GET /api/v1/observations/recent` response object or its `observations` array

Example:

```json
{
  "source": {
    "project": "spatial-data-api",
    "capturedAt": "2026-03-18T12:10:00Z"
  },
  "features": {
    "type": "FeatureCollection",
    "features": []
  },
  "observations": {
    "observations": []
  }
}
```

## Normalized Fields

At report time, the analytics project normalizes the bundle into these columns:

- `station_id`
- `station_name`
- `category`
- `region`
- `observed_at`
- `status`
- `alert_score`
- `reading_value`

If the JSON observations already carry those normalized fields, they can be used directly.

If an API bundle does not include `alert_score`, the analytics project falls back to a simple status-based proxy:

- `alert` -> `1.0`
- `normal` -> `0.25`
- `offline` -> `0.05`

This keeps the API-derived path runnable without changing the API response schema.

## Run Command

```bash
python -m environmental_monitoring_analytics.reporting --input data/api_observation_snapshot.json
```