"""Tests for P3 new tools (101-130)."""
from __future__ import annotations

import math
from collections.abc import Sequence
import pytest
from geoprompt import GeoPromptFrame


def _point_frame(coords: Sequence[tuple[float, float]], values: list[float] | None = None) -> GeoPromptFrame:
    rows = []
    for i, (x, y) in enumerate(coords):
        row: dict = {"site_id": f"p{i}", "geometry": {"type": "Point", "coordinates": (x, y)}}
        if values:
            row["value"] = values[i]
        rows.append(row)
    return GeoPromptFrame.from_records(rows)


def _grid_points(n: int = 25) -> list[tuple[float, float]]:
    side = int(math.sqrt(n))
    return [(float(x), float(y)) for y in range(side) for x in range(side)]


# ---- Tool 101: getis_ord_g_global ----
class TestGetisOrdGGlobal:
    def test_returns_g_statistic(self):
        pts = _grid_points(25)
        vals = [float(i) for i in range(25)]
        frame = _point_frame(pts, vals)
        result = frame.getis_ord_g_global("value", k=4)
        assert result["g_statistic"] is not None
        assert isinstance(result["z_score"], float)
        assert isinstance(result["p_value"], float)
        assert result["n"] == 25

    def test_empty_frame(self):
        frame = GeoPromptFrame.from_records([])
        with pytest.raises(KeyError):
            frame.getis_ord_g_global("value")


# ---- Tool 102: lees_l ----
class TestLeesL:
    def test_bivariate_association(self):
        pts = _grid_points(25)
        vals_x = [float(i) for i in range(25)]
        vals_y = [float(i * 2) for i in range(25)]
        rows = [{"site_id": f"p{i}", "x": vals_x[i], "y": vals_y[i],
                 "geometry": {"type": "Point", "coordinates": pts[i]}} for i in range(25)]
        frame = GeoPromptFrame.from_records(rows)
        result = frame.lees_l("x", "y", k=4)
        recs = result.to_records()
        assert len(recs) == 25
        assert "global_l_lee" in recs[0]
        assert "local_l_lee" in recs[0]

    def test_positive_correlation(self):
        pts = [(float(i), 0.0) for i in range(10)]
        rows = [{"site_id": f"p{i}", "x": float(i), "y": float(i),
                 "geometry": {"type": "Point", "coordinates": pts[i]}} for i in range(10)]
        frame = GeoPromptFrame.from_records(rows)
        result = frame.lees_l("x", "y", k=2)
        recs = result.to_records()
        assert recs[0]["global_l_lee"] > 0


# ---- Tool 103: spatial_correlogram ----
class TestSpatialCorrelogram:
    def test_returns_lag_entries(self):
        pts = _grid_points(25)
        vals = [float(i) for i in range(25)]
        frame = _point_frame(pts, vals)
        result = frame.spatial_correlogram("value", n_lags=5)
        assert len(result) == 5
        assert "morans_i" in result[0]
        assert result[0]["lag"] == 1

    def test_empty(self):
        frame = _point_frame([(0, 0)], [1.0])
        assert frame.spatial_correlogram("value") == []


# ---- Tool 104: variogram_cloud ----
class TestVariogramCloud:
    def test_returns_pairs(self):
        pts = [(0, 0), (1, 0), (2, 0), (0, 1)]
        vals = [1.0, 2.0, 4.0, 1.5]
        frame = _point_frame(pts, vals)
        result = frame.variogram_cloud("value")
        assert len(result) == 6  # C(4,2)
        assert "distance" in result[0]
        assert "semivariance" in result[0]
        assert all(r["semivariance"] >= 0 for r in result)


# ---- Tool 105: universal_kriging ----
class TestUniversalKriging:
    def test_generates_grid(self):
        pts = [(0, 0), (10, 0), (0, 10), (10, 10), (5, 5)]
        vals = [1.0, 2.0, 3.0, 4.0, 2.5]
        frame = _point_frame(pts, vals)
        result = frame.universal_kriging("value", grid_resolution=5, drift_order=1)
        recs = result.to_records()
        assert len(recs) == 25
        assert "value_uk" in recs[0]
        assert "trend_uk" in recs[0]
        assert "residual_uk" in recs[0]


# ---- Tool 106: rbf_interpolation ----
class TestRBFInterpolation:
    def test_generates_grid(self):
        pts = [(0, 0), (10, 0), (0, 10), (10, 10)]
        vals = [1.0, 2.0, 3.0, 4.0]
        frame = _point_frame(pts, vals)
        result = frame.rbf_interpolation("value", grid_resolution=5, function="multiquadric")
        recs = result.to_records()
        assert len(recs) == 25
        assert "value_rbf" in recs[0]

    def test_thin_plate(self):
        pts = [(0, 0), (5, 0), (0, 5)]
        vals = [1.0, 2.0, 3.0]
        frame = _point_frame(pts, vals)
        result = frame.rbf_interpolation("value", grid_resolution=3, function="thin_plate")
        assert len(result) == 9


