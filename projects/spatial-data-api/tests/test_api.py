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


def test_get_feature_not_found() -> None:
    response = client.get("/api/v1/features/missing")
    assert response.status_code == 404
    assert response.json()["detail"] == "Feature not found"