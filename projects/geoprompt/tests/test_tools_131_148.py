"""Tests for tools 131-148."""
from __future__ import annotations

import math
import os
import tempfile

import pytest
from geoprompt import GeoPromptFrame


def _point_frame(coords: list[tuple[float, float]], values: list[float] | None = None, **extra_cols: list) -> GeoPromptFrame:
    rows = []
    for i, (x, y) in enumerate(coords):
        row: dict = {"site_id": f"p{i}", "geometry": {"type": "Point", "coordinates": (x, y)}}
        if values is not None:
            row["value"] = values[i]
        for col_name, col_vals in extra_cols.items():
            row[col_name] = col_vals[i]
        rows.append(row)
    return GeoPromptFrame.from_records(rows)


def _grid_points(n: int = 25) -> list[tuple[float, float]]:
    side = int(math.sqrt(n))
    return [(float(x), float(y)) for y in range(side) for x in range(side)]


# ---- Tool 131: co_kriging ----
class TestCoKriging:
    def test_produces_grid(self):
        pts = _grid_points(25)
        primary = [float(i) for i in range(25)]
        secondary = [float(i * 0.5 + 1) for i in range(25)]
        rows = [{"site_id": f"p{i}", "geometry": {"type": "Point", "coordinates": pts[i]},
                 "primary": primary[i], "secondary": secondary[i]} for i in range(25)]
        frame = GeoPromptFrame.from_records(rows)
        result = frame.co_kriging("primary", "secondary", grid_resolution=5)
        recs = result.to_records()
        assert len(recs) == 25  # 5x5 grid
        assert "value_cok" in recs[0]

    def test_empty_frame(self):
        frame = GeoPromptFrame.from_records([])
        with pytest.raises(KeyError):
            frame.co_kriging("primary", "secondary")


# ---- Tool 132: empirical_bayesian_kriging ----
class TestEmpiricalBayesianKriging:
    def test_produces_grid(self):
        pts = _grid_points(25)
        vals = [float(i) for i in range(25)]
        frame = _point_frame(pts, vals)
        result = frame.empirical_bayesian_kriging("value", grid_resolution=5, n_subsets=3)
        recs = result.to_records()
        assert len(recs) == 25
        assert "value_ebk" in recs[0]
        assert "n_models_ebk" in recs[0]

    def test_too_few_points(self):
        frame = _point_frame([(0, 0), (1, 1)], [1.0, 2.0])
        result = frame.empirical_bayesian_kriging("value")
        assert len(result) == 2  # returns input unchanged


# ---- Tool 133: anisotropic_idw ----
class TestAnisotropicIdw:
    def test_produces_grid(self):
        pts = _grid_points(16)
        vals = [float(i) for i in range(16)]
        frame = _point_frame(pts, vals)
        result = frame.anisotropic_idw("value", grid_resolution=4, angle=45.0, ratio=2.0)
        recs = result.to_records()
        assert len(recs) == 16
        assert "value_aidw" in recs[0]

    def test_empty_frame(self):
        frame = GeoPromptFrame.from_records([])
        with pytest.raises(KeyError):
            frame.anisotropic_idw("value")


# ---- Tool 134: som_spatial ----
class TestSomSpatial:
    def test_assigns_clusters(self):
        pts = _grid_points(25)
        vals = [float(i) for i in range(25)]
        frame = _point_frame(pts, vals)
        result = frame.som_spatial(feature_columns=["value"], grid_rows=2, grid_cols=2, n_iterations=50)
        recs = result.to_records()
        assert len(recs) == 25
        assert "cluster_som" in recs[0]
        assert "bmu_row_som" in recs[0]
        assert "bmu_col_som" in recs[0]
        clusters = {r["cluster_som"] for r in recs}
        assert len(clusters) >= 2

    def test_without_feature_columns(self):
        pts = [(0.0, 0.0), (10.0, 10.0), (0.0, 10.0), (10.0, 0.0)]
        frame = _point_frame(pts)
        result = frame.som_spatial(grid_rows=2, grid_cols=2, n_iterations=50)
        assert len(result) == 4
        assert "cluster_som" in result.to_records()[0]


