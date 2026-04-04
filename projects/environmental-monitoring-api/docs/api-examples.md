# API Request and Response Examples

Concrete request and response pairs for review, integration testing, or consuming client development.

## Health Check

```bash
curl http://localhost:8000/health
```

```json
{
  "status": "ok",
  "backend": "file",
  "ready": true,
  "data_source": "sample_features.geojson"
}
```

## Station Status Query

```bash
curl http://localhost:8000/api/v1/features/station-002
```

```json
{
  "type": "Feature",
  "properties": {
    "featureId": "station-002",
    "name": "Sierra Air Quality Node",
    "category": "air_quality",
    "region": "West",
    "status": "alert",
    "lastObservationAt": "2026-03-18T12:05:00Z"
  },
  "geometry": {
    "type": "Point",
    "coordinates": [-121.5, 38.56]
  }
}
```

## Filtered Feature Listing

```bash
curl "http://localhost:8000/api/v1/features?category=hydrology&status=normal"
```

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "featureId": "station-001",
        "name": "Rio Grande Gauge",
        "category": "hydrology",
        "region": "Southwest",
        "status": "normal",
        "lastObservationAt": "2026-03-18T12:00:00Z"
      },
      "geometry": {
        "type": "Point",
        "coordinates": [-106.65, 35.08]
      }
    }
  ]
}
```

## Operations Summary

```bash
curl http://localhost:8000/api/v1/summary
```

```json
{
  "totalFeatures": 3,
  "alertFeatures": 1,
  "offlineFeatures": 1,
  "alertRate": 0.3333,
  "regionalAlerts": [
    { "region": "West", "alertFeatures": 1, "alertObservations": 2 }
  ],
  "recentAlerts": [
    {
      "observationId": "obs-2001",
      "featureId": "station-002",
      "stationName": "Sierra Air Quality Node",
      "region": "West",
      "category": "air_quality",
      "observedAt": "2026-03-18T12:05:00Z",
      "metricName": "pm25",
      "value": 41.8,
      "unit": "ug/m3",
      "alertScore": 0.85
    }
  ]
}
```

## Threshold Configuration

```bash
curl -X POST http://localhost:8000/api/v1/stations/station-002/thresholds \
  -H "Content-Type: application/json" \
  -d '{"metricName": "pm25", "maxValue": 50.0}'
```

```json
{
  "featureId": "station-002",
  "metricName": "pm25",
  "minValue": null,
  "maxValue": 50.0
}
```

After the threshold update, re-query the station to see derived alert state changes:

```bash
curl http://localhost:8000/api/v1/features/station-002
```

The `status` field reflects the threshold evaluation against the latest observation.

## Observation Export Bundle

```bash
curl "http://localhost:8000/api/v1/observations/export?region=West"
```

```json
{
  "source": {
    "name": "environmental-monitoring-api",
    "exportedAt": "2026-03-18T12:10:00Z",
    "dataSource": "sample_features.geojson"
  },
  "filters": { "region": "West" },
  "features": { "type": "FeatureCollection", "features": ["..."] },
  "observations": { "observations": ["..."], "summary": {"...": "..."} },
  "thresholds": [
    { "featureId": "station-002", "metricName": "pm25", "minValue": null, "maxValue": 35.0 }
  ]
}
```

## CSV Export

```bash
curl "http://localhost:8000/api/v1/observations/export?format=csv"
```

```csv
observation_id,feature_id,station_name,category,region,observed_at,metric_name,value,unit,status,min_threshold,max_threshold
obs-2001,station-002,Sierra Air Quality Node,air_quality,West,2026-03-18T12:05:00Z,pm25,41.8,ug/m3,alert,,35.0
```

## Error Responses

### Feature Not Found (404)

```json
{ "detail": "Feature not found" }
```

### Partial Bounding Box (422)

```json
{ "detail": "All bounding-box coordinates must be provided together" }
```

### Invalid Threshold (422)

Returned when `minValue >= maxValue` or neither bound is provided.
