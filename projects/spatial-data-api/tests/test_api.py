from fastapi.testclient import TestClient

from spatial_data_api.main import app


client = TestClient(app)


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


def test_feature_summary() -> None:
    response = client.get("/api/v1/features/summary")
    assert response.status_code == 200
    payload = response.json()
    assert payload["statuses"]["alert"] == 1
    assert payload["categories"]["water_quality"] == 1


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