# ---- Tool 135: mgwr ----
class TestMgwr:
    def test_produces_coefficients(self):
        pts = _grid_points(25)
        rows = [{"site_id": f"p{i}", "geometry": {"type": "Point", "coordinates": pts[i]},
                 "y": float(i) * 2 + 1, "x1": float(i), "x2": float(i % 5)}
                for i in range(25)]
        frame = GeoPromptFrame.from_records(rows)
        result = frame.mgwr("y", ["x1", "x2"])
        recs = result.to_records()
        assert len(recs) == 25
        assert "predicted_mgwr" in recs[0]
        assert "residual_mgwr" in recs[0]
        assert "r_squared_mgwr" in recs[0]
        assert "coeff_intercept_mgwr" in recs[0]
        assert "coeff_x1_mgwr" in recs[0]

    def test_too_few_points(self):
        frame = _point_frame([(0, 0), (1, 1)], [1.0, 2.0])
        rows = [{"site_id": "p0", "geometry": {"type": "Point", "coordinates": (0, 0)},
                 "y": 1.0, "x1": 0.0}]
        frame = GeoPromptFrame.from_records(rows)
        result = frame.mgwr("y", ["x1"])
        assert len(result) == 1  # returns input unchanged


# ---- Tool 136: gwr_poisson ----
class TestGwrPoisson:
    def test_produces_predictions(self):
        pts = _grid_points(25)
        rows = [{"site_id": f"p{i}", "geometry": {"type": "Point", "coordinates": pts[i]},
                 "count": float(i % 5 + 1), "x1": float(i)}
                for i in range(25)]
        frame = GeoPromptFrame.from_records(rows)
        result = frame.gwr_poisson("count", ["x1"], max_iter=5)
        recs = result.to_records()
        assert len(recs) == 25
        assert "predicted_gwrp" in recs[0]
        assert "residual_gwrp" in recs[0]
        assert "coeff_intercept_gwrp" in recs[0]
        # predictions should be positive (Poisson link)
        assert all(r["predicted_gwrp"] > 0 for r in recs)


# ---- Tool 137: spacetime_morans_i ----
class TestSpacetimeMoransI:
    def test_returns_time_slices(self):
        rows = []
        for t in [1, 2, 3]:
            for i in range(10):
                rows.append({
                    "site_id": f"p{t}_{i}",
                    "geometry": {"type": "Point", "coordinates": (float(i), float(i % 3))},
                    "value": float(i * t),
                    "time": t,
                })
        frame = GeoPromptFrame.from_records(rows)
        result = frame.spacetime_morans_i("value", "time", k=3)
        assert "global_morans_i" in result
        assert "time_slices" in result
        assert len(result["time_slices"]) == 3
        for s in result["time_slices"]:
            assert "time" in s
            assert "morans_i" in s
            assert "n" in s

    def test_empty_frame(self):
        frame = GeoPromptFrame.from_records([])
        with pytest.raises(KeyError):
            frame.spacetime_morans_i("value", "time")


# ---- Tool 138: watershed_delineation ----
class TestWatershedDelineation:
    def test_assigns_watersheds(self):
        # Create a simple terrain: two peaks flowing to a valley
        pts = [(float(x), float(y)) for y in range(5) for x in range(5)]
        elevations = []
        for y in range(5):
            for x in range(5):
                # Peak at (1,1) and (3,3), valley at (2,2)
                d1 = math.hypot(x - 1, y - 1)
                d2 = math.hypot(x - 3, y - 3)
                elevations.append(max(5 - d1, 5 - d2, 0.0))
        frame = _point_frame(pts, elevations)
        rows = [{"site_id": f"p{i}", "geometry": {"type": "Point", "coordinates": pts[i]},
                 "elevation": elevations[i]} for i in range(25)]
        frame = GeoPromptFrame.from_records(rows)
        result = frame.watershed_delineation("elevation", k=8)
        recs = result.to_records()
        assert len(recs) == 25
        assert "watershed_ws" in recs[0]

    def test_empty(self):
        frame = GeoPromptFrame.from_records([])
        with pytest.raises(KeyError):
            frame.watershed_delineation("elevation")