# ---- Tool 107: fuzzy_c_means ----
class TestFuzzyCMeans:
    def test_assigns_clusters_and_membership(self):
        pts = [(0, 0), (0, 1), (10, 10), (10, 11), (20, 20), (20, 21)]
        frame = _point_frame(pts)
        result = frame.fuzzy_c_means(n_clusters=3, random_seed=42)
        recs = result.to_records()
        assert len(recs) == 6
        assert "cluster_fcm" in recs[0]
        assert "max_membership_fcm" in recs[0]
        assert 0 <= recs[0]["max_membership_fcm"] <= 1.0
        assert "membership_0_fcm" in recs[0]


# ---- Tool 108: gaussian_mixture_spatial ----
class TestGaussianMixtureSpatial:
    def test_assigns_clusters(self):
        pts = [(0, 0), (0, 1), (10, 10), (10, 11)]
        frame = _point_frame(pts)
        result = frame.gaussian_mixture_spatial(n_components=2)
        recs = result.to_records()
        assert len(recs) == 4
        assert "cluster_gmm" in recs[0]


# ---- Tool 109: spatial_error_model ----
class TestSpatialErrorModel:
    def test_sem_regression(self):
        pts = [(float(i), 0.0) for i in range(20)]
        rows = [{"site_id": f"p{i}", "y": float(i * 2 + 1), "x": float(i),
                 "geometry": {"type": "Point", "coordinates": pts[i]}} for i in range(20)]
        frame = GeoPromptFrame.from_records(rows)
        result = frame.spatial_error_model("y", ["x"], k=3)
        recs = result.to_records()
        assert "predicted_sem" in recs[0]
        assert "lambda_sem" in recs[0]
        assert recs[0]["r_squared_sem"] > 0.5


# ---- Tool 110: spatial_lag_model ----
class TestSpatialLagModel:
    def test_slm_regression(self):
        pts = [(float(i), 0.0) for i in range(20)]
        rows = [{"site_id": f"p{i}", "y": float(i * 2 + 1), "x": float(i),
                 "geometry": {"type": "Point", "coordinates": pts[i]}} for i in range(20)]
        frame = GeoPromptFrame.from_records(rows)
        result = frame.spatial_lag_model("y", ["x"], k=3)
        recs = result.to_records()
        assert "predicted_slm" in recs[0]
        assert "rho_slm" in recs[0]
        assert recs[0]["r_squared_slm"] > 0.5


# ---- Tool 111: curvature ----
class TestCurvature:
    def test_computes_curvature_grid(self):
        pts = _grid_points(25)
        vals = [x * x + y * y for x, y in pts]  # paraboloid
        frame = _point_frame(pts, vals)
        result = frame.curvature("value")
        recs = result.to_records()
        assert len(recs) > 0
        assert "profile_curv" in recs[0]
        assert "plan_curv" in recs[0]
        assert "total_curv" in recs[0]


# ---- Tool 112: topographic_wetness_index ----
class TestTopographicWetnessIndex:
    def test_computes_twi(self):
        pts = _grid_points(25)
        vals = [float(y) for _, y in pts]  # slope north
        frame = _point_frame(pts, vals)
        result = frame.topographic_wetness_index("value", grid_resolution=5)
        recs = result.to_records()
        assert len(recs) > 0
        assert "twi_twi" in recs[0]


# ---- Tool 113: depression_fill ----
class TestDepressionFill:
    def test_fills_sink(self):
        pts = _grid_points(25)
        vals = [5.0] * 25
        # Create a sink in the middle
        vals[12] = 1.0  # middle cell
        frame = _point_frame(pts, vals)
        result = frame.depression_fill("value")
        recs = result.to_records()
        assert len(recs) > 0
        assert "filled_fill" in recs[0]
        assert "depth_fill" in recs[0]
        # All filled values should be >= original
        for r in recs:
            assert r["filled_fill"] >= r["original_fill"] - 1e-9


# ---- Tool 114: solar_radiation ----
class TestSolarRadiation:
    def test_computes_radiation(self):
        pts = _grid_points(16)
        vals = [float(y) for _, y in pts]
        frame = _point_frame(pts, vals)
        result = frame.solar_radiation("value", grid_resolution=4)
        recs = result.to_records()
        assert len(recs) == 16
        assert "radiation_solar" in recs[0]
        assert recs[0]["radiation_solar"] >= 0


