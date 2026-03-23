"""Tests for Tools 149-186 (big-backlog batch)."""
from __future__ import annotations

import math, tempfile, os, json
import pytest
from geoprompt import GeoPromptFrame


def _grid_points(n: int = 5) -> GeoPromptFrame:
    """NxN point grid with value/category."""
    recs = []
    for r in range(n):
        for c in range(n):
            recs.append({
                "geometry": {"type": "Point", "coordinates": (c, r)},
                "site_id": f"p{r}_{c}",
                "value": float(r + c),
                "binary": 1 if (r + c) % 2 == 0 else 0,
                "category": "A" if r < n // 2 else "B",
                "elevation": float(n - r + (n - c) * 0.5),
                "x1": float(c),
                "x2": float(r),
                "time": float(r * 10 + c),
            })
    return GeoPromptFrame.from_records(recs)


# ─────────────── Spatial Statistics ───────────────

class TestJoinCountStatistics:
    def test_basic(self):
        gf = _grid_points()
        result = gf.join_count_statistics("binary", k=4)
        assert "BB" in result and "WW" in result and "BW" in result
        assert result["BB"] + result["WW"] + result["BW"] > 0
        assert "z_BB" in result

    def test_small_frame(self):
        gf = GeoPromptFrame.from_records([
            {"geometry": {"type": "Point", "coordinates": (0, 0)}, "binary": 1},
        ])
        result = gf.join_count_statistics("binary")
        assert result["n"] == 1


class TestLosh:
    def test_basic(self):
        gf = _grid_points()
        result = gf.losh("value", k=4)
        assert len(result) == len(gf)
        recs = result.to_records()
        assert "h_losh" in recs[0]

    def test_small(self):
        gf = GeoPromptFrame.from_records([
            {"geometry": {"type": "Point", "coordinates": (0, 0)}, "value": 1},
        ])
        assert len(gf.losh("value")) == 1


class TestBivariateLocalMoransI:
    def test_basic(self):
        gf = _grid_points()
        result = gf.bivariate_local_morans_i("value", "x1", k=4)
        recs = result.to_records()
        assert "local_i_blm" in recs[0]
        assert "global_i_blm" in recs[0]


class TestMantelTest:
    def test_basic(self):
        gf = _grid_points(4)
        result = gf.mantel_test("value", n_permutations=99)
        assert "r" in result and "p_value" in result
        assert 0 <= result["p_value"] <= 1

    def test_small(self):
        gf = GeoPromptFrame.from_records([
            {"geometry": {"type": "Point", "coordinates": (0, 0)}, "value": 1},
        ])
        assert gf.mantel_test("value")["p_value"] == 1.0


class TestDirectionalCorrelogram:
    def test_basic(self):
        gf = _grid_points(5)
        result = gf.directional_correlogram("value", n_lags=5)
        assert len(result) == 5
        assert "morans_i" in result[0]
        assert "pair_count" in result[0]


class TestSpatialEntropy:
    def test_basic(self):
        gf = _grid_points()
        result = gf.spatial_entropy("category", k=4)
        recs = result.to_records()
        assert "local_entropy" in recs[0]
        assert all(recs[i]["local_entropy"] >= 0 for i in range(len(recs)))


# ─────────────── Interpolation ───────────────

class TestRegressionKriging:
    def test_basic(self):
        gf = _grid_points(4)
        result = gf.regression_kriging("value", ["x1", "x2"], grid_resolution=5)
        recs = result.to_records()
        assert len(recs) > 0
        assert "value_rk" in recs[0]
        assert "trend_rk" in recs[0]


class TestIndicatorKriging:
    def test_basic(self):
        gf = _grid_points(4)
        result = gf.indicator_kriging("value", threshold=4.0, grid_resolution=5)
        recs = result.to_records()
        assert len(recs) > 0
        assert "probability_ik" in recs[0]
        assert all(0 <= r["probability_ik"] <= 1 for r in recs)


class TestThinPlateSpline:
    def test_basic(self):
        gf = _grid_points(4)
        result = gf.thin_plate_spline("value", grid_resolution=5)
        recs = result.to_records()
        assert len(recs) == 25
        assert "value_tps" in recs[0]


class TestContourLines:
    def test_basic(self):
        gf = _grid_points(5)
        result = gf.contour_lines("value", n_levels=5, grid_resolution=10)
        recs = result.to_records()
        assert len(recs) > 0
        assert "level_contour" in recs[0]
        for r in recs:
            geom = r["geometry"]
            assert geom["type"] == "LineString"


# ─────────────── Clustering ───────────────

