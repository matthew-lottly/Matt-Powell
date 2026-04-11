# Example Output

Representative alert mart slice for an operations review.

```sql
station_id | snapshot_date | health_band | active_alerts | telemetry_sla_pct
-----------+---------------+-------------+---------------+------------------
ST-117     | 2026-03-14    | critical    | 3             | 82.4
ST-204     | 2026-03-14    | warning     | 2             | 94.1
ST-055     | 2026-03-14    | healthy     | 0             | 99.7
```

This shows the intended warehouse output style: one row per station-day with alertability and service-level context.