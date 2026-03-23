"""Tests for extended I/O methods: read_file, to_file, read_fgdb,
to_geopackage, read_raster, to_raster, read_excel, read_csv_xy,
to_csv_wkt, to_kml, list_layers, raster_stats.
"""

from __future__ import annotations

import json
import math
import os
import tempfile

import pytest

from geoprompt import GeoPromptFrame


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sample_frame(n: int = 5) -> GeoPromptFrame:
    records = [
        {"geometry": {"type": "Point", "coordinates": (float(i), float(i * 2))}, "site_id": f"s{i}", "value": float(i * 10)}
        for i in range(n)
    ]
    return GeoPromptFrame.from_records(records, geometry="geometry", crs="EPSG:4326")


def _write_geojson(path: str, frame: GeoPromptFrame | None = None) -> None:
    frame = frame or _sample_frame()
    features = []
    for row in frame.to_records():
        geom = row.get("geometry")
        props = {k: v for k, v in row.items() if k != "geometry"}
        features.append({"type": "Feature", "geometry": geom, "properties": props})
    fc = {"type": "FeatureCollection", "features": features}
    with open(path, "w") as f:
        json.dump(fc, f)


def _write_ndjson(path: str, frame: GeoPromptFrame | None = None) -> None:
    frame = frame or _sample_frame()
    with open(path, "w") as f:
        for row in frame.to_records():
            geom = row.get("geometry")
            props = {k: v for k, v in row.items() if k != "geometry"}
            feat = {"type": "Feature", "geometry": geom, "properties": props}
            f.write(json.dumps(feat) + "\n")


def _write_csv_wkt(path: str) -> None:
    with open(path, "w") as f:
        f.write("wkt,name,value\n")
        f.write("POINT (1 2),A,10\n")
        f.write("POINT (3 4),B,20\n")


def _write_csv_xy(path: str) -> None:
    with open(path, "w") as f:
        f.write("x,y,name,value\n")
        f.write("1.0,2.0,A,10\n")
        f.write("3.0,4.0,B,20\n")


def _write_asc_grid(path: str) -> None:
    with open(path, "w") as f:
        f.write("ncols 3\n")
        f.write("nrows 3\n")
        f.write("xllcorner 0\n")
        f.write("yllcorner 0\n")
        f.write("cellsize 1\n")
        f.write("nodata_value -9999\n")
        f.write("10 20 30\n")
        f.write("40 -9999 60\n")
        f.write("70 80 90\n")


# ---------------------------------------------------------------------------
# read_file dispatcher
# ---------------------------------------------------------------------------

class TestReadFile:
    def test_read_geojson(self, tmp_path):
        p = str(tmp_path / "data.geojson")
        _write_geojson(p)
        frame = GeoPromptFrame.read_file(p)
        assert len(frame) == 5

    def test_read_json(self, tmp_path):
        p = str(tmp_path / "data.json")
        _write_geojson(p)
        frame = GeoPromptFrame.read_file(p)
        assert len(frame) == 5

    def test_read_ndjson(self, tmp_path):
        p = str(tmp_path / "data.ndjson")
        _write_ndjson(p)
        frame = GeoPromptFrame.read_file(p)
        assert len(frame) == 5

    def test_read_csv(self, tmp_path):
        p = str(tmp_path / "data.csv")
        _write_csv_wkt(p)
        frame = GeoPromptFrame.read_file(p)
        assert len(frame) == 2

    def test_read_asc_raster(self, tmp_path):
        p = str(tmp_path / "elev.asc")
        _write_asc_grid(p)
        frame = GeoPromptFrame.read_file(p)
        # 9 cells minus 1 nodata = 8
        assert len(frame) == 8

    def test_unsupported_extension(self, tmp_path):
        p = str(tmp_path / "data.xyz123")
        with open(p, "w") as f:
            f.write("test")
        with pytest.raises(ValueError, match="Unsupported"):
            GeoPromptFrame.read_file(p)


# ---------------------------------------------------------------------------
# to_file dispatcher
# ---------------------------------------------------------------------------

