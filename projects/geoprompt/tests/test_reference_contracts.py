from __future__ import annotations

from pathlib import Path

import pytest

from geoprompt import GeoPromptFrame
from geoprompt.exceptions import CRSError
from geoprompt.io import read_features


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_sample_feature_bounds_contract() -> None:
    frame = read_features(PROJECT_ROOT / "data" / "sample_features.json", crs="EPSG:4326")
    bounds = frame.bounds()
    assert bounds.min_x == -112.09
    assert bounds.min_y == 40.55
    assert bounds.max_x == -111.74
    assert bounds.max_y == 40.78


def test_sample_feature_nearest_neighbor_contract() -> None:
    frame = read_features(PROJECT_ROOT / "data" / "sample_features.json", crs="EPSG:4326")
    pairs = [(row["origin"], row["neighbor"]) for row in frame.nearest_neighbors(k=1)]
    assert pairs == [
        ("north-hub-point", "central-yard-point"),
        ("central-yard-point", "central-service-zone"),
        ("west-corridor-line", "central-yard-point"),
        ("south-corridor-line", "central-service-zone"),
        ("east-service-zone", "south-corridor-line"),
        ("central-service-zone", "central-yard-point"),
    ]


def test_haversine_requires_geographic_crs_runtime_contract() -> None:
    frame = read_features(PROJECT_ROOT / "data" / "sample_features.json", crs="EPSG:3857")
    with pytest.raises(CRSError, match="EPSG:4326"):
        frame.nearest_neighbors(k=1, distance_method="haversine")


def test_haversine_requires_crs_set_runtime_contract() -> None:
    frame = GeoPromptFrame.from_records(
        [
            {"site_id": "a", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
            {"site_id": "b", "geometry": {"type": "Point", "coordinates": [1.0, 1.0]}},
        ]
    )
    with pytest.raises(CRSError, match="requires CRS"):
        frame.distance_matrix(distance_method="haversine")