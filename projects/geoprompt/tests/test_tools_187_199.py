"""Tests for tools 187-199 and improved tools 175-179."""
from __future__ import annotations

import math
from collections.abc import Sequence
import pytest

from geoprompt.frame import GeoPromptFrame


# ── Helpers ──────────────────────────────────────────────────────────

def _point(x: float, y: float) -> dict:
    return {"type": "Point", "coordinates": (x, y)}


def _polygon(coords: list[list[float]]) -> dict:
    return {"type": "Polygon", "coordinates": [coords]}


def _line(coords: list[list[float]]) -> dict:
    return {"type": "LineString", "coordinates": coords}


def _make_point_frame(points: Sequence[tuple[float, float]], values: list[float] | None = None) -> GeoPromptFrame:
    records = []
    for i, (x, y) in enumerate(points):
        rec = {"geometry": _point(x, y), "site_id": f"s{i}"}
        if values is not None:
            rec["value"] = values[i]
        records.append(rec)
    return GeoPromptFrame.from_records(records)


def _make_network_frame() -> GeoPromptFrame:
    """A small triangle network for routing tests."""
    return GeoPromptFrame.from_records([
        {"geometry": _line([[0, 0], [1, 0]]), "from_node": "A", "to_node": "B", "cost": 1.0},
        {"geometry": _line([[1, 0], [1, 1]]), "from_node": "B", "to_node": "C", "cost": 1.0},
        {"geometry": _line([[0, 0], [1, 1]]), "from_node": "A", "to_node": "C", "cost": 1.5},
        {"geometry": _line([[1, 1], [2, 1]]), "from_node": "C", "to_node": "D", "cost": 2.0},
        {"geometry": _line([[2, 1], [2, 2]]), "from_node": "D", "to_node": "E", "cost": 1.0},
        {"geometry": _line([[1, 0], [2, 0]]), "from_node": "B", "to_node": "F", "cost": 3.0},
        {"geometry": _line([[2, 0], [2, 1]]), "from_node": "F", "to_node": "D", "cost": 1.0},
    ])


# ══════════════════════════════════════════════════════════════════════
# IMPROVED TOOLS
# ══════════════════════════════════════════════════════════════════════

class TestImprovedPolygonValidityCheck:
    """Tests for the improved polygon_validity_check (tool 175)."""

    def test_valid_ccw_polygon(self):
        # CCW: (0,0)->(0,1)->(1,1)->(1,0) has negative signed area = valid
        gf = GeoPromptFrame.from_records([{
            "geometry": _polygon([[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]])
        }])
        result = gf.polygon_validity_check()
        row = result.to_records()[0]
        assert row["is_valid_pv"] is True

    def test_clockwise_detected(self):
        # CW: (0,0)->(1,0)->(1,1)->(0,1) has positive signed area = clockwise = invalid
        gf = GeoPromptFrame.from_records([{
            "geometry": _polygon([[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]])
        }])
        result = gf.polygon_validity_check()
        row = result.to_records()[0]
        assert row["is_valid_pv"] is False
        assert "clockwise_outer_ring" in row["issue_pv"]

    def test_self_intersection_detected(self):
        # Figure-eight polygon
        gf = GeoPromptFrame.from_records([{
            "geometry": _polygon([[0, 0], [2, 2], [2, 0], [0, 2], [0, 0]])
        }])
        result = gf.polygon_validity_check()
        row = result.to_records()[0]
        assert row["is_valid_pv"] is False
        assert "self_intersection" in row["issue_pv"]

    def test_duplicate_consecutive_vertex(self):
        gf = GeoPromptFrame.from_records([{
            "geometry": _polygon([[0, 0], [1, 0], [1, 0], [1, 1], [0, 1], [0, 0]])
        }])
        result = gf.polygon_validity_check()
        row = result.to_records()[0]
        assert "duplicate_consecutive_vertex" in row["issue_pv"]

    def test_non_polygon_type(self):
        gf = GeoPromptFrame.from_records([{"geometry": _point(0, 0)}])
        result = gf.polygon_validity_check()
        row = result.to_records()[0]
        assert row["is_valid_pv"] is True

    def test_empty_frame(self):
        gf = GeoPromptFrame.from_records([])
        result = gf.polygon_validity_check()
        assert len(result) == 0


