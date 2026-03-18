from datetime import datetime, timezone

import os

import pytest

from spatial_data_api.repository import PostGISFeatureRepository


pytestmark = pytest.mark.skipif(
    os.getenv("SPATIAL_DATA_API_RUN_DB_TESTS") != "1",
    reason="Set SPATIAL_DATA_API_RUN_DB_TESTS=1 to run PostGIS integration tests.",
)


def test_postgis_repository_summary() -> None:
    database_url = os.getenv(
        "SPATIAL_DATA_API_INTEGRATION_DB_URL",
        "postgresql+psycopg://spatial:spatial@localhost:5432/spatial",
    )
    repository = PostGISFeatureRepository(database_url)

    assert repository.is_ready() is True

    summary = repository.summary()
    assert summary.total_features == 3
    assert summary.categories["hydrology"] == 1
    assert summary.statuses["alert"] == 1
    assert "West" in summary.regions


def test_postgis_repository_feature_lookup() -> None:
    database_url = os.getenv(
        "SPATIAL_DATA_API_INTEGRATION_DB_URL",
        "postgresql+psycopg://spatial:spatial@localhost:5432/spatial",
    )
    repository = PostGISFeatureRepository(database_url)

    feature = repository.get_feature("station-002")
    assert feature is not None
    assert feature.properties.name == "Sierra Air Quality Node"
    assert feature.properties.region == "West"
    assert feature.properties.status == "alert"


def test_postgis_repository_recent_observations() -> None:
    database_url = os.getenv(
        "SPATIAL_DATA_API_INTEGRATION_DB_URL",
        "postgresql+psycopg://spatial:spatial@localhost:5432/spatial",
    )
    repository = PostGISFeatureRepository(database_url)

    observations = repository.list_recent_observations(limit=2)
    assert len(observations) == 2
    assert observations[0].observation_id == "obs-2001"
    assert observations[0].status == "alert"


def test_postgis_repository_recent_observations_with_window() -> None:
    database_url = os.getenv(
        "SPATIAL_DATA_API_INTEGRATION_DB_URL",
        "postgresql+psycopg://spatial:spatial@localhost:5432/spatial",
    )
    repository = PostGISFeatureRepository(database_url)

    observations = repository.list_recent_observations(
        start_at=datetime(2026, 3, 18, 12, 0, tzinfo=timezone.utc),
        end_at=datetime(2026, 3, 18, 12, 5, tzinfo=timezone.utc),
    )
    assert [observation.observation_id for observation in observations] == ["obs-2001", "obs-1001"]


def test_postgis_repository_feature_observations() -> None:
    database_url = os.getenv(
        "SPATIAL_DATA_API_INTEGRATION_DB_URL",
        "postgresql+psycopg://spatial:spatial@localhost:5432/spatial",
    )
    repository = PostGISFeatureRepository(database_url)

    observations = repository.list_feature_observations("station-001", limit=5)
    assert len(observations) == 2
    assert observations[0].metric_name == "river_stage_ft"
    assert observations[1].observation_id == "obs-1002"