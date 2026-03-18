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
    assert payload["name"] == "Spatial Data API"
    assert payload["backend"] == "file"
    assert payload["feature_count"] == 3
    assert payload["data_source"] == "sample_features.geojson"


def test_list_features_by_category() -> None:
    response = client.get("/api/v1/features", params={"category": "hydrology"})
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["features"]) == 1
    assert payload["features"][0]["properties"]["featureId"] == "asset-001"


def test_get_feature_not_found() -> None:
    response = client.get("/api/v1/features/missing")
    assert response.status_code == 404
    assert response.json()["detail"] == "Feature not found"