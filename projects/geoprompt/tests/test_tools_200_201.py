"""Tests for tools 200-201: GeoParquet and FlatGeobuf I/O."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

import geoprompt.frame as frame_module
from geoprompt import GeoPromptFrame


def _sample_frame() -> GeoPromptFrame:
    return GeoPromptFrame.from_records([
        {"site_id": "A", "value": 1.0, "geometry": {"type": "Point", "coordinates": (0, 0)}},
        {"site_id": "B", "value": 2.0, "geometry": {"type": "Point", "coordinates": (1, 1)}},
    ], crs="EPSG:4326")


class _FakeGeoDataFrame:
    def __init__(self, rows, geometry_name="geometry", crs="EPSG:4326"):
        self._rows = list(rows)
        self.geometry = SimpleNamespace(name=geometry_name)
        self.crs = crs

    def iterrows(self):
        for idx, row in enumerate(self._rows):
            yield idx, row


class TestGeoParquetIO:
    def test_read_geoparquet_exists(self):
        assert hasattr(GeoPromptFrame, "read_geoparquet")
        assert hasattr(GeoPromptFrame, "to_geoparquet")

    def test_read_geoparquet_with_fake_backend(self, monkeypatch):
        fake_rows = [
            {"site_id": "A", "value": 1.0, "geometry": {"type": "Point", "coordinates": (0, 0)}},
            {"site_id": "B", "value": 2.0, "geometry": {"type": "Point", "coordinates": (1, 1)}},
        ]
        fake_gpd = SimpleNamespace(read_parquet=lambda path: _FakeGeoDataFrame(fake_rows, crs="EPSG:3857"))
        monkeypatch.setattr(frame_module, "geometry_from_shapely", lambda geom: geom)
        monkeypatch.setitem(__import__("sys").modules, "geopandas", fake_gpd)
        frame = GeoPromptFrame.read_geoparquet("sample.parquet")
        recs = frame.to_records()
        assert len(recs) == 2
        assert recs[0]["site_id"] == "A"
        assert frame.crs == "EPSG:3857"

    def test_to_geoparquet_with_fake_backend(self, monkeypatch):
        calls = {}

        class FakeWriterGeoDataFrame:
            def __init__(self, rows, geometry="geometry", crs=None):
                calls["rows"] = rows
                calls["geometry"] = geometry
                calls["crs"] = crs

            def to_parquet(self, path):
                calls["path"] = path

        fake_gpd = SimpleNamespace(GeoDataFrame=FakeWriterGeoDataFrame)
        monkeypatch.setitem(__import__("sys").modules, "geopandas", fake_gpd)
        monkeypatch.setattr("geoprompt.overlay.geometry_to_shapely", lambda geom: geom)
        _sample_frame().to_geoparquet("output.parquet")
        assert calls["path"] == "output.parquet"
        assert calls["crs"] == "EPSG:4326"
        assert len(calls["rows"]) == 2


class TestFlatGeobufIO:
    def test_read_flatgeobuf_exists(self):
        assert hasattr(GeoPromptFrame, "read_flatgeobuf")
        assert hasattr(GeoPromptFrame, "to_flatgeobuf")

    def test_read_flatgeobuf_with_fake_backend(self, monkeypatch):
        fake_rows = [
            {"site_id": "A", "geometry": {"type": "Point", "coordinates": (0, 0)}},
        ]
        fake_gpd = SimpleNamespace(read_file=lambda path: _FakeGeoDataFrame(fake_rows, crs="EPSG:4326"))
        monkeypatch.setattr(frame_module, "geometry_from_shapely", lambda geom: geom)
        monkeypatch.setitem(__import__("sys").modules, "geopandas", fake_gpd)
        frame = GeoPromptFrame.read_flatgeobuf("sample.fgb")
        recs = frame.to_records()
        assert len(recs) == 1
        assert recs[0]["site_id"] == "A"

    def test_to_flatgeobuf_with_fake_backend(self, monkeypatch):
        calls = {}

        class FakeWriterGeoDataFrame:
            def __init__(self, rows, geometry="geometry", crs=None):
                calls["rows"] = rows
                calls["geometry"] = geometry
                calls["crs"] = crs

            def to_file(self, path, driver=None):
                calls["path"] = path
                calls["driver"] = driver

        fake_gpd = SimpleNamespace(GeoDataFrame=FakeWriterGeoDataFrame)
        monkeypatch.setitem(__import__("sys").modules, "geopandas", fake_gpd)
        monkeypatch.setattr("geoprompt.overlay.geometry_to_shapely", lambda geom: geom)
        _sample_frame().to_flatgeobuf("output.fgb")
        assert calls["path"] == "output.fgb"
        assert calls["driver"] == "FlatGeobuf"

    def test_import_errors_when_geopandas_missing(self, monkeypatch):
        monkeypatch.delitem(__import__("sys").modules, "geopandas", raising=False)
        original_import = __import__("builtins").__dict__["__import__"]

        def _failing_import(name, *args, **kwargs):
            if name == "geopandas":
                raise ImportError("missing geopandas")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", _failing_import)
        with pytest.raises(ImportError):
            GeoPromptFrame.read_geoparquet("missing.parquet")
        with pytest.raises(ImportError):
            GeoPromptFrame.read_flatgeobuf("missing.fgb")