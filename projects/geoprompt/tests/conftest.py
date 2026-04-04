"""Shared test fixtures for geoprompt test suite."""

from __future__ import annotations

from pathlib import Path

import pytest

from geoprompt import GeoPromptFrame
from geoprompt.io import read_features, read_points


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"


@pytest.fixture
def sample_points_frame() -> GeoPromptFrame:
    return read_points(DATA_DIR / "sample_points.json")


@pytest.fixture
def sample_features_frame() -> GeoPromptFrame:
    return read_features(DATA_DIR / "sample_features.json", crs="EPSG:4326")


@pytest.fixture
def benchmark_features_frame() -> GeoPromptFrame:
    return read_features(DATA_DIR / "benchmark_features.json", crs="EPSG:4326")


@pytest.fixture
def benchmark_regions_frame() -> GeoPromptFrame:
    return read_features(DATA_DIR / "benchmark_regions.json", crs="EPSG:4326")


@pytest.fixture
def simple_points_frame() -> GeoPromptFrame:
    return GeoPromptFrame.from_records([
        {"site_id": "a", "value": 1.0, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
        {"site_id": "b", "value": 2.0, "geometry": {"type": "Point", "coordinates": [1.0, 0.0]}},
        {"site_id": "c", "value": 3.0, "geometry": {"type": "Point", "coordinates": [0.0, 1.0]}},
    ], crs="EPSG:4326")


@pytest.fixture
def mixed_geometry_frame() -> GeoPromptFrame:
    return GeoPromptFrame.from_records([
        {"site_id": "point-a", "value": 1.0, "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
        {"site_id": "line-a", "value": 2.0, "geometry": {"type": "LineString", "coordinates": [[0.0, 0.0], [1.0, 1.0]]}},
        {"site_id": "poly-a", "value": 3.0, "geometry": {"type": "Polygon", "coordinates": [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]]}},
    ], crs="EPSG:4326")


@pytest.fixture
def malformed_records() -> list[dict]:
    return [
        {"site_id": "bad-1", "geometry": None},
        {"site_id": "bad-2", "geometry": {"type": "Unknown", "coordinates": [0, 0]}},
        {"site_id": "bad-3", "geometry": {"type": "Point"}},
        {"site_id": "bad-4", "geometry": {"type": "Point", "coordinates": []}},
        {"site_id": "bad-5", "geometry": {"type": "LineString", "coordinates": [[0, 0]]}},
    ]
