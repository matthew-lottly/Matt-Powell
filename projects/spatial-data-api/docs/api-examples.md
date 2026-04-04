# API Request and Response Examples

Concrete request and response pairs for each endpoint. Use these for review, integration testing, or client development.

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

## Readiness Check

```bash
curl http://localhost:8000/health/ready
```

```json
{
  "status": "ok",
  "ready": true
}
```

## Service Metadata

```bash
curl http://localhost:8000/api/v1/metadata
```

```json
{
  "name": "Environmental Monitoring API",
  "version": "0.1.0",
  "environment": "development",
  "backend": "file",
  "feature_count": 3,
  "data_source": "sample_features.geojson"
}
```

## List Features with Category Filter

```bash
curl "http://localhost:8000/api/v1/features?category=hydrology"
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

## List Features with Bounding Box

```bash
curl "http://localhost:8000/api/v1/features?min_longitude=-123.0&min_latitude=37.0&max_longitude=-120.0&max_latitude=40.0"
```

```json
{
  "type": "FeatureCollection",
  "features": [
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
  ]
}
```

## Feature Summary

```bash
curl http://localhost:8000/api/v1/features/summary
```

```json
{
  "total_features": 3,
  "categories": {
    "hydrology": 1,
    "air_quality": 1,
    "water_quality": 1
  },
  "statuses": {
    "normal": 1,
    "alert": 1,
    "offline": 1
  },
  "regions": ["Southwest", "West", "Gulf"]
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
    {
      "region": "Southwest",
      "alertFeatures": 0,
      "alertObservations": 0
    },
    {
      "region": "Gulf",
      "alertFeatures": 0,
      "alertObservations": 0
    },
    {
      "region": "West",
      "alertFeatures": 1,
      "alertObservations": 2
    }
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
  ],
  "startAt": null,
  "endAt": null
}
```

## Operations Summary with Time Window

```bash
curl "http://localhost:8000/api/v1/summary?start_at=2026-03-18T12:00:00Z&end_at=2026-03-18T12:05:00Z"
```

Returns the same structure but filters recent alerts to the specified window.

## Recent Observations

```bash
curl "http://localhost:8000/api/v1/observations/recent?limit=3"
```

```json
{
  "observations": [
    {
      "observationId": "obs-2001",
      "featureId": "station-002",
      "observedAt": "2026-03-18T12:05:00Z",
      "metricName": "pm25",
      "value": 41.8,
      "unit": "ug/m3",
      "status": "alert"
    }
  ],
  "summary": {
    "totalObservations": 3,
    "categories": {"air_quality": 2, "hydrology": 1},
    "statuses": {"alert": 2, "normal": 1},
    "metrics": {"pm25": 2, "river_stage_ft": 1},
    "earliestObservedAt": "2026-03-18T12:00:00Z",
    "latestObservedAt": "2026-03-18T12:05:00Z"
  }
}
```

## Feature Observations

```bash
curl "http://localhost:8000/api/v1/features/station-001/observations?limit=2"
```

```json
{
  "observations": [
    {
      "observationId": "obs-1001",
      "featureId": "station-001",
      "observedAt": "2026-03-18T12:00:00Z",
      "metricName": "river_stage_ft",
      "value": 4.2,
      "unit": "ft",
      "status": "normal"
    }
  ],
  "summary": {
    "totalObservations": 2,
    "categories": {"hydrology": 2},
    "statuses": {"normal": 2},
    "metrics": {"river_stage_ft": 2},
    "earliestObservedAt": "2026-03-17T18:00:00Z",
    "latestObservedAt": "2026-03-18T12:00:00Z"
  }
}
```

## Set Station Threshold

```bash
curl -X POST http://localhost:8000/api/v1/stations/station-002/thresholds \
  -H "Content-Type: application/json" \
  -d '{"metricName": "pm25", "maxValue": 45.0}'
```

```json
{
  "featureId": "station-002",
  "metricName": "pm25",
  "minValue": null,
  "maxValue": 45.0
}
```

## Export Observations as JSON Bundle

```bash
curl "http://localhost:8000/api/v1/observations/export?region=West&min_longitude=-123.0&min_latitude=37.0&max_longitude=-120.0&max_latitude=40.0"
```

```json
{
  "source": {
    "name": "environmental-monitoring-api",
    "exportedAt": "2026-03-18T12:10:00Z",
    "dataSource": "sample_features.geojson"
  },
  "filters": {
    "region": "West",
    "bbox": [-123.0, 37.0, -120.0, 40.0]
  },
  "features": { "type": "FeatureCollection", "features": ["..."] },
  "observations": { "observations": ["..."], "summary": {"...": "..."} },
  "thresholds": [
    { "featureId": "station-002", "metricName": "pm25", "minValue": null, "maxValue": 35.0 }
  ]
}
```

## Export Observations as CSV

```bash
curl "http://localhost:8000/api/v1/observations/export?format=csv&start_at=2026-03-18T12:00:00Z"
```

```csv
observation_id,feature_id,station_name,category,region,observed_at,metric_name,value,unit,status,min_threshold,max_threshold
obs-2001,station-002,Sierra Air Quality Node,air_quality,West,2026-03-18T12:05:00Z,pm25,41.8,ug/m3,alert,,35.0
obs-1001,station-001,Rio Grande Gauge,hydrology,Southwest,2026-03-18T12:00:00Z,river_stage_ft,4.2,ft,normal,,
```

## Error Responses

### Feature Not Found

```bash
curl http://localhost:8000/api/v1/features/nonexistent
```

```json
{ "detail": "Feature not found" }
```

HTTP 404.

### Partial Bounding Box

```bash
curl "http://localhost:8000/api/v1/features?min_longitude=-123.0"
```

```json
{ "detail": "All bounding-box coordinates must be provided together" }
```

HTTP 422.

### Invalid Threshold Bounds

```bash
curl -X POST http://localhost:8000/api/v1/stations/station-002/thresholds \
  -H "Content-Type: application/json" \
  -d '{"metricName": "pm25", "minValue": 50.0, "maxValue": 45.0}'
```

HTTP 422. `minValue` must be less than `maxValue`.