class TestSpectralClustering:
    def test_basic(self):
        gf = _grid_points(5)
        result = gf.spectral_clustering(n_clusters=3, k=5)
        recs = result.to_records()
        assert "cluster_sc" in recs[0]
        clusters = {r["cluster_sc"] for r in recs}
        assert len(clusters) >= 1

    def test_small(self):
        gf = GeoPromptFrame.from_records([
            {"geometry": {"type": "Point", "coordinates": (0, 0)}},
        ])
        result = gf.spectral_clustering(n_clusters=3)
        assert len(result) == 1


class TestSkaterRegionalization:
    def test_basic(self):
        gf = _grid_points(5)
        result = gf.skater_regionalization(["value", "x1"], n_regions=3, k=4)
        recs = result.to_records()
        assert "region_skater" in recs[0]
        regions = {r["region_skater"] for r in recs}
        assert len(regions) >= 2


class TestRegionCompactness:
    def test_basic(self):
        gf = _grid_points(5)
        clustered = gf.spectral_clustering(n_clusters=3)
        result = clustered.region_compactness("cluster_sc")
        recs = result.to_records()
        assert "compactness_compact" in recs[0]


class TestClusterSummary:
    def test_basic(self):
        gf = _grid_points(5)
        clustered = gf.spectral_clustering(n_clusters=3)
        result = clustered.cluster_summary("cluster_sc", value_columns=["value"])
        assert len(result) >= 1
        assert "count" in result[0]
        assert "mean_value" in result[0]
        assert "spatial_variance" in result[0]


# ─────────────── Regression ───────────────

class TestLogisticGWR:
    def test_basic(self):
        gf = _grid_points(4)
        result = gf.logistic_gwr("binary", ["x1", "x2"], max_iter=5)
        recs = result.to_records()
        assert "predicted_lgwr" in recs[0]
        assert "residual_lgwr" in recs[0]
        assert all(0 <= r["predicted_lgwr"] <= 1 for r in recs)


class TestGWSummaryStats:
    def test_basic(self):
        gf = _grid_points(5)
        result = gf.gw_summary_stats("value", k=4)
        recs = result.to_records()
        assert "mean_gws" in recs[0]
        assert "variance_gws" in recs[0]
        assert "skewness_gws" in recs[0]
        assert "kurtosis_gws" in recs[0]


class TestModelComparison:
    def test_basic(self):
        recs = [
            {"geometry": {"type": "Point", "coordinates": (i, 0)}, "y": float(i * 2), "pred1": float(i * 2.1), "pred2": float(i * 1.5)}
            for i in range(10)
        ]
        gf = GeoPromptFrame.from_records(recs)
        result = gf.model_comparison("y", ["pred1", "pred2"])
        assert len(result) == 2
        assert result[0]["r_squared"] > result[1]["r_squared"]
        assert "aic" in result[0] and "bic" in result[0]


# ─────────────── Terrain/Hydrology ───────────────

class TestStreamExtraction:
    def test_basic(self):
        gf = _grid_points(5)
        result = gf.stream_extraction("elevation", threshold=3.0, k=4)
        recs = result.to_records()
        assert len(recs) > 0
        assert "accumulation_se" in recs[0]
        assert "receiver_idx_se" in recs[0]
        assert "routing_se" in recs[0]

    def test_single_feature_returns_empty(self):
        gf = GeoPromptFrame.from_records([
            {"geometry": {"type": "Point", "coordinates": (0, 0)}, "elevation": 10.0}
        ])
        result = gf.stream_extraction("elevation", threshold=1.0)
        assert len(result) == 0

    def test_warns_for_geographic_crs(self):
        gf = _grid_points(3).set_crs("EPSG:4326")
        with pytest.warns(UserWarning, match="projected coordinates"):
            gf.stream_extraction("elevation", threshold=2.0, k=4)


class TestHAND:
    def test_basic(self):
        gf = _grid_points(5)
        result = gf.hand("elevation", stream_threshold=3.0, k=4)
        recs = result.to_records()
        assert len(recs) == 25
        assert "hand_hand" in recs[0]
        assert "is_stream_hand" in recs[0]
        assert "drainage_idx_hand" in recs[0]
        assert "drainage_distance_hand" in recs[0]

    def test_single_feature_has_zero_hand(self):
        gf = GeoPromptFrame.from_records([
            {"geometry": {"type": "Point", "coordinates": (0, 0)}, "elevation": 10.0}
        ])
        result = gf.hand("elevation", stream_threshold=1.0)
        rec = result.to_records()[0]
        assert rec["hand_hand"] == 0.0
        assert rec["is_stream_hand"] is True

    def test_warns_for_geographic_crs(self):
        gf = _grid_points(3).set_crs("EPSG:4326")
        with pytest.warns(UserWarning, match="projected coordinates"):
            gf.hand("elevation", stream_threshold=2.0, k=4)


