"""Startup and health-check validation tests."""

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


# --- Health and readiness ---


def test_health_returns_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["ready"] is True
    assert "backend" in payload
    assert "data_source" in payload


def test_readiness_returns_ok() -> None:
    response = client.get("/health/ready")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["ready"] is True


def test_health_and_readiness_agree() -> None:
    health = client.get("/health").json()
    ready = client.get("/health/ready").json()
    assert health["ready"] == ready["ready"]


# --- Startup validation ---


def test_root_endpoint_lists_routes() -> None:
    response = client.get("/")
    assert response.status_code == 200
    payload = response.json()
    assert "dashboard" in payload


def test_metadata_returns_expected_shape() -> None:
    response = client.get("/api/v1/metadata")
    assert response.status_code == 200
    payload = response.json()
    required_keys = {"name", "version", "environment", "backend", "feature_count", "data_source"}
    assert required_keys.issubset(payload.keys())
    assert payload["feature_count"] > 0


def test_openapi_schema_available_on_startup() -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "paths" in schema
    assert "/health" in schema["paths"]


def test_swagger_ui_available() -> None:
    response = client.get("/docs")
    assert response.status_code == 200
    assert "swagger" in response.text.lower() or "openapi" in response.text.lower()


def test_dashboard_renders() -> None:
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "html" in response.headers.get("content-type", "").lower() or len(response.text) > 100


# --- Feature availability after startup ---


def test_features_available_after_startup() -> None:
    response = client.get("/api/v1/features")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["features"]) > 0


def test_summary_available_after_startup() -> None:
    response = client.get("/api/v1/summary")
    assert response.status_code == 200
    payload = response.json()
    assert payload["totalFeatures"] > 0


def test_feature_summary_matches_metadata_count() -> None:
    metadata = client.get("/api/v1/metadata").json()
    summary = client.get("/api/v1/features/summary").json()
    assert summary["total_features"] == metadata["feature_count"]