# ---- Tool 115: network_voronoi ----
class TestNetworkVoronoi:
    def test_assigns_to_nearest_facility(self):
        demand = _point_frame([(0, 0), (1, 0), (5, 5), (6, 5)])
        facilities = _point_frame([(0, 0), (6, 5)])
        result = demand.network_voronoi(facilities)
        recs = result.to_records()
        assert len(recs) == 4
        assert "facility_nv" in recs[0]
        assert recs[0]["facility_nv"] == "p0"
        assert recs[3]["facility_nv"] == "p1"


# ---- Tool 116: max_flow ----
class TestMaxFlow:
    def test_simple_flow(self):
        rows = [
            {"site_id": "s", "capacity": 10.0, "geometry": {"type": "Point", "coordinates": (0, 0)},
             "edge_to": "a"},
            {"site_id": "a", "capacity": 5.0, "geometry": {"type": "Point", "coordinates": (1, 0)},
             "edge_to": "t"},
            {"site_id": "t", "capacity": 10.0, "geometry": {"type": "Point", "coordinates": (2, 0)},
             "edge_to": ""},
        ]
        frame = GeoPromptFrame.from_records(rows)
        result = frame.max_flow("s", "t")
        assert "max_flow" in result
        assert result["max_flow"] == pytest.approx(5.0)


# ---- Tool 117: k_cross_function ----
class TestKCrossFunction:
    def test_bivariate_k(self):
        frame1 = _point_frame([(0, 0), (1, 0), (2, 0)])
        frame2 = _point_frame([(0, 1), (1, 1), (2, 1)])
        result = frame1.k_cross_function(frame2, n_distances=5)
        assert len(result) == 5
        assert "k_cross" in result[0]
        assert result[0]["k_cross"] >= 0


# ---- Tool 118: pair_correlation_function ----
class TestPairCorrelation:
    def test_returns_g_r(self):
        import random
        rng = random.Random(42)
        pts = [(rng.uniform(0, 10), rng.uniform(0, 10)) for _ in range(30)]
        frame = _point_frame(pts)
        result = frame.pair_correlation_function(n_distances=5)
        assert len(result) == 5
        assert "g_r" in result[0]
        assert "expected_g" in result[0]


# ---- Tool 119: nn_g_function ----
class TestNNGFunction:
    def test_returns_g_cdf(self):
        import random
        rng = random.Random(42)
        pts = [(rng.uniform(0, 10), rng.uniform(0, 10)) for _ in range(20)]
        frame = _point_frame(pts)
        result = frame.nn_g_function(n_distances=5)
        assert len(result) == 5
        assert "g_empirical" in result[0]
        assert 0 <= result[-1]["g_empirical"] <= 1.0


# ---- Tool 120: empty_space_f_function ----
class TestEmptySpaceFFunction:
    def test_returns_f_cdf(self):
        import random
        rng = random.Random(42)
        pts = [(rng.uniform(0, 10), rng.uniform(0, 10)) for _ in range(20)]
        frame = _point_frame(pts)
        result = frame.empty_space_f_function(n_distances=5, n_random=50)
        assert len(result) == 5
        assert "f_empirical" in result[0]
        assert 0 <= result[-1]["f_empirical"] <= 1.0


