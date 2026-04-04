# Example Output

Representative ranked anomaly event list.

```csv
timestamp_utc,station_id,detector,score,severity,reason
2026-03-14T12:00:00Z,ST-117,rolling_zscore,4.8,critical,battery voltage collapsed faster than trailing 7-day baseline
2026-03-14T13:00:00Z,ST-204,delta_guard,3.9,warning,salinity jump exceeded expected hourly change envelope
2026-03-14T13:15:00Z,ST-091,mad_detector,3.2,warning,telemetry gap followed by unstable backfill values
```

The reviewer should be able to tell what happened, where, and why it was flagged.