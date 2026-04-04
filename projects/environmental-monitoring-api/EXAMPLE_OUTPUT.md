# Example Output

Representative API response for a station status query.

```json
{
  "station_id": "ST-204",
  "region": "coastal-south",
  "status": "warning",
  "latest_observation_utc": "2026-03-14T16:00:00Z",
  "metrics": {
    "water_level_ft": 6.2,
    "salinity_psu": 18.4,
    "battery_v": 11.7
  },
  "alerts": ["salinity_above_threshold", "battery_declining"]
}
```

The important review signal is the shape of the payload: stable IDs, timestamps, current metrics, and explicit alert flags.