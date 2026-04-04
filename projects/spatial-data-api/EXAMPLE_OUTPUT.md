# Example Output

Representative GeoJSON response from a bbox-filtered feature request.

```json
{
  "type": "FeatureCollection",
  "count": 2,
  "features": [
    {"type": "Feature", "properties": {"site_id": "SZ-01", "risk_band": "warning"}, "geometry": {"type": "Point", "coordinates": [-95.38, 29.74]}},
    {"type": "Feature", "properties": {"site_id": "SZ-02", "risk_band": "critical"}, "geometry": {"type": "Point", "coordinates": [-95.35, 29.72]}}
  ]
}
```

The evaluation value here is shape and semantics: standards-compliant GeoJSON with immediately useful properties.