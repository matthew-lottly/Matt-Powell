# Example Output

Representative service-ready table and view contract summary.

```text
schema: monitoring
base_table: monitoring.station_observations
primary_key: observation_id
spatial_index: gist(geom)
published_view: monitoring_api.current_station_status
published_columns: station_id, observed_at_utc, status_band, alert_count, geom
```

This gives a reviewer a concrete sense of what the blueprint is meant to expose downstream.