# ---- Tool 139: stream_ordering ----
class TestStreamOrdering:
    def test_strahler_and_shreve(self):
        # Linear downhill: elevation decreases along x
        pts = [(float(i), 0.0) for i in range(10)]
        rows = [{"site_id": f"p{i}", "geometry": {"type": "Point", "coordinates": pts[i]},
                 "elevation": 10.0 - i} for i in range(10)]
        frame = GeoPromptFrame.from_records(rows)
        result = frame.stream_ordering("elevation", k=2)
        recs = result.to_records()
        assert len(recs) == 10
        assert "strahler_stream" in recs[0]
        assert "shreve_stream" in recs[0]
        # All values should be >= 1
        assert all(r["strahler_stream"] >= 1 for r in recs)
        assert all(r["shreve_stream"] >= 1 for r in recs)


# ---- Tool 140: time_dependent_routing ----
class TestTimeDependentRouting:
    def test_finds_path(self):
        rows = [
            {"from_node": "A", "to_node": "B", "cost": 1.0, "time_factor": 0.1,
             "geometry": {"type": "Point", "coordinates": (0, 0)}},
            {"from_node": "B", "to_node": "C", "cost": 2.0, "time_factor": 0.2,
             "geometry": {"type": "Point", "coordinates": (1, 0)}},
            {"from_node": "A", "to_node": "C", "cost": 5.0, "time_factor": 0.1,
             "geometry": {"type": "Point", "coordinates": (2, 0)}},
        ]
        frame = GeoPromptFrame.from_records(rows)
        result = frame.time_dependent_routing("A", "C")
        assert result["path"] == ["A", "B", "C"]
        assert result["total_cost"] > 0

    def test_no_path(self):
        rows = [
            {"from_node": "A", "to_node": "B", "cost": 1.0, "time_factor": 0.1,
             "geometry": {"type": "Point", "coordinates": (0, 0)}},
        ]
        frame = GeoPromptFrame.from_records(rows)
        result = frame.time_dependent_routing("A", "Z")
        assert result["path"] == []
        assert result["total_cost"] == float("inf")

    def test_empty_frame(self):
        frame = GeoPromptFrame.from_records([])
        result = frame.time_dependent_routing("A", "B")
        assert result["path"] == []


# ---- Tool 141: cvrp ----
class TestCvrp:
    def test_assigns_routes(self):
        rows = [
            {"site_id": "depot", "geometry": {"type": "Point", "coordinates": (0, 0)}, "demand": 0.0},
            {"site_id": "c1", "geometry": {"type": "Point", "coordinates": (1, 0)}, "demand": 30.0},
            {"site_id": "c2", "geometry": {"type": "Point", "coordinates": (2, 0)}, "demand": 30.0},
            {"site_id": "c3", "geometry": {"type": "Point", "coordinates": (0, 2)}, "demand": 30.0},
            {"site_id": "c4", "geometry": {"type": "Point", "coordinates": (3, 3)}, "demand": 30.0},
        ]
        frame = GeoPromptFrame.from_records(rows)
        result = frame.cvrp("depot", "demand", capacity=60)
        recs = result.to_records()
        assert len(recs) == 5
        assert "route_cvrp" in recs[0]
        assert "sequence_cvrp" in recs[0]
        # With capacity 60, need at least 2 routes for demands totaling 120
        routes = {r["route_cvrp"] for r in recs}
        assert len(routes) >= 2


# ---- Tool 142: inhomogeneous_k ----
class TestInhomogeneousK:
    def test_returns_distances(self):
        pts = _grid_points(25)
        frame = _point_frame(pts)
        result = frame.inhomogeneous_k(n_distances=5)
        assert len(result) == 5
        assert "distance" in result[0]
        assert "k_inhom" in result[0]
        assert "l_inhom" in result[0]

    def test_too_few_points(self):
        frame = _point_frame([(0, 0)])
        result = frame.inhomogeneous_k()
        assert result == []


