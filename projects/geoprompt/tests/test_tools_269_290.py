"""Tests for GeoPromptFrame tools 269-290."""
from __future__ import annotations
import math, pytest
from geoprompt.frame import GeoPromptFrame

def _col(gf: GeoPromptFrame, name: str) -> list:
    return [r[name] for r in gf.to_records()]

def _grid_frame(n: int = 16) -> GeoPromptFrame:
    side = int(n ** 0.5)
    rows = []
    for i in range(n):
        x, y = float(i % side), float(i // side)
        rows.append({
            "geometry": {"type": "Point", "coordinates": (x, y)},
            "value": float(i), "cat": "A" if i % 2 == 0 else "B",
            "weight": float(i + 1), "elev": float(i * 0.5),
            "x_col": float(i * 2), "region": f"r{i % 3}",
            "cluster_a": i % 3, "cluster_b": i % 4,
        })
    return GeoPromptFrame(rows)

def _network_frame() -> GeoPromptFrame:
    edges = [
        ("A", "B", 1.0), ("B", "C", 2.0),
        ("C", "D", 1.5), ("A", "D", 4.0), ("B", "D", 3.0),
    ]
    rows = []
    for f, t, w in edges:
        rows.append({
            "geometry": {"type": "LineString", "coordinates": ((0,0),(1,1))},
            "from_node": f, "to_node": t, "cost": w,
        })
    return GeoPromptFrame(rows)


class TestSLXModel:
    def test_basic(self):
        gf = _grid_frame()
        r = gf.slx_model("value", ["x_col"], k=4)
        recs = r.to_records()
        assert len(recs) == 16
        assert "predicted_slx" in recs[0]
        assert "theta_x_col_slx" in recs[0]  # WX coefficient


class TestSACModel:
    def test_basic(self):
        gf = _grid_frame()
        r = gf.sac_model("value", ["x_col"], k=4, max_iterations=5)
        recs = r.to_records()
        assert len(recs) == 16
        assert "rho_sac" in recs[0]
        assert "lambda_sac" in recs[0]


class TestRegionAutocorrelation:
    def test_basic(self):
        gf = _grid_frame()
        r = gf.region_autocorrelation("region", "value")
        recs = r.to_records()
        assert len(recs) == 3
        assert "moran_I_rac" in recs[0]
        assert "mean_value_rac" in recs[0]


class TestClusterComparison:
    def test_basic(self):
        gf = _grid_frame()
        r = gf.cluster_comparison("cluster_a", "cluster_b")
        recs = r.to_records()
        assert len(recs) == 16
        assert "rand_index_ccmp" in recs[0]
        assert "jaccard_ccmp" in recs[0]
        assert 0.0 <= recs[0]["rand_index_ccmp"] <= 1.0

    def test_same_labels(self):
        gf = _grid_frame()
        r = gf.cluster_comparison("cluster_a", "cluster_a")
        recs = r.to_records()
        assert recs[0]["rand_index_ccmp"] == 1.0


class TestContiguityRepair:
    def test_basic(self):
        gf = _grid_frame()
        # First cluster, then repair
        clustered = gf.constrained_kmeans(n_clusters=4, k_neighbors=3)
        r = clustered.contiguity_repair("cluster_ckm", k=3)
        recs = r.to_records()
        assert len(recs) == 16
        assert "cluster_crep" in recs[0]
        assert "changed_crep" in recs[0]


class TestStreamNetworkSummary:
    def test_basic(self):
        gf = _network_frame()
        r = gf.stream_network_summary()
        recs = r.to_records()
        assert len(recs) == 4  # A, B, C, D
        assert "strahler_order_sns" in recs[0]
        assert "in_degree_sns" in recs[0]


class TestRidgeValleyExtraction:
    def test_basic(self):
        gf = _grid_frame()
        r = gf.ridge_valley_extraction("elev", k=4)
        recs = r.to_records()
        assert len(recs) == 16
        assert "class_rdvl" in recs[0]
        classes = set(_col(r, "class_rdvl"))
        assert classes.issubset({"ridge", "valley", "slope"})


class TestMultiSourceRouting:
    def test_basic(self):
        gf = _network_frame()
        r = gf.multi_source_routing(sources=["A", "D"], weight_column="cost")
        recs = r.to_records()
        assert len(recs) == 4
        assert "nearest_source_msr" in recs[0]
        # A should be nearest to A
        a_rec = [rec for rec in recs if rec["node_msr"] == "A"][0]
        assert a_rec["distance_msr"] == 0.0


class TestRouteSequencing:
    def test_basic(self):
        gf = _network_frame()
        r = gf.route_sequencing(stops=["A", "C", "D"], weight_column="cost")
        recs = r.to_records()
        assert len(recs) > 0
        assert "cumulative_rseq" in recs[0]


class TestFlowAssignment:
    def test_basic(self):
        gf = _network_frame()
        r = gf.flow_assignment(weight_column="cost")
        recs = r.to_records()
        assert len(recs) == 5
        assert "flow_flow" in recs[0]


class TestSurfaceBlending:
    def test_basic(self):
        gf = _grid_frame()
        r = gf.surface_blending(["value", "weight"])
        recs = r.to_records()
        assert len(recs) == 16
        assert "blended_sblnd" in recs[0]
        assert "disagreement_sblnd" in recs[0]

    def test_custom_weights(self):
        gf = _grid_frame()
        r = gf.surface_blending(["value", "weight"], weights=[0.7, 0.3])
        recs = r.to_records()
        assert len(recs) == 16


class TestGridAlgebra:
    def test_basic(self):
        gf = _grid_frame()
        r = gf.grid_algebra("value + weight", output_column="sum")
        recs = r.to_records()
        assert len(recs) == 16
        # First row: value=0, weight=1 → 0+1=1
        assert recs[0]["sum_ralg"] == pytest.approx(1.0, abs=0.01)


class TestGridClip:
    def test_basic(self):
        gf = _grid_frame()
        clip = GeoPromptFrame([
            {"geometry": {"type": "Polygon", "coordinates": ((0, 0), (2, 0), (2, 2), (0, 2), (0, 0))}},
        ])
        r = gf.grid_clip(clip)
        recs = r.to_records()
        assert len(recs) > 0
        assert len(recs) < 16  # Should have clipped some out


class TestRasterSummary:
    def test_basic(self):
        gf = _grid_frame()
        r = gf.raster_summary("value")
        recs = r.to_records()
        assert len(recs) == 1
        assert recs[0]["min_rsum"] == 0.0
        assert recs[0]["max_rsum"] == 15.0
        assert recs[0]["count_rsum"] == 16


class TestGridNeighborhood:
    def test_basic(self):
        gf = _grid_frame()
        r = gf.grid_neighborhood("value", k=4)
        recs = r.to_records()
        assert len(recs) == 16
        assert "nb_mean_gnbr" in recs[0]
        assert "nb_range_gnbr" in recs[0]


class TestLocalMorphology:
    def test_dilate(self):
        gf = _grid_frame()
        r = gf.local_morphology("value", operation="dilate", k=4)
        recs = r.to_records()
        assert len(recs) == 16
        # Dilate (max filter) should be >= original value
        for rec in recs:
            assert rec["morph_lmrp"] >= rec["value"]

    def test_erode(self):
        gf = _grid_frame()
        r = gf.local_morphology("value", operation="erode", k=4)
        recs = r.to_records()
        for rec in recs:
            assert rec["morph_lmrp"] <= rec["value"]


class TestSurfaceThreshold:
    def test_basic(self):
        gf = _grid_frame()
        r = gf.surface_threshold("value", n_classes=3)
        recs = r.to_records()
        assert len(recs) == 16
        classes = set(_col(r, "class_sthr"))
        assert len(classes) >= 2

    def test_custom_breaks(self):
        gf = _grid_frame()
        r = gf.surface_threshold("value", breaks=[5.0, 10.0])
        recs = r.to_records()
        assert recs[0]["class_sthr"] == 0  # value=0 < 5
        assert recs[-1]["class_sthr"] == 2  # value=15 >= 10


class TestFocalStats:
    def test_mean(self):
        gf = _grid_frame()
        r = gf.focal_stats("value", stat="mean", k=4)
        recs = r.to_records()
        assert len(recs) == 16
        assert "focal_mean_fcst" in recs[0]

    def test_max(self):
        gf = _grid_frame()
        r = gf.focal_stats("value", stat="max", k=4)
        recs = r.to_records()
        for rec in recs:
            assert rec["focal_max_fcst"] >= rec["value"]


class TestRegionalizationFeasibility:
    def test_basic(self):
        gf = _grid_frame()
        r = gf.regionalization_feasibility(n_regions=4)
        recs = r.to_records()
        assert len(recs) == 1
        assert recs[0]["feasible_rfeas"] is True
        assert recs[0]["n_features_rfeas"] == 16


class TestLocalInfluence:
    def test_basic(self):
        gf = _grid_frame()
        r = gf.local_influence("value", ["x_col"])
        recs = r.to_records()
        assert len(recs) == 16
        assert "cooks_d_linf" in recs[0]
        assert "leverage_linf" in recs[0]


class TestResidualSpatialDiagnostics:
    def test_basic(self):
        gf = _grid_frame()
        # Add residual column
        rows = gf.to_records()
        for i, row in enumerate(rows):
            row["resid"] = float(i) - 7.5  # centered
        gf2 = GeoPromptFrame(rows)
        r = gf2.residual_spatial_diagnostics("resid", k=4)
        recs = r.to_records()
        assert len(recs) == 16
        assert "local_moran_resid_rsd" in recs[0]
        assert "resid_cluster_rsd" in recs[0]


class TestRegressionReport:
    def test_basic(self):
        gf = _grid_frame()
        r = gf.regression_report("value", ["x_col"])
        recs = r.to_records()
        assert len(recs) == 1
        assert "r_squared_rrpt" in recs[0]
        assert "aic_rrpt" in recs[0]
        assert "durbin_watson_rrpt" in recs[0]
        assert recs[0]["r_squared_rrpt"] > 0.9  # value = x_col/2, should be near-perfect
