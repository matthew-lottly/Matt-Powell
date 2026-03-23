"""Tests for tools 223-245."""

from __future__ import annotations

import pytest
from geoprompt import GeoPromptFrame


def _col(gf: GeoPromptFrame, name: str) -> list:
    return [r[name] for r in gf.to_records()]


def _grid_frame() -> GeoPromptFrame:
    """4×4 point grid with elevation, category, value, residual, time columns."""
    rows = []
    cats = ["A", "B", "C", "D"]
    for i in range(4):
        for j in range(4):
            rows.append({
                "geometry": {"type": "Point", "coordinates": (float(i), float(j))},
                "elevation": float(i + j),
                "category": cats[(i + j) % 4],
                "value": float(i * 10 + j),
                "value2": float((i + 1) * (j + 1)),
                "residual": float(i - j) * 0.5,
                "time": float(i + j * 0.1),
                "x1": float(i),
                "x2": float(j),
            })
    return GeoPromptFrame(rows)


def _network_frame() -> GeoPromptFrame:
    """6-edge directed network A->B->C->D, A->E->D, E->F."""
    edges = [
        ("A", "B", 1.0), ("B", "C", 2.0), ("C", "D", 1.0),
        ("A", "E", 3.0), ("E", "D", 1.0), ("E", "F", 2.0),
    ]
    rows = []
    for f, t, w in edges:
        rows.append({
            "geometry": {"type": "LineString", "coordinates": [[0, 0], [1, 1]]},
            "from_node": f, "to_node": t, "weight": w,
        })
    return GeoPromptFrame(rows)


