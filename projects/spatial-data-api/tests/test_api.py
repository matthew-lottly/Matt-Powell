"""Pyright import resolution in the parent workspace does not model this nested src layout."""

# pyright: reportMissingImports=false

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from spatial_data_api.main import app
from spatial_data_api.repository import get_repository


client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_repository_cache() -> Generator[None, None, None]:
    get_repository.cache_clear()
    yield
    get_repository.cache_clear()


def test_healthcheck() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "backend": "file",
        "ready": True,
        "data_source": "sample_features.geojson",
    }


def test_root_lists_dashboard() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["dashboard"] == "/dashboard"


def test_dashboard_page() -> None:
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "Environmental Monitoring Dashboard" in response.text


def test_readiness_check() -> None:
    response = client.get("/health/ready")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["ready"] is True


def test_metadata() -> None:
    response = client.get("/api/v1/metadata")
    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "Environmental Monitoring API"
    assert payload["backend"] == "file"
    assert payload["feature_count"] == 3
    assert payload["data_source"] == "sample_features.geojson"


def test_list_features_by_category() -> None:
    response = client.get("/api/v1/features", params={"category": "hydrology"})
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["features"]) == 1
    assert payload["features"][0]["properties"]["featureId"] == "station-001"


def test_list_features_by_status() -> None:
    response = client.get("/api/v1/features", params={"status": "alert"})
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["features"]) == 1
    assert payload["features"][0]["properties"]["name"] == "Sierra Air Quality Node"