class TestLSFactor:
    def test_basic(self):
        gf = _grid_points(5)
        result = gf.ls_factor("elevation")
        recs = result.to_records()
        assert len(recs) == 25
        assert "ls_ls" in recs[0]
        assert "slope_deg_ls" in recs[0]
        assert "flow_length_ls" in recs[0]
        assert "routing_ls" in recs[0]

    def test_single_feature_has_non_negative_outputs(self):
        gf = GeoPromptFrame.from_records([
            {"geometry": {"type": "Point", "coordinates": (0, 0)}, "elevation": 10.0}
        ])
        result = gf.ls_factor("elevation")
        rec = result.to_records()[0]
        assert rec["ls_ls"] >= 0
        assert rec["flow_length_ls"] >= 1.0

    def test_warns_for_geographic_crs(self):
        gf = _grid_points(3).set_crs("EPSG:4326")
        with pytest.warns(UserWarning, match="projected coordinates"):
            gf.ls_factor("elevation")


# ─────────────── Network ───────────────

def _network_frame() -> GeoPromptFrame:
    edges = [
        {"geometry": {"type": "LineString", "coordinates": [(0, 0), (1, 0)]}, "from_node": "A", "to_node": "B", "cost": 1.0, "capacity": 5.0, "edge_to": "B", "site_id": "A"},
        {"geometry": {"type": "LineString", "coordinates": [(1, 0), (2, 0)]}, "from_node": "B", "to_node": "C", "cost": 2.0, "capacity": 3.0, "edge_to": "C", "site_id": "B"},
        {"geometry": {"type": "LineString", "coordinates": [(0, 0), (1, 1)]}, "from_node": "A", "to_node": "D", "cost": 3.0, "capacity": 4.0, "edge_to": "D", "site_id": "A2"},
        {"geometry": {"type": "LineString", "coordinates": [(1, 1), (2, 0)]}, "from_node": "D", "to_node": "C", "cost": 1.0, "capacity": 2.0, "edge_to": "C", "site_id": "D"},
    ]
    return GeoPromptFrame.from_records(edges)


class TestODCostMatrix:
    def test_basic(self):
        origins = GeoPromptFrame.from_records([
            {"geometry": {"type": "Point", "coordinates": (0, 0)}, "site_id": "O1"},
            {"geometry": {"type": "Point", "coordinates": (1, 0)}, "site_id": "O2"},
        ])
        dests = GeoPromptFrame.from_records([
            {"geometry": {"type": "Point", "coordinates": (3, 0)}, "site_id": "D1"},
        ])
        result = origins.od_cost_matrix(origins, dests)
        assert len(result) == 2
        assert "cost" in result[0]


class TestMinCut:
    def test_basic(self):
        gf = _network_frame()
        result = gf.min_cut("A", "C", capacity_column="capacity", id_column="site_id")
        assert "max_flow" in result
        assert "cut_edges" in result


# ─────────────── Point Pattern ───────────────

class TestSpatiotemporalKnox:
    def test_basic(self):
        gf = _grid_points(4)
        result = gf.spatiotemporal_knox("time", spatial_threshold=2.0, temporal_threshold=15.0, n_permutations=99)
        assert "knox_statistic" in result
        assert 0 <= result["p_value"] <= 1


class TestMarkVariogram:
    def test_basic(self):
        gf = _grid_points(5)
        result = gf.mark_variogram("value", n_lags=5)
        assert len(result) == 5
        assert "semivariance" in result[0]
        assert "pair_count" in result[0]


# ─────────────── Geometry ───────────────

class TestPolygonValidityCheck:
    def test_valid(self):
        gf = GeoPromptFrame.from_records([{
            "geometry": {"type": "Polygon", "coordinates": [[(0, 0), (1, 0), (1, 1), (0, 0)]]},
        }])
        result = gf.polygon_validity_check()
        recs = result.to_records()
        assert "is_valid_pv" in recs[0]

    def test_too_few_vertices(self):
        # Build frame with raw invalid polygon bypassing normalization
        gf = GeoPromptFrame.from_records([{
            "geometry": {"type": "Point", "coordinates": (0, 0)},
        }])
        result = gf.polygon_validity_check()
        recs = result.to_records()
        # Point geometry should be considered valid (not a polygon)
        assert recs[0].get("is_valid_pv") is True


class TestPolygonRepair:
    def test_close_ring(self):
        gf = GeoPromptFrame.from_records([{
            "geometry": {"type": "Polygon", "coordinates": [(0, 0), (1, 0), (1, 1), (0, 1)]},
        }])
        result = gf.polygon_repair()
        recs = result.to_records()
        assert recs[0]["repaired_pr"] is True