# ---- Tool 143: polygon_subdivision ----
class TestPolygonSubdivision:
    def test_subdivides_polygon(self):
        rows = [{"site_id": "p0", "geometry": {
            "type": "Polygon",
            "coordinates": [[(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]]
        }}]
        frame = GeoPromptFrame.from_records(rows)
        result = frame.polygon_subdivision(n_divisions=4)
        recs = result.to_records()
        assert len(recs) == 4
        assert "subdivision_sub" in recs[0]
        # Each should be a polygon
        for r in recs:
            assert r["geometry"]["type"] == "Polygon"

    def test_point_passthrough(self):
        rows = [{"site_id": "p0", "geometry": {"type": "Point", "coordinates": (5, 5)}}]
        frame = GeoPromptFrame.from_records(rows)
        result = frame.polygon_subdivision(n_divisions=4)
        recs = result.to_records()
        assert len(recs) == 1  # Point not subdivided
        assert recs[0]["subdivision_sub"] == 0


# ---- Tool 144: line_planarize ----
class TestLinePlanarize:
    def test_splits_at_intersection(self):
        rows = [
            {"site_id": "L1", "geometry": {
                "type": "LineString", "coordinates": [(0, 5), (10, 5)]
            }},
            {"site_id": "L2", "geometry": {
                "type": "LineString", "coordinates": [(5, 0), (5, 10)]
            }},
        ]
        frame = GeoPromptFrame.from_records(rows)
        result = frame.line_planarize()
        recs = result.to_records()
        # Two crossing lines → should produce 4 segments
        assert len(recs) == 4
        assert "segment_lp" in recs[0]
        assert "source_row_lp" in recs[0]

    def test_no_intersection(self):
        rows = [
            {"site_id": "L1", "geometry": {
                "type": "LineString", "coordinates": [(0, 0), (1, 0)]
            }},
            {"site_id": "L2", "geometry": {
                "type": "LineString", "coordinates": [(0, 5), (1, 5)]
            }},
        ]
        frame = GeoPromptFrame.from_records(rows)
        result = frame.line_planarize()
        recs = result.to_records()
        assert len(recs) == 2  # No split needed


# ---- Tool 148: to_topojson ----
class TestToTopojson:
    def test_point_topology(self):
        frame = _point_frame([(0, 0), (1, 1)])
        result = frame.to_topojson("test")
        assert result["type"] == "Topology"
        assert "test" in result["objects"]
        geoms = result["objects"]["test"]["geometries"]
        assert len(geoms) == 2
        assert geoms[0]["type"] == "Point"

    def test_linestring_topology(self):
        rows = [{"site_id": "L1", "geometry": {
            "type": "LineString", "coordinates": [(0, 0), (1, 1), (2, 0)]
        }}]
        frame = GeoPromptFrame.from_records(rows)
        result = frame.to_topojson()
        assert result["type"] == "Topology"
        geoms = result["objects"]["data"]["geometries"]
        assert len(geoms) == 1
        assert geoms[0]["type"] == "LineString"
        assert len(result["arcs"]) == 1

    def test_polygon_topology(self):
        rows = [{"site_id": "p0", "geometry": {
            "type": "Polygon",
            "coordinates": [[(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]]
        }}]
        frame = GeoPromptFrame.from_records(rows)
        result = frame.to_topojson()
        geoms = result["objects"]["data"]["geometries"]
        assert geoms[0]["type"] == "Polygon"
        assert len(result["arcs"]) == 1


# ---- Tools 145-147: File I/O (structural tests without external libs) ----
class TestFileIO:
    def test_read_shapefile_import_error(self):
        """read_shapefile raises ImportError when neither pyshp nor fiona available."""
        # This test is structural — just checks the method signature exists
        assert hasattr(GeoPromptFrame, "read_shapefile")
        assert hasattr(GeoPromptFrame, "to_shapefile")

    def test_read_geopackage_exists(self):
        assert hasattr(GeoPromptFrame, "read_geopackage")

    def test_read_kml_from_string(self):
        """Test KML reading with a minimal KML file."""
        kml_content = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <name>Test Point</name>
      <Point>
        <coordinates>-122.0,37.0</coordinates>
      </Point>
    </Placemark>
    <Placemark>
      <name>Test Line</name>
      <LineString>
        <coordinates>-122.0,37.0 -121.0,38.0</coordinates>
      </LineString>
    </Placemark>
  </Document>
</kml>"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".kml", delete=False) as f:
            f.write(kml_content)
            path = f.name
        try:
            frame = GeoPromptFrame.read_kml(path)
            recs = frame.to_records()
            assert len(recs) == 2
            assert recs[0]["name"] == "Test Point"
            assert recs[0]["geometry"]["type"] == "Point"
            assert recs[1]["geometry"]["type"] == "LineString"
        finally:
            os.unlink(path)
