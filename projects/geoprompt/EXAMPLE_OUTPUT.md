# Example Output

Representative GeoJSON feature output from a prompt-driven spatial extraction.

```json
{
  "type": "Feature",
  "properties": {
    "label": "priority-inspection-zone",
    "risk_score": 0.82,
    "reason": "high proximity to repeat inundation footprint"
  },
  "geometry": {
    "type": "Polygon",
    "coordinates": [[[-95.42, 29.71], [-95.40, 29.71], [-95.40, 29.73], [-95.42, 29.73], [-95.42, 29.71]]]
  }
}
```

This is the kind of direct geometry artifact someone can evaluate without importing the package.