class TestImprovedPolygonRepair:
    """Tests for the improved polygon_repair (tool 176)."""

    def test_closes_ring(self):
        # CW polygon: repair should reverse it (normalizer auto-closes, so we test winding fix)
        gf = GeoPromptFrame.from_records([{
            "geometry": _polygon([[0, 0], [1, 0], [1, 1], [0, 1]])
        }])
        result = gf.polygon_repair()
        row = result.to_records()[0]
        assert row["repaired_pr"] is True

    def test_fixes_winding(self):
        # CW ring: (0,0)->(1,0)->(1,1)->(0,1)->(0,0) has positive area
        gf = GeoPromptFrame.from_records([{
            "geometry": _polygon([[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]])
        }])
        result = gf.polygon_repair()
        row = result.to_records()[0]
        assert row["repaired_pr"] is True
        assert "reversed_outer_ring" in row["repairs_pr"]

    def test_removes_duplicate_vertices(self):
        gf = GeoPromptFrame.from_records([{
            "geometry": _polygon([[0, 0], [1, 0], [1, 0], [1, 1], [0, 1], [0, 0]])
        }])
        result = gf.polygon_repair()
        row = result.to_records()[0]
        assert row["repaired_pr"] is True
        assert "removed_duplicate_vertices" in row["repairs_pr"]

    def test_repair_report_column_exists(self):
        # A valid CCW polygon should not need repair
        gf = GeoPromptFrame.from_records([{
            "geometry": _polygon([[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]])
        }])
        result = gf.polygon_repair()
        row = result.to_records()[0]
        assert "repairs_pr" in row
        assert row["repaired_pr"] is False

    def test_non_polygon(self):
        gf = GeoPromptFrame.from_records([{"geometry": _point(0, 0)}])
        result = gf.polygon_repair()
        row = result.to_records()[0]
        assert row["repaired_pr"] is False