class TestToFile:
    def test_to_geojson(self, tmp_path):
        p = str(tmp_path / "out.geojson")
        _sample_frame().to_file(p)
        assert os.path.exists(p)
        with open(p) as f:
            data = json.load(f)
        assert data["type"] == "FeatureCollection"
        assert len(data["features"]) == 5

    def test_to_csv(self, tmp_path):
        p = str(tmp_path / "out.csv")
        _sample_frame().to_file(p)
        assert os.path.exists(p)
        with open(p) as f:
            lines = f.readlines()
        assert len(lines) > 1

    def test_to_ndjson(self, tmp_path):
        p = str(tmp_path / "out.ndjson")
        _sample_frame().to_file(p)
        assert os.path.exists(p)
        with open(p) as f:
            lines = [l.strip() for l in f if l.strip()]
        assert len(lines) == 5

    def test_to_asc_raster(self, tmp_path):
        p = str(tmp_path / "out.asc")
        # read ASC then write it
        src = str(tmp_path / "in.asc")
        _write_asc_grid(src)
        frame = GeoPromptFrame.read_file(src)
        # Write with to_raster directly (to_file for .asc not in dispatch)
        frame.to_raster(p, value_column="value")
        assert os.path.exists(p)

    def test_unsupported_write(self, tmp_path):
        p = str(tmp_path / "out.xyz123")
        with pytest.raises(ValueError, match="Unsupported"):
            _sample_frame().to_file(p)


# ---------------------------------------------------------------------------
# read_csv_xy
# ---------------------------------------------------------------------------

class TestReadCsvXY:
    def test_basic(self, tmp_path):
        p = str(tmp_path / "pts.csv")
        _write_csv_xy(p)
        frame = GeoPromptFrame.read_csv_xy(p)
        assert len(frame) == 2
        row = frame.to_records()[0]
        geom = row["geometry"]
        assert geom["type"] == "Point"
        assert abs(geom["coordinates"][0] - 1.0) < 1e-6
        assert abs(geom["coordinates"][1] - 2.0) < 1e-6

    def test_custom_columns(self, tmp_path):
        p = str(tmp_path / "pts.csv")
        with open(p, "w") as f:
            f.write("lon,lat,name\n")
            f.write("10.0,20.0,Place\n")
        frame = GeoPromptFrame.read_csv_xy(p, x_column="lon", y_column="lat")
        assert len(frame) == 1

    def test_tab_delimited(self, tmp_path):
        p = str(tmp_path / "pts.csv")
        with open(p, "w") as f:
            f.write("x\ty\tname\n")
            f.write("5.0\t6.0\tSpot\n")
        frame = GeoPromptFrame.read_csv_xy(p, delimiter="\t")
        assert len(frame) == 1


# ---------------------------------------------------------------------------
# to_csv_wkt / round-trip
# ---------------------------------------------------------------------------

class TestToCsvWkt:
    def test_round_trip(self, tmp_path):
        p = str(tmp_path / "out.csv")
        original = _sample_frame(3)
        original.to_csv_wkt(p)
        reloaded = GeoPromptFrame.read_csv_wkt(p)
        assert len(reloaded) == 3
        row = reloaded.to_records()[0]
        geom = row["geometry"]
        assert geom["type"] == "Point"


# ---------------------------------------------------------------------------
# to_kml / read_kml round-trip
# ---------------------------------------------------------------------------

