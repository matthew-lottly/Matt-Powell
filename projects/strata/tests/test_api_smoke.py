from __future__ import annotations

import pytest


def test_api_factory_exposes_health_and_datasets() -> None:
    pytest.importorskip("fastapi")

    from fastapi.testclient import TestClient

    from hetero_conformal.api import create_app

    client = TestClient(create_app())

    health_response = client.get("/health")
    datasets_response = client.get("/datasets")

    assert health_response.status_code == 200
    assert health_response.json() == {"status": "ok"}
    assert datasets_response.status_code == 200
    assert "synthetic" in datasets_response.json()["datasets"]
