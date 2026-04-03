"""Tests for invalid queries and edge-case input validation."""

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


# --- Feature listing validation ---


def test_unknown_category_returns_empty() -> None:
    response = client.get("/api/v1/features", params={"category": "nonexistent"})
    assert response.status_code == 200
    assert response.json()["features"] == []


def test_unknown_status_returns_empty() -> None:
    response = client.get("/api/v1/features", params={"status": "unknown_status"})
    assert response.status_code == 200
    assert response.json()["features"] == []


def test_unknown_region_returns_empty() -> None:
    response = client.get("/api/v1/features", params={"region": "Antarctica"})
    assert response.status_code == 200
    assert response.json()["features"] == []


def test_bounding_box_with_two_params_rejected() -> None:
    response = client.get(
        "/api/v1/features",
        params={"min_longitude": -123.0, "min_latitude": 37.0},
    )
    assert response.status_code == 422


def test_bounding_box_with_three_params_rejected() -> None:
    response = client.get(
        "/api/v1/features",
        params={
            "min_longitude": -123.0,
            "min_latitude": 37.0,
            "max_longitude": -120.0,
        },
    )
    assert response.status_code == 422


def test_bounding_box_no_matches() -> None:
    response = client.get(
        "/api/v1/features",
        params={
            "min_longitude": 0.0,
            "min_latitude": 0.0,
            "max_longitude": 1.0,
            "max_latitude": 1.0,
        },
    )
    assert response.status_code == 200
    assert response.json()["features"] == []


# --- Single feature validation ---


def test_get_missing_feature() -> None:
    response = client.get("/api/v1/features/does-not-exist")
    assert response.status_code == 404
    assert "detail" in response.json()


# --- Observation validation ---


def test_observations_for_missing_feature() -> None:
    response = client.get("/api/v1/features/does-not-exist/observations")
    assert response.status_code == 404


def test_recent_observations_zero_limit() -> None:
    response = client.get("/api/v1/observations/recent", params={"limit": 0})
    assert response.status_code == 200
    payload = response.json()
    assert payload["observations"] == []


def test_recent_observations_negative_limit() -> None:
    response = client.get("/api/v1/observations/recent", params={"limit": -1})
    assert response.status_code in (200, 422)


def test_observations_time_window_no_matches() -> None:
    response = client.get(
        "/api/v1/observations/recent",
        params={"start_at": "2020-01-01T00:00:00Z", "end_at": "2020-01-02T00:00:00Z"},
    )
    assert response.status_code == 200
    assert response.json()["observations"] == []


# --- Threshold validation ---


def test_threshold_missing_feature() -> None:
    response = client.post(
        "/api/v1/stations/nonexistent/thresholds",
        json={"metricName": "pm25", "maxValue": 45.0},
    )
    assert response.status_code == 404


def test_threshold_no_bounds() -> None:
    response = client.post(
        "/api/v1/stations/station-001/thresholds",
        json={"metricName": "pm25"},
    )
    assert response.status_code == 422


def test_threshold_inverted_bounds() -> None:
    response = client.post(
        "/api/v1/stations/station-001/thresholds",
        json={"metricName": "pm25", "minValue": 100.0, "maxValue": 10.0},
    )
    assert response.status_code == 422


def test_threshold_equal_bounds() -> None:
    response = client.post(
        "/api/v1/stations/station-001/thresholds",
        json={"metricName": "pm25", "minValue": 45.0, "maxValue": 45.0},
    )
    assert response.status_code == 422


def test_threshold_empty_body() -> None:
    response = client.post(
        "/api/v1/stations/station-001/thresholds",
        json={},
    )
    assert response.status_code == 422


# --- Export validation ---


def test_export_invalid_format() -> None:
    response = client.get(
        "/api/v1/observations/export",
        params={"format": "xml"},
    )
    assert response.status_code in (200, 422)


def test_export_empty_region() -> None:
    response = client.get(
        "/api/v1/observations/export",
        params={"region": "Nowhere"},
    )
    assert response.status_code == 200


# --- OpenAPI contract ---


def test_openapi_schema_available() -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "paths" in schema
    assert "info" in schema
