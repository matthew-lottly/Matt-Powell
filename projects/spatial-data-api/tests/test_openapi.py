"""Pyright import resolution in the parent workspace does not model this nested src layout."""

# pyright: reportMissingImports=false

from fastapi.testclient import TestClient

from spatial_data_api.main import app


client = TestClient(app)


def test_openapi_schema_exposes_docs_and_summary_routes() -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    payload = response.json()
    assert "/health" in payload["paths"]
    assert "/api/v1/summary" in payload["paths"]
