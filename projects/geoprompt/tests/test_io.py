"""IO tests for read, write, and format operations."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from geoprompt import GeoPromptFrame
from geoprompt.io import (
    _read_json,
    frame_to_geojson,
    read_features,
    read_geojson,
    read_points,
    write_geojson,
    write_json,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class TestReadJson:
    def test_read_valid_json(self, tmp_path: Path) -> None:
        path = tmp_path / "test.json"
        path.write_text('{"key": "value"}', encoding="utf-8")
        result = _read_json(path)
        assert result == {"key": "value"}


class TestReadFeatures:
    def test_sample_features(self) -> None:
        frame = read_features(PROJECT_ROOT / "data" / "sample_features.json")
        assert len(frame) == 6

    def test_with_crs(self) -> None:
        frame = read_features(PROJECT_ROOT / "data" / "sample_features.json", crs="EPSG:4326")
        assert frame.crs == "EPSG:4326"


class TestReadPoints:
    def test_sample_points(self) -> None:
        frame = read_points(PROJECT_ROOT / "data" / "sample_points.json")
        assert len(frame) == 5

    def test_mixed_geometry_raises(self) -> None:
        with pytest.raises(TypeError, match="point geometry"):
            read_points(PROJECT_ROOT / "data" / "sample_features.json")


class TestReadGeoJSON:
    def test_feature_collection(self, tmp_path: Path) -> None:
        payload = {
            "type": "FeatureCollection",
            "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
            "features": [
                {
                    "type": "Feature",
                    "id": "a",
                    "properties": {"name": "A"},
                    "geometry": {"type": "Point", "coordinates": [0.0, 0.0]},
                }
            ],
        }
        path = tmp_path / "test.geojson"
        path.write_text(json.dumps(payload), encoding="utf-8")
        frame = read_geojson(path)
        assert len(frame) == 1
        assert frame.crs == "EPSG:4326"


class TestWriteJson:
    def test_write_creates_file(self, tmp_path: Path) -> None:
        path = write_json(tmp_path / "output.json", {"key": "value"})
        assert path.exists()
        assert json.loads(path.read_text(encoding="utf-8")) == {"key": "value"}

    def test_write_creates_parents(self, tmp_path: Path) -> None:
        path = write_json(tmp_path / "sub" / "dir" / "output.json", {"nested": True})
        assert path.exists()


class TestWriteGeoJSON:
    def test_round_trip(self, tmp_path: Path) -> None:
        frame = read_features(PROJECT_ROOT / "data" / "sample_features.json", crs="EPSG:4326")
        path = write_geojson(tmp_path / "output.geojson", frame)
        assert path.exists()
        reloaded = read_geojson(path)
        assert len(reloaded) == len(frame)


class TestFrameToGeoJSON:
    def test_feature_collection_structure(self) -> None:
        frame = read_features(PROJECT_ROOT / "data" / "sample_features.json", crs="EPSG:4326")
        collection = frame_to_geojson(frame)
        assert collection["type"] == "FeatureCollection"
        assert len(collection["features"]) == len(frame)
        assert collection["crs"]["properties"]["name"] == "EPSG:4326"