def test_list_features_by_bounding_box() -> None:
    response = client.get(
        "/api/v1/features",
        params={
            "min_longitude": -123.0,
            "min_latitude": 37.0,
            "max_longitude": -120.0,
            "max_latitude": 40.0,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert [feature["properties"]["featureId"] for feature in payload["features"]] == ["station-002"]


def test_list_features_rejects_partial_bounding_box() -> None:
    response = client.get("/api/v1/features", params={"min_longitude": -123.0})
    assert response.status_code == 422
    assert response.json()["detail"] == "All bounding-box coordinates must be provided together"


def test_feature_summary() -> None:
    response = client.get("/api/v1/features/summary")
    assert response.status_code == 200
    payload = response.json()
    assert payload["statuses"]["alert"] == 1
    assert payload["categories"]["water_quality"] == 1


def test_operations_summary() -> None:
    response = client.get("/api/v1/summary")
    assert response.status_code == 200
    payload = response.json()
    assert payload["totalFeatures"] == 3
    assert payload["alertFeatures"] == 1
    assert payload["offlineFeatures"] == 1
    assert payload["alertRate"] == 0.3333
    assert payload["regionalAlerts"][2] == {
        "region": "West",
        "alertFeatures": 1,
        "alertObservations": 2,
    }
    assert payload["recentAlerts"][0]["observationId"] == "obs-2001"
    assert payload["recentAlerts"][0]["featureId"] == "station-002"


def test_operations_summary_with_time_window() -> None:
    response = client.get(
        "/api/v1/summary",
        params={"start_at": "2026-03-18T12:00:00Z", "end_at": "2026-03-18T12:05:00Z"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["startAt"] == "2026-03-18T12:00:00Z"
    assert payload["endAt"] == "2026-03-18T12:05:00Z"
    assert [item["observationId"] for item in payload["recentAlerts"]] == ["obs-2001"]


def test_threshold_update_changes_feature_status() -> None:
    response = client.post(
        "/api/v1/stations/station-002/thresholds",
        json={"metricName": "pm25", "maxValue": 45.0},
    )
    assert response.status_code == 200
    assert response.json() == {
        "featureId": "station-002",
        "metricName": "pm25",
        "minValue": None,
        "maxValue": 45.0,
    }

    feature_response = client.get("/api/v1/features/station-002")
    assert feature_response.status_code == 200
    assert feature_response.json()["properties"]["status"] == "normal"

    summary_response = client.get("/api/v1/features/summary")
    assert summary_response.status_code == 200
    assert summary_response.json()["statuses"] == {"normal": 2, "offline": 1}


def test_threshold_update_validates_bounds() -> None:
    response = client.post(
        "/api/v1/stations/station-002/thresholds",
        json={"metricName": "pm25", "minValue": 50.0, "maxValue": 45.0},
    )
    assert response.status_code == 422


def test_feature_status_uses_seeded_value_without_threshold_override() -> None:
    response = client.get("/api/v1/features/station-001")
    assert response.status_code == 200
    assert response.json()["properties"]["status"] == "normal"


def test_threshold_update_feature_not_found() -> None:
    response = client.post(
        "/api/v1/stations/missing/thresholds",
        json={"metricName": "pm25", "maxValue": 45.0},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Feature not found"


def test_recent_observations() -> None:
    response = client.get("/api/v1/observations/recent", params={"limit": 3})
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["observations"]) == 3
    assert payload["summary"]["totalObservations"] == 3
    assert payload["summary"]["categories"]["air_quality"] == 2
    assert payload["summary"]["metrics"] == {"pm25": 2, "river_stage_ft": 1}
    assert payload["observations"][0]["observationId"] == "obs-2001"
    assert payload["observations"][0]["status"] == "alert"


def test_recent_observations_with_time_window() -> None:
    response = client.get(
        "/api/v1/observations/recent",
        params={"start_at": "2026-03-18T12:00:00Z", "end_at": "2026-03-18T12:05:00Z"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert [item["observationId"] for item in payload["observations"]] == ["obs-2001", "obs-1001"]
    assert payload["summary"]["latestObservedAt"] == "2026-03-18T12:05:00Z"
    assert payload["summary"]["earliestObservedAt"] == "2026-03-18T12:00:00Z"


def test_export_observations_json_bundle() -> None:
    response = client.get(
        "/api/v1/observations/export",
        params={
            "region": "West",
            "min_longitude": -123.0,
            "min_latitude": 37.0,
            "max_longitude": -120.0,
            "max_latitude": 40.0,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["source"]["name"] == "environmental-monitoring-api"
    assert payload["filters"]["region"] == "West"
    assert payload["filters"]["bbox"] == [-123.0, 37.0, -120.0, 40.0]
    assert [feature["properties"]["featureId"] for feature in payload["features"]["features"]] == ["station-002"]
    assert payload["observations"]["summary"]["totalObservations"] == 2
    assert payload["thresholds"] == [
        {
            "featureId": "station-002",
            "metricName": "pm25",
            "minValue": None,
            "maxValue": 35.0,
        }
    ]


def test_export_observations_csv() -> None:
    response = client.get(
        "/api/v1/observations/export",
        params={"format": "csv", "start_at": "2026-03-18T12:00:00Z"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    lines = response.text.strip().splitlines()
    assert lines[0] == "observation_id,feature_id,station_name,category,region,observed_at,metric_name,value,unit,status,min_threshold,max_threshold"
    assert any("obs-2001,station-002,Sierra Air Quality Node,air_quality,West,2026-03-18T12:05:00Z,pm25,41.8,ug/m3,alert,,35.0" == line for line in lines)


def test_feature_observations() -> None:
    response = client.get("/api/v1/features/station-001/observations", params={"limit": 2})
    assert response.status_code == 200
    payload = response.json()
    assert [item["observationId"] for item in payload["observations"]] == ["obs-1001", "obs-1002"]
    assert payload["summary"]["categories"] == {"hydrology": 2}
    assert payload["summary"]["statuses"] == {"normal": 2}
    assert payload["observations"][0]["metricName"] == "river_stage_ft"


def test_feature_observations_with_end_at() -> None:
    response = client.get(
        "/api/v1/features/station-003/observations",
        params={"end_at": "2026-03-17T21:00:00Z"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert [item["observationId"] for item in payload["observations"]] == ["obs-3002"]


def test_feature_observations_not_found() -> None:
    response = client.get("/api/v1/features/missing/observations")
    assert response.status_code == 404
    assert response.json()["detail"] == "Feature not found"


def test_get_feature_not_found() -> None:
    response = client.get("/api/v1/features/missing")
    assert response.status_code == 404
    assert response.json()["detail"] == "Feature not found"