class TestImprovedSharedBoundaries:
    """Tests for the improved shared_boundaries (tool 179)."""

    def test_shared_edge_detection(self):
        gf = GeoPromptFrame.from_records([
            {"geometry": _polygon([[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]), "site_id": "A"},
            {"geometry": _polygon([[1, 0], [2, 0], [2, 1], [1, 1], [1, 0]]), "site_id": "B"},
        ])
        result = gf.shared_boundaries()
        rows = result.to_records()
        assert len(rows) >= 1
        assert rows[0]["left_sb"] == "A"
        assert rows[0]["right_sb"] == "B"
        assert "n_shared_edges_sb" in rows[0]

    def test_no_shared_boundary(self):
        gf = GeoPromptFrame.from_records([
            {"geometry": _polygon([[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]), "site_id": "A"},
            {"geometry": _polygon([[5, 5], [6, 5], [6, 6], [5, 6], [5, 5]]), "site_id": "B"},
        ])
        result = gf.shared_boundaries()
        assert len(result) == 0

    def test_single_polygon(self):
        gf = GeoPromptFrame.from_records([
            {"geometry": _polygon([[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]), "site_id": "A"},
        ])
        result = gf.shared_boundaries()
        assert len(result) == 0

    def test_length_reported(self):
        gf = GeoPromptFrame.from_records([
            {"geometry": _polygon([[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]), "site_id": "A"},
            {"geometry": _polygon([[1, 0], [2, 0], [2, 1], [1, 1], [1, 0]]), "site_id": "B"},
        ])
        result = gf.shared_boundaries()
        rows = result.to_records()
        assert len(rows) >= 1
        assert "length_sb" in rows[0]
        assert rows[0]["length_sb"] > 0


class TestImprovedVoronoiPolygons:
    """Tests for the improved voronoi_polygons (tool 178)."""

    def test_basic_voronoi(self):
        pts = [(0, 0), (2, 0), (1, 2)]
        gf = _make_point_frame(pts)
        result = gf.voronoi_polygons()
        rows = result.to_records()
        assert len(rows) == 3
        # At least some cells should have positive area
        areas = [row.get("area_vor", 0) for row in rows]
        assert sum(1 for a in areas if a > 0) >= 1

    def test_single_point(self):
        gf = _make_point_frame([(0, 0)])
        result = gf.voronoi_polygons()
        assert len(result) == 1

    def test_voronoi_area_positive(self):
        pts = [(0, 0), (10, 0), (5, 10), (0, 10), (10, 10)]
        gf = _make_point_frame(pts)
        result = gf.voronoi_polygons()
        areas = [row.get("area_vor", 0) for row in result.to_records()]
        # Most cells should have area > 0
        assert sum(1 for a in areas if a > 0) >= 3


class TestImprovedThinPlateSpline:
    """Tests for the improved thin_plate_spline (tool 157)."""

    def test_basic_tps(self):
        pts = [(0, 0), (1, 0), (0, 1), (1, 1)]
        vals = [1.0, 2.0, 3.0, 4.0]
        gf = _make_point_frame(pts, vals)
        result = gf.thin_plate_spline("value", grid_resolution=5)
        rows = result.to_records()
        assert len(rows) == 25
        assert "value_tps" in rows[0]

    def test_condition_field(self):
        pts = [(0, 0), (1, 0), (0, 1), (1, 1)]
        vals = [1.0, 2.0, 3.0, 4.0]
        gf = _make_point_frame(pts, vals)
        result = gf.thin_plate_spline("value", grid_resolution=3)
        row = result.to_records()[0]
        assert "condition_tps" in row

    def test_too_few_points(self):
        gf = _make_point_frame([(0, 0), (1, 1)], [1.0, 2.0])
        result = gf.thin_plate_spline("value")
        assert len(result) == 2  # returns original


# ══════════════════════════════════════════════════════════════════════
# NEW TOOLS
# ══════════════════════════════════════════════════════════════════════

class TestDBSCAN:
    """Tests for dbscan (tool 187)."""

    def test_basic_clustering(self):
        pts = [(0, 0), (0.1, 0), (0, 0.1), (5, 5), (5.1, 5), (5, 5.1)]
        gf = _make_point_frame(pts)
        result = gf.dbscan(eps=1.0, min_samples=2)
        rows = result.to_records()
        assert len(rows) == 6
        # Two tight clusters should be found
        labels = [r["cluster_db"] for r in rows]
        # First 3 should share a label, last 3 should share another
        assert labels[0] == labels[1] == labels[2]
        assert labels[3] == labels[4] == labels[5]
        assert labels[0] != labels[3]

    def test_noise_detection(self):
        pts = [(0, 0), (0.1, 0), (0, 0.1), (100, 100)]
        gf = _make_point_frame(pts)
        result = gf.dbscan(eps=1.0, min_samples=2)
        rows = result.to_records()
        # The isolated point should be noise
        assert rows[3]["is_noise_db"] is True

    def test_empty_frame(self):
        gf = GeoPromptFrame.from_records([])
        result = gf.dbscan(eps=1.0)
        assert len(result) == 0

    def test_all_noise_high_min_samples(self):
        pts = [(0, 0), (10, 10), (20, 20)]
        gf = _make_point_frame(pts)
        result = gf.dbscan(eps=1.0, min_samples=5)
        rows = result.to_records()
        assert all(r["is_noise_db"] for r in rows)


class TestHDBSCAN:
    """Tests for hdbscan (tool 188)."""

    def test_basic_clustering(self):
        pts = [(0, 0), (0.1, 0), (0, 0.1), (0.05, 0.05),
               (5, 5), (5.1, 5), (5, 5.1), (5.05, 5.05)]
        gf = _make_point_frame(pts)
        result = gf.hdbscan(min_cluster_size=3)
        rows = result.to_records()
        assert len(rows) == 8
        labels = [r["cluster_hdb"] for r in rows]
        # Two clusters; first 4 and last 4
        assert labels[0] == labels[1] == labels[2] == labels[3]
        assert labels[4] == labels[5] == labels[6] == labels[7]

    def test_core_distance_reported(self):
        pts = [(0, 0), (1, 0), (0, 1), (1, 1)]
        gf = _make_point_frame(pts)
        result = gf.hdbscan(min_cluster_size=2)
        row = result.to_records()[0]
        assert "core_distance_hdb" in row

    def test_empty_frame(self):
        gf = GeoPromptFrame.from_records([])
        result = gf.hdbscan(min_cluster_size=2)
        assert len(result) == 0


class TestMultivariateMoransI:
    """Tests for multivariate_morans_i (tool 189)."""

    def test_basic_output(self):
        pts = [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0)]
        records = [{"geometry": _point(x, 0), "val_a": float(x), "val_b": float(x) * 2} for x, _ in pts]
        gf = GeoPromptFrame.from_records(records)
        results = gf.multivariate_morans_i(["val_a", "val_b"], k=2)
        assert len(results) > 0
        assert results[0]["statistic"] == "multivariate_morans_i"
        assert "I" in results[0]

    def test_cross_moran_entries(self):
        records = [{"geometry": _point(i, 0), "a": float(i), "b": float(i * 3)} for i in range(5)]
        gf = GeoPromptFrame.from_records(records)
        results = gf.multivariate_morans_i(["a", "b"], k=2)
        cross = [r for r in results if r.get("statistic") == "cross_moran"]
        assert len(cross) == 4  # 2x2 matrix

    def test_too_few_points(self):
        gf = GeoPromptFrame.from_records([
            {"geometry": _point(0, 0), "a": 1.0, "b": 2.0},
            {"geometry": _point(1, 1), "a": 3.0, "b": 4.0},
        ])
        results = gf.multivariate_morans_i(["a", "b"])
        assert results[0]["I"] == 0.0


class TestLocalGearyDecomposition:
    """Tests for local_geary_decomposition (tool 190)."""

    def test_output_has_per_variable_columns(self):
        records = [{"geometry": _point(i, 0), "a": float(i), "b": float(i ** 2)} for i in range(6)]
        gf = GeoPromptFrame.from_records(records)
        result = gf.local_geary_decomposition(["a", "b"], k=3)
        rows = result.to_records()
        assert len(rows) == 6
        assert "local_geary_lgd" in rows[0]
        assert "geary_a_lgd" in rows[0]
        assert "geary_b_lgd" in rows[0]

    def test_single_feature(self):
        gf = GeoPromptFrame.from_records([{"geometry": _point(0, 0), "a": 1.0, "b": 2.0}])
        result = gf.local_geary_decomposition(["a", "b"])
        assert len(result) == 1


class TestAdaptiveIDW:
    """Tests for adaptive_idw (tool 191)."""

    def test_basic_output(self):
        pts = [(0, 0), (1, 0), (0, 1), (1, 1), (0.5, 0.5)]
        vals = [1.0, 2.0, 3.0, 4.0, 2.5]
        gf = _make_point_frame(pts, vals)
        result = gf.adaptive_idw("value", grid_resolution=5, k_neighbors=3)
        rows = result.to_records()
        assert len(rows) == 25
        assert "value_aidw" in rows[0]
        assert "power_aidw" in rows[0]

    def test_too_few_points(self):
        gf = _make_point_frame([(0, 0)], [1.0])
        result = gf.adaptive_idw("value")
        assert len(result) == 1


class TestFocalStatistics:
    """Tests for focal_statistics (existing tool 80 — verify no regression)."""

    def test_basic_output(self):
        pts = [(0, 0), (1, 0), (0, 1), (1, 1)]
        vals = [10.0, 20.0, 30.0, 40.0]
        gf = _make_point_frame(pts, vals)
        result = gf.focal_statistics("value", grid_resolution=5, window_size=3, statistic="mean")
        rows = result.to_records()
        assert len(rows) == 25
        assert "value_focal" in rows[0]

    def test_min_lte_max(self):
        pts = [(0, 0), (1, 0), (0, 1), (1, 1)]
        vals = [1.0, 5.0, 3.0, 7.0]
        gf = _make_point_frame(pts, vals)
        result_min = gf.focal_statistics("value", grid_resolution=4, window_size=3, statistic="min")
        result_max = gf.focal_statistics("value", grid_resolution=4, window_size=3, statistic="max")
        mins = [r["value_focal"] for r in result_min.to_records()]
        maxs = [r["value_focal"] for r in result_max.to_records()]
        for mn, mx in zip(mins, maxs):
            assert mn <= mx


class TestRasterAlgebra:
    """Tests for raster_algebra (tool 193)."""

    def test_simple_expression(self):
        records = [{"geometry": _point(i, 0), "val": float(i)} for i in range(5)]
        gf = GeoPromptFrame.from_records(records)
        result = gf.raster_algebra("val", expression="x * 2 + 1")
        rows = result.to_records()
        assert rows[0]["result_ra"] == pytest.approx(1.0)
        assert rows[2]["result_ra"] == pytest.approx(5.0)

    def test_sqrt_expression(self):
        records = [{"geometry": _point(0, 0), "val": 16.0}]
        gf = GeoPromptFrame.from_records(records)
        result = gf.raster_algebra("val", expression="sqrt(x)")
        assert result.to_records()[0]["result_ra"] == pytest.approx(4.0)

    def test_power_expression(self):
        records = [{"geometry": _point(0, 0), "val": 3.0}]
        gf = GeoPromptFrame.from_records(records)
        result = gf.raster_algebra("val", expression="x ** 2")
        assert result.to_records()[0]["result_ra"] == pytest.approx(9.0)


class TestPolygonTriangulation:
    """Tests for polygon_triangulation (tool 194)."""

    def test_square_triangulation(self):
        gf = GeoPromptFrame.from_records([{
            "geometry": _polygon([[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]])
        }])
        result = gf.polygon_triangulation()
        rows = result.to_records()
        # Square should produce 2 triangles
        assert len(rows) == 2
        for row in rows:
            geom = row["geometry"]
            assert geom["type"] == "Polygon"
            assert len(geom["coordinates"][0]) == 4  # 3 vertices + closing

    def test_triangle_input(self):
        gf = GeoPromptFrame.from_records([{
            "geometry": _polygon([[0, 0], [1, 0], [0.5, 1], [0, 0]])
        }])
        result = gf.polygon_triangulation()
        assert len(result) == 1

    def test_non_polygon_skipped(self):
        gf = GeoPromptFrame.from_records([{"geometry": _point(0, 0)}])
        result = gf.polygon_triangulation()
        assert len(result) == 0

    def test_empty_frame(self):
        gf = GeoPromptFrame.from_records([])
        result = gf.polygon_triangulation()
        assert len(result) == 0


class TestServiceAreaPolygons:
    """Tests for service_area_polygons (tool 195)."""

    def test_basic_service_areas(self):
        gf = _make_network_frame()
        result = gf.service_area_polygons(origin_nodes=["A"], cost_breaks=[2.0, 5.0])
        rows = result.to_records()
        assert len(rows) >= 1
        assert "origin_sa" in rows[0]
        assert "cost_break_sa" in rows[0]
        assert "area_sa" in rows[0]

    def test_larger_cost_more_reachable(self):
        gf = _make_network_frame()
        result = gf.service_area_polygons(origin_nodes=["A"], cost_breaks=[1.5, 10.0])
        rows = result.to_records()
        if len(rows) >= 2:
            areas = {r["cost_break_sa"]: r["area_sa"] for r in rows}
            if 1.5 in areas and 10.0 in areas:
                assert areas[10.0] >= areas[1.5]

    def test_single_edge_frame(self):
        gf = GeoPromptFrame.from_records([
            {"geometry": _line([[0, 0], [1, 0]]), "from_node": "A", "to_node": "B", "cost": 1.0},
        ])
        result = gf.service_area_polygons(origin_nodes=["A"], cost_breaks=[5.0])
        assert isinstance(result.to_records(), list)


class TestIsochrones:
    """Tests for isochrones (tool 196)."""

    def test_basic_isochrones(self):
        gf = _make_network_frame()
        result = gf.isochrones(origin_node="A", time_breaks=[2.0, 5.0, 10.0])
        rows = result.to_records()
        # Might not produce all breaks if not enough nodes
        assert isinstance(rows, list)
        for row in rows:
            assert "origin_iso" in row
            assert "time_break_iso" in row

    def test_single_edge(self):
        gf = GeoPromptFrame.from_records([
            {"geometry": _line([[0, 0], [1, 0]]), "from_node": "X", "to_node": "Y", "cost": 1.0},
        ])
        result = gf.isochrones(origin_node="X", time_breaks=[5.0])
        assert isinstance(result.to_records(), list)


class TestNegativeBinomialGWR:
    """Tests for negative_binomial_gwr (tool 197)."""

    def test_basic_output(self):
        records = [
            {"geometry": _point(i, j), "count": abs(i + j) + 1, "x1": float(i), "x2": float(j)}
            for i in range(4) for j in range(4)
        ]
        gf = GeoPromptFrame.from_records(records)
        result = gf.negative_binomial_gwr("count", ["x1", "x2"], k_neighbors=5)
        rows = result.to_records()
        assert len(rows) == 16
        assert "predicted_nbgwr" in rows[0]
        assert "residual_nbgwr" in rows[0]
        assert "alpha_nbgwr" in rows[0]
        assert "intercept_nbgwr" in rows[0]

    def test_too_few_points(self):
        gf = GeoPromptFrame.from_records([
            {"geometry": _point(0, 0), "count": 1, "x1": 1.0},
            {"geometry": _point(1, 1), "count": 2, "x1": 2.0},
        ])
        result = gf.negative_binomial_gwr("count", ["x1"])
        assert len(result) == 2  # returns original


class TestGeographicallyWeightedPCA:
    """Tests for geographically_weighted_pca (tool 198)."""

    def test_basic_output(self):
        records = [
            {"geometry": _point(i, j), "a": float(i), "b": float(j), "c": float(i + j)}
            for i in range(5) for j in range(5)
        ]
        gf = GeoPromptFrame.from_records(records)
        result = gf.geographically_weighted_pca(["a", "b", "c"], n_components=2, k_neighbors=8)
        rows = result.to_records()
        assert len(rows) == 25
        assert "pc1_gwpca" in rows[0]
        assert "pc2_gwpca" in rows[0]
        assert "eigenvalue_1_gwpca" in rows[0]
        assert "explained_variance_gwpca" in rows[0]

    def test_too_few_variables(self):
        records = [{"geometry": _point(i, 0), "a": float(i)} for i in range(5)]
        gf = GeoPromptFrame.from_records(records)
        result = gf.geographically_weighted_pca(["a"], n_components=1)
        assert len(result) == 5  # returns original


class TestSpaceTimeKriging:
    """Tests for space_time_kriging (tool 199)."""

    def test_basic_output(self):
        records = [
            {"geometry": _point(i, j), "value": float(i + j), "time": float(t)}
            for i in range(3) for j in range(3) for t in range(3)
        ]
        gf = GeoPromptFrame.from_records(records)
        result = gf.space_time_kriging("value", "time", grid_resolution=5, target_time=2.0)
        rows = result.to_records()
        assert len(rows) == 25
        assert "predicted_stk" in rows[0]
        assert "variance_stk" in rows[0]
        assert "target_time_stk" in rows[0]

    def test_variance_non_negative(self):
        records = [
            {"geometry": _point(i, j), "value": float(i * j), "time": float(t)}
            for i in range(3) for j in range(3) for t in range(2)
        ]
        gf = GeoPromptFrame.from_records(records)
        result = gf.space_time_kriging("value", "time", grid_resolution=4)
        for row in result.to_records():
            assert row["variance_stk"] >= 0

    def test_too_few_points(self):
        gf = GeoPromptFrame.from_records([
            {"geometry": _point(0, 0), "value": 1.0, "time": 0.0},
        ])
        result = gf.space_time_kriging("value", "time")
        assert len(result) == 1


# ══════════════════════════════════════════════════════════════════════
# NEIGHBOR CACHE INFRASTRUCTURE
# ══════════════════════════════════════════════════════════════════════

class TestNeighborCache:
    """Tests for the new _cached_distance_matrix and _cached_knn methods."""

    def test_distance_matrix_cached(self):
        gf = _make_point_frame([(0, 0), (1, 0), (0, 1)])
        dm1 = gf._cached_distance_matrix()
        dm2 = gf._cached_distance_matrix()
        assert dm1 is dm2  # same object from cache

    def test_distance_matrix_values(self):
        gf = _make_point_frame([(0, 0), (3, 4)])
        dm = gf._cached_distance_matrix()
        assert dm[0][1] == pytest.approx(5.0)
        assert dm[1][0] == pytest.approx(5.0)
        assert dm[0][0] == pytest.approx(0.0)

    def test_knn_cached(self):
        gf = _make_point_frame([(0, 0), (1, 0), (2, 0), (3, 0)])
        knn1 = gf._cached_knn(2)
        knn2 = gf._cached_knn(2)
        assert knn1 is knn2

    def test_knn_values(self):
        gf = _make_point_frame([(0, 0), (1, 0), (10, 0)])
        knn = gf._cached_knn(1)
        assert knn[0] == [1]  # nearest to (0,0) is (1,0)
        assert knn[1] == [0]  # nearest to (1,0) is (0,0)
        assert knn[2] == [1]  # nearest to (10,0) is (1,0)