class TestKmlRoundTrip:
    def test_point_round_trip(self, tmp_path):
        p = str(tmp_path / "out.kml")
        original = _sample_frame(3)
        original.to_kml(p, name_column="site_id")
        reloaded = GeoPromptFrame.read_kml(p)
        assert len(reloaded) == 3

    def test_polygon_kml(self, tmp_path):
        records = [{
            "geometry": {
                "type": "Polygon",
                "coordinates": [[(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]],
            },
            "name": "box",
        }]
        frame = GeoPromptFrame.from_records(records, geometry="geometry")
        p = str(tmp_path / "poly.kml")
        frame.to_kml(p, name_column="name")
        reloaded = GeoPromptFrame.read_kml(p)
        assert len(reloaded) == 1


# ---------------------------------------------------------------------------
# ASCII Grid raster read/write
# ---------------------------------------------------------------------------

class TestAscGrid:
    def test_read(self, tmp_path):
        p = str(tmp_path / "grid.asc")
        _write_asc_grid(p)
        frame = GeoPromptFrame.read_raster(p)
        assert len(frame) == 8  # 9 cells - 1 nodata
        vals = sorted(float(r["value"]) for r in frame.to_records())
        assert 10.0 in vals
        assert 90.0 in vals

    def test_sample_step(self, tmp_path):
        p = str(tmp_path / "grid.asc")
        _write_asc_grid(p)
        frame = GeoPromptFrame.read_raster(p, sample_step=2)
        # With step=2 on 3x3 grid: rows 0,2; cols 0,2 → 4 cells, minus any nodata
        # row0: 10, 30; row2: 70, 90 → 4 cells (nodata at row1 skipped)
        assert len(frame) == 4

    def test_write_asc(self, tmp_path):
        src = str(tmp_path / "in.asc")
        _write_asc_grid(src)
        frame = GeoPromptFrame.read_raster(src)

        out = str(tmp_path / "out.asc")
        frame.to_raster(out, value_column="value")
        assert os.path.exists(out)

        # Verify it's a valid ASC file
        with open(out) as f:
            lines = f.readlines()
        assert lines[0].strip().startswith("ncols")

    def test_nodata_include(self, tmp_path):
        p = str(tmp_path / "grid.asc")
        _write_asc_grid(p)
        frame = GeoPromptFrame.read_raster(p, nodata_skip=False)
        assert len(frame) == 9  # All cells including nodata


# ---------------------------------------------------------------------------
# read_file / to_file GeoJSON round-trip
# ---------------------------------------------------------------------------

class TestGeoJsonRoundTrip:
    def test_round_trip(self, tmp_path):
        original = _sample_frame(4)
        p = str(tmp_path / "data.geojson")
        original.to_file(p)
        reloaded = GeoPromptFrame.read_file(p)
        assert len(reloaded) == 4


# ---------------------------------------------------------------------------
# LineString + Polygon in to_kml
# ---------------------------------------------------------------------------

class TestKmlLineString:
    def test_linestring(self, tmp_path):
        records = [{
            "geometry": {"type": "LineString", "coordinates": [(0, 0), (1, 1), (2, 0)]},
            "name": "river",
        }]
        frame = GeoPromptFrame.from_records(records, geometry="geometry")
        p = str(tmp_path / "line.kml")
        frame.to_kml(p, name_column="name")
        reloaded = GeoPromptFrame.read_kml(p)
        assert len(reloaded) == 1
        assert reloaded.to_records()[0]["geometry"]["type"] == "LineString"


# ---------------------------------------------------------------------------
# list_layers with GeoPackage (sqlite3 fallback)
# ---------------------------------------------------------------------------

class TestListLayers:
    def test_gpkg_sqlite3_fallback(self, tmp_path):
        """Create a minimal GeoPackage via sqlite3 and list its layers."""
        import sqlite3
        gpkg = str(tmp_path / "test.gpkg")
        conn = sqlite3.connect(gpkg)
        conn.execute("CREATE TABLE gpkg_contents (table_name TEXT, data_type TEXT, identifier TEXT)")
        conn.execute("INSERT INTO gpkg_contents VALUES ('rivers', 'features', 'rivers')")
        conn.execute("INSERT INTO gpkg_contents VALUES ('cities', 'features', 'cities')")
        conn.commit()
        conn.close()
        layers = GeoPromptFrame.list_layers(gpkg)
        assert "rivers" in layers
        assert "cities" in layers


# ---------------------------------------------------------------------------
# read_file with NDJSON variants
# ---------------------------------------------------------------------------

class TestNdjsonVariants:
    def test_geojsonl(self, tmp_path):
        p = str(tmp_path / "data.geojsonl")
        _write_ndjson(p)
        frame = GeoPromptFrame.read_file(p)
        assert len(frame) == 5

    def test_jsonl(self, tmp_path):
        p = str(tmp_path / "data.jsonl")
        _write_ndjson(p)
        frame = GeoPromptFrame.read_file(p)
        assert len(frame) == 5