# ---- Tool 121: minimum_bounding_circle ----
class TestMinimumBoundingCircle:
    def test_circle_around_polygon(self):
        rows = [{"site_id": "poly", "geometry": {
            "type": "Polygon",
            "coordinates": [[(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]]
        }}]
        frame = GeoPromptFrame.from_records(rows)
        result = frame.minimum_bounding_circle()
        recs = result.to_records()
        assert recs[0]["radius_mbc"] > 0
        assert recs[0]["area_mbc"] > 0

    def test_single_point(self):
        frame = _point_frame([(5, 5)])
        recs = frame.minimum_bounding_circle().to_records()
        assert recs[0]["radius_mbc"] == 0.0


# ---- Tool 122: minimum_bounding_rectangle ----
class TestMinimumBoundingRectangle:
    def test_rectangle_dimensions(self):
        rows = [{"site_id": "poly", "geometry": {
            "type": "Polygon",
            "coordinates": [[(0, 0), (10, 0), (10, 5), (0, 5), (0, 0)]]
        }}]
        frame = GeoPromptFrame.from_records(rows)
        result = frame.minimum_bounding_rectangle()
        recs = result.to_records()
        assert recs[0]["width_mbr"] is not None
        assert recs[0]["area_mbr"] is not None
        assert recs[0]["area_mbr"] > 0


# ---- Tool 123: hausdorff_distance ----
class TestHausdorffDistance:
    def test_identical_shapes(self):
        frame = _point_frame([(0, 0), (1, 1)])
        d = frame.hausdorff_distance(frame)
        assert d == pytest.approx(0.0, abs=1e-9)

    def test_different_shapes(self):
        frame1 = _point_frame([(0, 0)])
        frame2 = _point_frame([(10, 0)])
        d = frame1.hausdorff_distance(frame2)
        assert d == pytest.approx(10.0, abs=1e-9)


# ---- Tool 124: snap_to_grid ----
class TestSnapToGrid:
    def test_snaps_coordinates(self):
        frame = _point_frame([(1.7, 2.3), (4.9, 0.1)])
        result = frame.snap_to_grid(cell_size=1.0)
        recs = result.to_records()
        geom0 = recs[0]["geometry"]
        assert geom0["coordinates"][0] == pytest.approx(2.0)
        assert geom0["coordinates"][1] == pytest.approx(2.0)

    def test_invalid_cell_size(self):
        frame = _point_frame([(0, 0)])
        with pytest.raises(ValueError):
            frame.snap_to_grid(cell_size=-1)


# ---- Tool 125: polygon_skeleton ----
class TestPolygonSkeleton:
    def test_skeleton_points(self):
        rows = [{"site_id": "poly", "geometry": {
            "type": "Polygon",
            "coordinates": [[(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]]
        }}]
        frame = GeoPromptFrame.from_records(rows)
        result = frame.polygon_skeleton(step=2.0)
        recs = result.to_records()
        assert recs[0].get("skeleton_count_skel", 0) > 0


# ---- Tool 126: wkt_to_geometry / geometry_to_wkt ----
class TestWKTConversion:
    def test_point_roundtrip(self):
        frame = _point_frame([(1.5, 2.5)])
        wkt_frame = frame.geometry_to_wkt()
        recs = wkt_frame.to_records()
        assert recs[0]["wkt"] == "POINT (1.5 2.5)"

    def test_wkt_parse(self):
        rows = [{"site_id": "a", "wkt": "POINT (3.0 4.0)", "geometry": {"type": "Point", "coordinates": (0, 0)}}]
        frame = GeoPromptFrame.from_records(rows)
        result = frame.wkt_to_geometry("wkt")
        recs = result.to_records()
        assert recs[0]["geometry"]["type"] == "Point"
        assert recs[0]["geometry"]["coordinates"][0] == pytest.approx(3.0)


# ---- Tool 127: spatial_markov ----
class TestSpatialMarkov:
    def test_transition_matrix(self):
        rows = []
        for t in range(3):
            for i in range(10):
                rows.append({
                    "site_id": f"p{i}",
                    "time": t,
                    "value": float(i + t),
                    "geometry": {"type": "Point", "coordinates": (float(i), 0.0)},
                })
        frame = GeoPromptFrame.from_records(rows)
        result = frame.spatial_markov("value", "time", n_classes=3)
        assert "transition_matrix" in result
        assert len(result["transition_matrix"]) == 3
        # Each row should sum to ~1
        for row in result["transition_matrix"]:
            s = sum(row)
            if s > 0:
                assert s == pytest.approx(1.0, abs=0.01)


# ---- Tool 128: spatially_constrained_clustering ----
class TestSpatiallyConstrainedClustering:
    def test_returns_clusters(self):
        pts = [(0, 0), (0, 1), (0, 2), (10, 10), (10, 11), (10, 12)]
        rows = [{"site_id": f"p{i}", "val": float(i),
                 "geometry": {"type": "Point", "coordinates": pts[i]}} for i in range(6)]
        frame = GeoPromptFrame.from_records(rows)
        result = frame.spatially_constrained_clustering(["val"], n_clusters=2, k=2)
        recs = result.to_records()
        assert len(recs) == 6
        assert "cluster_scc" in recs[0]
        clusters = set(r["cluster_scc"] for r in recs)
        assert len(clusters) >= 2


# ---- Tool 129: max_p_regions ----
class TestMaxPRegions:
    def test_assigns_regions(self):
        pts = [(float(i), 0.0) for i in range(10)]
        rows = [{"site_id": f"p{i}", "pop": 100.0,
                 "geometry": {"type": "Point", "coordinates": pts[i]}} for i in range(10)]
        frame = GeoPromptFrame.from_records(rows)
        result = frame.max_p_regions("pop", threshold=250.0, k=2)
        recs = result.to_records()
        assert len(recs) == 10
        assert "region_maxp" in recs[0]


# ---- Tool 130: spatial_regime_model ----
class TestSpatialRegimeModel:
    def test_regime_regression(self):
        rows = []
        for i in range(20):
            regime = "A" if i < 10 else "B"
            rows.append({
                "site_id": f"p{i}",
                "y": float(i * 2 + (1 if regime == "A" else 3)),
                "x": float(i),
                "regime": regime,
                "geometry": {"type": "Point", "coordinates": (float(i), 0.0)},
            })
        frame = GeoPromptFrame.from_records(rows)
        result = frame.spatial_regime_model("y", ["x"], "regime")
        recs = result.to_records()
        assert "predicted_regime" in recs[0]
        assert recs[0]["r_squared_regime"] > 0.5