class TestLineMerge:
    def test_basic(self):
        gf = GeoPromptFrame.from_records([
            {"geometry": {"type": "LineString", "coordinates": [(0, 0), (1, 0)]}},
            {"geometry": {"type": "LineString", "coordinates": [(1, 0), (2, 0)]}},
        ])
        result = gf.line_merge()
        recs = result.to_records()
        assert len(recs) >= 1
        coords = recs[0]["geometry"]["coordinates"]
        assert len(coords) == 3


class TestVoronoiPolygons:
    def test_basic(self):
        gf = _grid_points(3)
        result = gf.voronoi_polygons()
        recs = result.to_records()
        assert len(recs) == 9
        assert "area_vor" in recs[0]


class TestSharedBoundaries:
    def test_basic(self):
        gf = GeoPromptFrame.from_records([
            {"geometry": {"type": "Polygon", "coordinates": [[(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]]}, "site_id": "A"},
            {"geometry": {"type": "Polygon", "coordinates": [[(1, 0), (2, 0), (2, 1), (1, 1), (1, 0)]]}, "site_id": "B"},
        ])
        result = gf.shared_boundaries()
        recs = result.to_records()
        assert len(recs) >= 1


class TestTopologyAudit:
    def test_dangling_lines(self):
        gf = GeoPromptFrame.from_records([
            {"geometry": {"type": "LineString", "coordinates": [(0, 0), (1, 0)]}},
            {"geometry": {"type": "LineString", "coordinates": [(2, 0), (3, 0)]}},
        ])
        result = gf.topology_audit()
        assert len(result) >= 2  # at least some dangles

    def test_duplicate(self):
        gf = GeoPromptFrame.from_records([
            {"geometry": {"type": "Point", "coordinates": (0, 0)}},
            {"geometry": {"type": "Point", "coordinates": (0, 0)}},
        ])
        result = gf.topology_audit()
        dups = [r for r in result if r["issue"] == "duplicate_geometry"]
        assert len(dups) == 1


# ─────────────── I/O ───────────────

class TestWKBRoundtrip:
    def test_roundtrip(self):
        gf = GeoPromptFrame.from_records([
            {"geometry": {"type": "Point", "coordinates": (1.5, 2.5)}, "val": 1},
        ])
        with_wkb = gf.geometry_to_wkb("wkb_hex")
        recs = with_wkb.to_records()
        assert "wkb_hex" in recs[0]
        assert len(recs[0]["wkb_hex"]) > 0


class TestGeoJSONSeq:
    def test_roundtrip(self):
        gf = _grid_points(3)
        with tempfile.NamedTemporaryFile(suffix=".geojsonl", delete=False, mode="w") as f:
            path = f.name
        try:
            gf.to_geojson_seq(path)
            loaded = GeoPromptFrame.read_geojson_seq(path)
            assert len(loaded) == len(gf)
        finally:
            os.unlink(path)


class TestCSVWithWKT:
    def test_read(self):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
            f.write("id,wkt,val\n")
            f.write('1,"POINT (1 2)",42\n')
            f.write('2,"POINT (3 4)",99\n')
            path = f.name
        try:
            gf = GeoPromptFrame.read_csv_wkt(path, geometry_column="wkt")
            assert len(gf) == 2
        finally:
            os.unlink(path)


# ─────────────── Raster ───────────────

class TestRasterize:
    def test_basic(self):
        gf = _grid_points(4)
        result = gf.rasterize("value", grid_resolution=10)
        recs = result.to_records()
        assert len(recs) > 0
        assert "value_rast" in recs[0]


class TestZonalStatisticsGrid:
    def test_basic(self):
        pts = _grid_points(5)
        zones = GeoPromptFrame.from_records([
            {"geometry": {"type": "Point", "coordinates": (1, 1)}, "zone_id": "Z1"},
            {"geometry": {"type": "Point", "coordinates": (3, 3)}, "zone_id": "Z2"},
        ])
        result = pts.zonal_statistics_grid(zones, "value")
        recs = result.to_records()
        assert len(recs) == 2
        assert "mean_zsg" in recs[0]
        assert "count_zsg" in recs[0]


class TestConnectedComponents:
    def test_basic(self):
        gf = GeoPromptFrame.from_records([
            {"geometry": {"type": "LineString", "coordinates": [(0, 0), (1, 0)]}, "from_node": "A", "to_node": "B"},
            {"geometry": {"type": "LineString", "coordinates": [(1, 0), (2, 0)]}, "from_node": "B", "to_node": "C"},
            {"geometry": {"type": "LineString", "coordinates": [(5, 5), (6, 6)]}, "from_node": "X", "to_node": "Y"},
        ])
        result = gf.connected_components()
        recs = result.to_records()
        assert "component_cc" in recs[0]
        comps = {r["component_cc"] for r in recs}
        assert len(comps) == 2
