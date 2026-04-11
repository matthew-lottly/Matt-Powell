# Example Output

Representative risk classification output for a scored station batch.

```csv
station_id,predicted_risk,confidence,top_driver,secondary_driver
ST-117,high,0.87,telemetry_gap_rate,battery_decline
ST-204,medium,0.73,salinity_variability,late_ingest_count
ST-055,low,0.91,stable_baseline,high_uptime
```

The point of the artifact is not only the label, but also the explainability drivers attached to each station.