def _polygon_frame() -> GeoPromptFrame:
    """Two adjacent triangles with small gap for repair testing."""
    return GeoPromptFrame([
        {"geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [0.5, 1], [0, 0]]]}},
        {"geometry": {"type": "Polygon", "coordinates": [[[1.0001, 0], [2, 0], [1.5, 1], [1.0001, 0]]]}},
    ])


# ---------------------------------------------------------------
# Tool 223: directional_variogram
# ---------------------------------------------------------------
class TestDirectionalVariogram:
    def test_basic(self):
        gf = _grid_frame()
        result = gf.directional_variogram("value", n_lags=3, n_directions=4)
        assert len(result) == 12  # 3 lags × 4 directions
        assert "semivariance_dvar" in result.to_records()[0]

    def test_custom_suffix(self):
        gf = _grid_frame()
        result = gf.directional_variogram("value", n_lags=2, n_directions=2, dv_suffix="dv2")
        assert "semivariance_dv2" in result.to_records()[0]

    def test_small_frame(self):
        gf = GeoPromptFrame([{"geometry": {"type": "Point", "coordinates": (0, 0)}, "v": 1}])
        result = gf.directional_variogram("v")
        assert len(result) > 0  # returns original row


# ---------------------------------------------------------------
# Tool 224: distance_band_scan
# ---------------------------------------------------------------
class TestDistanceBandScan:
    def test_basic(self):
        gf = _grid_frame()
        result = gf.distance_band_scan("value", n_bands=3, permutations=9)
        assert len(result) == 3
        rec = result.to_records()[0]
        assert "morans_I_dbs" in rec
        assert "pseudo_p_dbs" in rec
        assert "significant_dbs" in rec

    def test_small_frame(self):
        gf = GeoPromptFrame([
            {"geometry": {"type": "Point", "coordinates": (0, 0)}, "v": 1},
            {"geometry": {"type": "Point", "coordinates": (1, 1)}, "v": 2},
        ])
        result = gf.distance_band_scan("v", n_bands=2, permutations=9)
        assert len(result) == 0  # n<3


# ---------------------------------------------------------------
# Tool 225: local_entropy
# ---------------------------------------------------------------
class TestLocalEntropy:
    def test_basic(self):
        gf = _grid_frame()
        result = gf.local_entropy("category", k=3)
        recs = result.to_records()
        assert len(recs) == 16
        assert "entropy_lent" in recs[0]
        assert "norm_entropy_lent" in recs[0]
        assert "class_count_lent" in recs[0]

    def test_entropy_nonzero(self):
        gf = _grid_frame()
        result = gf.local_entropy("category", k=5)
        entropies = _col(result, "entropy_lent")
        assert any(e > 0 for e in entropies)


# ---------------------------------------------------------------
# Tool 226: spatial_inequality
# ---------------------------------------------------------------
class TestSpatialInequality:
    def test_basic(self):
        gf = _grid_frame()
        result = gf.spatial_inequality("category", k=4)
        recs = result.to_records()
        assert len(recs) == 16
        assert "dissimilarity_sineq" in recs[0]
        assert "isolation_sineq" in recs[0]
        assert "exposure_sineq" in recs[0]

    def test_values_in_range(self):
        gf = _grid_frame()
        result = gf.spatial_inequality("category", k=4)
        for r in result.to_records():
            assert 0.0 <= r["dissimilarity_sineq"] <= 1.0
            assert 0.0 <= r["isolation_sineq"] <= 1.0


# ---------------------------------------------------------------
# Tool 227: hierarchical_spatial_cluster
# ---------------------------------------------------------------
class TestHierarchicalSpatialCluster:
    def test_basic(self):
        gf = _grid_frame()
        result = gf.hierarchical_spatial_cluster(n_clusters=3, k=4)
        labels = _col(result, "cluster_hsc")
        assert len(labels) == 16
        assert len(set(labels)) <= 3

    def test_with_value(self):
        gf = _grid_frame()
        result = gf.hierarchical_spatial_cluster(n_clusters=2, k=4, value_column="value")
        labels = _col(result, "cluster_hsc")
        assert len(set(labels)) <= 2


# ---------------------------------------------------------------
# Tool 228: constrained_kmeans
# ---------------------------------------------------------------
class TestConstrainedKmeans:
    def test_basic(self):
        gf = _grid_frame()
        result = gf.constrained_kmeans(n_clusters=3, k_neighbors=4)
        labels = _col(result, "cluster_ckm")
        assert len(labels) == 16
        assert len(set(labels)) <= 3

    def test_all_assigned(self):
        gf = _grid_frame()
        result = gf.constrained_kmeans(n_clusters=4, k_neighbors=4)
        labels = _col(result, "cluster_ckm")
        assert all(l >= 0 for l in labels)


# ---------------------------------------------------------------
# Tool 229: cluster_stability
# ---------------------------------------------------------------
class TestClusterStability:
    def test_basic(self):
        gf = _grid_frame()
        gf = gf.constrained_kmeans(n_clusters=3, k_neighbors=4)
        result = gf.cluster_stability("cluster_ckm", n_runs=3, subsample_fraction=0.7)
        recs = result.to_records()
        assert "stability_cstab" in recs[0]
        assert "stable_cstab" in recs[0]

    def test_values_in_range(self):
        gf = _grid_frame().constrained_kmeans(n_clusters=2, k_neighbors=4)
        result = gf.cluster_stability("cluster_ckm", n_runs=3, subsample_fraction=0.7)
        for r in result.to_records():
            assert 0.0 <= r["stability_cstab"] <= 1.0


# ---------------------------------------------------------------
# Tool 230: local_collinearity
# ---------------------------------------------------------------
class TestLocalCollinearity:
    def test_basic(self):
        gf = _grid_frame()
        result = gf.local_collinearity(x_columns=["x1", "x2"], k=5)
        recs = result.to_records()
        assert "condition_number_lcol" in recs[0]
        assert "collinear_lcol" in recs[0]

    def test_condition_positive(self):
        gf = _grid_frame()
        result = gf.local_collinearity(x_columns=["x1", "x2"], k=8)
        for r in result.to_records():
            assert r["condition_number_lcol"] >= 0


# ---------------------------------------------------------------
# Tool 231: local_heteroskedasticity
# ---------------------------------------------------------------
class TestLocalHeteroskedasticity:
    def test_basic(self):
        gf = _grid_frame()
        result = gf.local_heteroskedasticity("residual", k=5)
        recs = result.to_records()
        assert "bp_stat_lhet" in recs[0]
        assert "heteroskedastic_lhet" in recs[0]

    def test_local_variance_present(self):
        gf = _grid_frame()
        result = gf.local_heteroskedasticity("residual", k=5)
        assert "local_variance_lhet" in result.to_records()[0]


# ---------------------------------------------------------------
# Tool 232: quantile_regression_local
# ---------------------------------------------------------------
class TestQuantileRegressionLocal:
    def test_basic(self):
        gf = _grid_frame()
        result = gf.quantile_regression_local("value", x_columns=["x1", "x2"], quantile=0.5, k=10)
        recs = result.to_records()
        assert "beta_intercept_qrl" in recs[0]
        assert "beta_x1_qrl" in recs[0]
        assert "predicted_qrl" in recs[0]

    def test_different_quantile(self):
        gf = _grid_frame()
        r1 = gf.quantile_regression_local("value", x_columns=["x1"], quantile=0.25, k=10)
        r2 = gf.quantile_regression_local("value", x_columns=["x1"], quantile=0.75, k=10)
        # Different quantiles should give different predictions generally
        p1 = _col(r1, "predicted_qrl")
        p2 = _col(r2, "predicted_qrl")
        assert p1 != p2 or all(v == 0.0 for v in p1)  # at minimum not crashing


# ---------------------------------------------------------------
# Tool 233: viewshed_points
# ---------------------------------------------------------------
class TestViewshedPoints:
    def test_basic(self):
        gf = _grid_frame()
        result = gf.viewshed_points("elevation", observer_index=0, k=4)
        recs = result.to_records()
        assert len(recs) == 16
        assert "visible_vs" in recs[0]
        assert "distance_to_observer_vs" in recs[0]

    def test_observer_visible(self):
        gf = _grid_frame()
        result = gf.viewshed_points("elevation", observer_index=0)
        assert _col(result, "visible_vs")[0] is True


# ---------------------------------------------------------------
# Tool 234: intervisibility
# ---------------------------------------------------------------
class TestIntervisibility:
    def test_basic(self):
        gf = GeoPromptFrame([
            {"geometry": {"type": "Point", "coordinates": (0, 0)}, "elev": 10},
            {"geometry": {"type": "Point", "coordinates": (1, 0)}, "elev": 10},
            {"geometry": {"type": "Point", "coordinates": (2, 0)}, "elev": 10},
        ])
        result = gf.intervisibility("elev")
        assert len(result) > 0
        assert "from_iv" in result.to_records()[0]
        assert "distance_iv" in result.to_records()[0]

    def test_small_frame(self):
        gf = GeoPromptFrame([{"geometry": {"type": "Point", "coordinates": (0, 0)}, "elev": 5}])
        result = gf.intervisibility("elev")
        assert len(result) == 0  # n<2


# ---------------------------------------------------------------
# Tool 235: least_cost_surface
# ---------------------------------------------------------------
class TestLeastCostSurface:
    def test_basic(self):
        gf = _grid_frame()
        result = gf.least_cost_surface("value", origin_index=0, k=4)
        recs = result.to_records()
        assert "acc_cost_lcs" in recs[0]
        assert "reachable_lcs" in recs[0]

    def test_origin_zero_cost(self):
        gf = _grid_frame()
        result = gf.least_cost_surface("value", origin_index=0, k=4)
        assert _col(result, "acc_cost_lcs")[0] == 0.0


# ---------------------------------------------------------------
# Tool 236: edge_criticality
# ---------------------------------------------------------------
class TestEdgeCriticality:
    def test_basic(self):
        gf = _network_frame()
        result = gf.edge_criticality(weight_column="weight")
        recs = result.to_records()
        assert len(recs) == 6
        assert "criticality_ecrit" in recs[0]
        assert "critical_ecrit" in recs[0]


# ---------------------------------------------------------------
# Tool 237: network_resilience
# ---------------------------------------------------------------
class TestNetworkResilience:
    def test_basic(self):
        gf = _network_frame()
        result = gf.network_resilience(weight_column="weight")
        recs = result.to_records()
        assert len(recs) > 0
        assert "degree_nres" in recs[0]
        assert "betweenness_nres" in recs[0]
        assert "resilience_nres" in recs[0]

    def test_resilience_in_range(self):
        gf = _network_frame()
        result = gf.network_resilience()
        for r in result.to_records():
            assert 0.0 <= r["resilience_nres"] <= 1.0


# ---------------------------------------------------------------
# Tool 238: route_barriers
# ---------------------------------------------------------------
class TestRouteBarriers:
    def test_basic(self):
        gf = _network_frame()
        result = gf.route_barriers(origin="A", destination="D")
        assert len(result) > 0
        rec = result.to_records()[0]
        assert "from_rb" in rec
        assert "to_rb" in rec

    def test_with_blocked(self):
        gf = _network_frame()
        # Block A->B so must go through E
        result = gf.route_barriers(origin="A", destination="D", blocked_edges=[("A", "B")])
        froms = _col(result, "from_rb")
        assert "B" not in froms or "A" not in froms  # path avoids A->B edge

    def test_unreachable(self):
        gf = _network_frame()
        result = gf.route_barriers(origin="A", destination="Z")
        assert len(result) == 0


# ---------------------------------------------------------------
# Tool 239: quadrat_grid
# ---------------------------------------------------------------
class TestQuadratGrid:
    def test_basic(self):
        gf = _grid_frame()
        result = gf.quadrat_grid(n_x=3, n_y=3)
        assert len(result) == 9
        rec = result.to_records()[0]
        assert "count_qa" in rec
        assert "vmr_qa" in rec

    def test_counts_sum(self):
        gf = _grid_frame()
        result = gf.quadrat_grid(n_x=2, n_y=2)
        total = sum(_col(result, "count_qa"))
        assert total == 16


# ---------------------------------------------------------------
# Tool 240: space_time_k
# ---------------------------------------------------------------
class TestSpaceTimeK:
    def test_basic(self):
        gf = _grid_frame()
        result = gf.space_time_k("time", n_distance_bins=3, n_time_bins=3)
        assert len(result) == 9
        rec = result.to_records()[0]
        assert "K_stk" in rec
        assert "pair_count_stk" in rec


# ---------------------------------------------------------------
# Tool 241: mesh_subdivision
# ---------------------------------------------------------------
class TestMeshSubdivision:
    def test_triangle_subdivision(self):
        gf = GeoPromptFrame([{
            "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [0.5, 1], [0, 0]]]},
        }])
        result = gf.mesh_subdivision(iterations=1)
        assert len(result) == 4  # triangle -> 4 sub-triangles

    def test_two_iterations(self):
        gf = GeoPromptFrame([{
            "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [0.5, 1], [0, 0]]]},
        }])
        result = gf.mesh_subdivision(iterations=2)
        assert len(result) == 16  # 4^2

    def test_non_polygon_passthrough(self):
        gf = GeoPromptFrame([{"geometry": {"type": "Point", "coordinates": (0, 0)}}])
        result = gf.mesh_subdivision(iterations=1)
        assert len(result) == 1


# ---------------------------------------------------------------
# Tool 242: gap_overlap_repair
# ---------------------------------------------------------------
class TestGapOverlapRepair:
    def test_basic(self):
        gf = _polygon_frame()
        result = gf.gap_overlap_repair(tolerance=0.01)
        recs = result.to_records()
        assert len(recs) == 2
        assert "snapped_gor" in recs[0]

    def test_non_polygon(self):
        gf = GeoPromptFrame([{"geometry": {"type": "Point", "coordinates": (0, 0)}}])
        result = gf.gap_overlap_repair()
        assert result.to_records()[0]["snapped_gor"] is False


# ---------------------------------------------------------------
# Tool 243: nodata_mask
# ---------------------------------------------------------------
class TestNodataMask:
    def test_basic(self):
        rows = [
            {"geometry": {"type": "Point", "coordinates": (i, 0)}, "v": -9999.0 if i < 2 else float(i)}
            for i in range(5)
        ]
        gf = GeoPromptFrame(rows)
        result = gf.nodata_mask("v", nodata_value=-9999.0)
        mask = _col(result, "is_nodata_ndm")
        assert mask[0] is True
        assert mask[1] is True
        assert mask[4] is False

    def test_masked_value_none(self):
        rows = [
            {"geometry": {"type": "Point", "coordinates": (i, 0)}, "v": -9999.0 if i == 0 else 5.0}
            for i in range(3)
        ]
        gf = GeoPromptFrame(rows)
        result = gf.nodata_mask("v")
        recs = result.to_records()
        assert recs[0]["masked_value_ndm"] is None
        assert recs[1]["masked_value_ndm"] == 5.0


# ---------------------------------------------------------------
# Tool 244: grid_resample
# ---------------------------------------------------------------
class TestGridResample:
    def test_nearest(self):
        gf = _grid_frame()
        result = gf.grid_resample("elevation", target_resolution=5, method="nearest")
        assert len(result) == 25  # 5×5

    def test_bilinear(self):
        gf = _grid_frame()
        result = gf.grid_resample("elevation", target_resolution=4, method="bilinear")
        assert len(result) == 16
        vals = _col(result, "value_grs")
        assert all(isinstance(v, float) for v in vals)


# ---------------------------------------------------------------
# Tool 245: surface_difference
# ---------------------------------------------------------------
class TestSurfaceDifference:
    def test_basic(self):
        gf = _grid_frame()
        result = gf.surface_difference("value", "value2")
        recs = result.to_records()
        assert "diff_sdif" in recs[0]
        assert "abs_diff_sdif" in recs[0]
        assert "rmse_sdif" in recs[0]
        assert "mae_sdif" in recs[0]

    def test_same_surface_zero_diff(self):
        gf = _grid_frame()
        result = gf.surface_difference("value", "value")
        diffs = _col(result, "diff_sdif")
        assert all(d == 0.0 for d in diffs)

    def test_ratio(self):
        gf = _grid_frame()
        result = gf.surface_difference("value", "value2")
        recs = result.to_records()
        # ratio should be value/value2 for non-zero value2
        for r in recs:
            if r["ratio_sdif"] is not None:
                assert isinstance(r["ratio_sdif"], float)
