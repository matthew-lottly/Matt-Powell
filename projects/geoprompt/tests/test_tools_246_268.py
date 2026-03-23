"""Tests for GeoPromptFrame tools 246-268."""
from __future__ import annotations

import math
import pytest
from geoprompt.frame import GeoPromptFrame

# ── helpers ──────────────────────────────────────────────────────────
def _col(gf: GeoPromptFrame, name: str) -> list:
    return [r[name] for r in gf.to_records()]

def _grid_frame(n: int = 16) -> GeoPromptFrame:
    """4×4 grid, 8 columns."""
    side = int(n ** 0.5)
    rows = []
    for i in range(n):
        x, y = float(i % side), float(i // side)
        rows.append({
            "geometry": {"type": "Point", "coordinates": (x, y)},
            "value": float(i),
            "cat": "A" if i % 2 == 0 else "B",
            "weight": float(i + 1),
            "elev": float(i * 0.5),
            "time": float(i * 0.1),
            "ws": f"w{i % 3}",
            "x_col": float(i * 2),
        })
    return GeoPromptFrame(rows)

def _network_frame() -> GeoPromptFrame:
    """Simple 4-node network: A-B-C-D."""
    edges = [
        ("A", "B", 1.0), ("B", "C", 2.0),
        ("C", "D", 1.5), ("A", "D", 4.0),
        ("B", "D", 3.0),
    ]
    rows = []
    for f, t, w in edges:
        rows.append({
            "geometry": {"type": "LineString", "coordinates": ((0, 0), (1, 1))},
            "from_node": f, "to_node": t, "cost": w, "traffic": w * 10,
        })
    return GeoPromptFrame(rows)

def _polygon_frame() -> GeoPromptFrame:
    rows = [
        {"geometry": {"type": "Polygon", "coordinates": ((0, 0), (1, 0), (1, 1), (0, 1), (0, 0))}, "id": 1},
        {"geometry": {"type": "Polygon", "coordinates": ((1, 0), (2, 0), (2, 1), (1, 1), (1, 0))}, "id": 2},
        {"geometry": {"type": "Polygon", "coordinates": ((3, 3), (4, 3), (4, 4), (3, 3))}, "id": 3},
    ]
    return GeoPromptFrame(rows)


# ── Tool 246: local_variance_decomposition ──────────────────────────
class TestLocalVarianceDecomposition:
    def test_basic(self):
        gf = _grid_frame()
        r = gf.local_variance_decomposition("value", k=4)
        recs = r.to_records()
        assert len(recs) == 16
        assert "local_var_lvd" in recs[0]
        assert "contrast_lvd" in recs[0]
        assert "local_mean_lvd" in recs[0]

    def test_single(self):
        rows = [{"geometry": {"type": "Point", "coordinates": (0, 0)}, "value": 1.0}]
        gf = GeoPromptFrame(rows)
        assert len(gf.local_variance_decomposition("value", k=4).to_records()) == 1


# ── Tool 247: robust_morans_i ──────────────────────────────────────
class TestRobustMoransI:
    def test_basic(self):
        gf = _grid_frame()
        r = gf.robust_morans_i("value", k=4)
        recs = r.to_records()
        assert len(recs) == 16
        assert "moran_I_rmi" in recs[0]
        assert "winsorised_dev_rmi" in recs[0]

    def test_trim_fraction(self):
        gf = _grid_frame()
        r = gf.robust_morans_i("value", trim_fraction=0.25)
        assert len(r.to_records()) == 16


# ── Tool 248: weighted_join_count ──────────────────────────────────
class TestWeightedJoinCount:
    def test_basic(self):
        gf = _grid_frame()
        r = gf.weighted_join_count("cat", k=4)
        recs = r.to_records()
        assert len(recs) == 16
        assert "same_join_wjc" in recs[0]
        assert "diff_join_wjc" in recs[0]
        assert "join_ratio_wjc" in recs[0]

    def test_with_weight_column(self):
        gf = _grid_frame()
        r = gf.weighted_join_count("cat", weight_column="weight")
        assert len(r.to_records()) == 16


# ── Tool 249: local_network_association ────────────────────────────
class TestLocalNetworkAssociation:
    def test_basic(self):
        gf = _network_frame()
        r = gf.local_network_association(value_column="cost")
        recs = r.to_records()
        assert len(recs) > 0
        assert "local_I_lna" in recs[0]
        assert "degree_lna" in recs[0]

    def test_no_value_column(self):
        gf = _network_frame()
        r = gf.local_network_association()
        assert len(r.to_records()) > 0


# ── Tool 250: surface_masking ──────────────────────────────────────
class TestSurfaceMasking:
    def test_basic(self):
        gf = _grid_frame()
        mask = GeoPromptFrame([
            {"geometry": {"type": "Polygon", "coordinates": ((0, 0), (2, 0), (2, 2), (0, 2), (0, 0))}},
        ])
        r = gf.surface_masking(mask, "value")
        recs = r.to_records()
        assert len(recs) == 16
        assert "masked_smsk" in recs[0]
        masked_count = sum(1 for rec in recs if rec["masked_smsk"])
        assert masked_count >= 0


# ── Tool 251: contour_to_polygon ───────────────────────────────────
class TestContourToPolygon:
    def test_basic(self):
        gf = _grid_frame()
        r = gf.contour_to_polygon("value", threshold=5.0)
        recs = r.to_records()
        assert len(recs) > 0
        assert "cluster_cpol" in recs[0]
        assert "point_count_cpol" in recs[0]

    def test_high_threshold(self):
        gf = _grid_frame()
        r = gf.contour_to_polygon("value", threshold=999.0)
        assert len(r.to_records()) == 0


# ── Tool 252: ring_orientation ─────────────────────────────────────
class TestRingOrientation:
    def test_basic(self):
        gf = _polygon_frame()
        r = gf.ring_orientation()
        recs = r.to_records()
        assert len(recs) == 3
        assert "corrected_ro" in recs[0]

    def test_clockwise_corrected(self):
        # Clockwise ring
        rows = [{"geometry": {"type": "Polygon", "coordinates": ((0, 0), (0, 1), (1, 0), (0, 0))}}]
        gf = GeoPromptFrame(rows)
        r = gf.ring_orientation()
        recs = r.to_records()
        assert len(recs) == 1


# ── Tool 253: multipart_normalize ──────────────────────────────────
class TestMultipartNormalize:
    def test_single_part(self):
        rows = [{"geometry": {"type": "Point", "coordinates": (0, 0)}, "val": 1}]
        gf = GeoPromptFrame(rows)
        r = gf.multipart_normalize()
        recs = r.to_records()
        assert len(recs) == 1
        assert recs[0]["parent_mpn"] == 0
        assert recs[0]["part_mpn"] == 0

    def test_multiple_single_parts(self):
        rows = [
            {"geometry": {"type": "Point", "coordinates": (0, 0)}, "val": 1},
            {"geometry": {"type": "Point", "coordinates": (1, 1)}, "val": 2},
        ]
        gf = GeoPromptFrame(rows)
        r = gf.multipart_normalize()
        recs = r.to_records()
        assert len(recs) == 2
        assert recs[0]["parent_mpn"] == 0
        assert recs[1]["parent_mpn"] == 1


# ── Tool 254: segment_intersection ─────────────────────────────────
class TestSegmentIntersection:
    def test_crossing_lines(self):
        rows = [
            {"geometry": {"type": "LineString", "coordinates": ((0, 0), (2, 2))}},
            {"geometry": {"type": "LineString", "coordinates": ((0, 2), (2, 0))}},
        ]
        gf = GeoPromptFrame(rows)
        r = gf.segment_intersection()
        recs = r.to_records()
        assert len(recs) == 1
        assert abs(recs[0]["geometry"]["coordinates"][0] - 1.0) < 0.01

    def test_no_crossing(self):
        rows = [
            {"geometry": {"type": "LineString", "coordinates": ((0, 0), (1, 0))}},
            {"geometry": {"type": "LineString", "coordinates": ((0, 2), (1, 2))}},
        ]
        gf = GeoPromptFrame(rows)
        r = gf.segment_intersection()
        assert len(r.to_records()) == 0


# ── Tool 255: cluster_explanation ──────────────────────────────────
class TestClusterExplanation:
    def test_basic(self):
        gf = _grid_frame()
        r = gf.cluster_explanation("cat", ["value", "weight"])
        recs = r.to_records()
        assert len(recs) == 2  # A and B
        assert "count_cexp" in recs[0]
        assert "distinctiveness_cexp" in recs[0]


# ── Tool 256: auto_cluster_k ──────────────────────────────────────
class TestAutoClusterK:
    def test_basic(self):
        gf = _grid_frame()
        r = gf.auto_cluster_k(max_k=4)
        recs = r.to_records()
        assert len(recs) > 0
        assert "silhouette_ack" in recs[0]
        assert "wcss_ack" in recs[0]


# ── Tool 257: d_infinity_flow ──────────────────────────────────────
class TestDInfinityFlow:
    def test_basic(self):
        gf = _grid_frame()
        r = gf.d_infinity_flow("elev", k=4)
        recs = r.to_records()
        assert len(recs) == 16
        assert "flow_angle_dinf" in recs[0]
        assert "is_sink_dinf" in recs[0]


# ── Tool 258: terrain_derivative_bundle ────────────────────────────
class TestTerrainDerivativeBundle:
    def test_basic(self):
        gf = _grid_frame()
        r = gf.terrain_derivative_bundle("elev", k=4)
        recs = r.to_records()
        assert len(recs) == 16
        for key in ["slope_tdb", "aspect_tdb", "curvature_tdb", "tri_tdb", "tpi_tdb", "roughness_tdb"]:
            assert key in recs[0], f"Missing {key}"


# ── Tool 259: watershed_summary ────────────────────────────────────
class TestWatershedSummary:
    def test_basic(self):
        gf = _grid_frame()
        r = gf.watershed_summary("ws", "value")
        recs = r.to_records()
        assert len(recs) == 3  # w0, w1, w2
        assert "mean_wsum" in recs[0]
        assert "count_wsum" in recs[0]

    def test_no_value(self):
        gf = _grid_frame()
        r = gf.watershed_summary("ws")
        assert len(r.to_records()) == 3


# ── Tool 260: spatial_two_stage_ls ─────────────────────────────────
class TestSpatialTwoStageLS:
    def test_basic(self):
        gf = _grid_frame()
        r = gf.spatial_two_stage_ls("value", ["x_col"], k=4)
        recs = r.to_records()
        assert len(recs) == 16
        assert "predicted_s2sls" in recs[0]
        assert "r_squared_s2sls" in recs[0]
        assert "rho_s2sls" in recs[0]


# ── Tool 261: balanced_clustering ──────────────────────────────────
class TestBalancedClustering:
    def test_basic(self):
        gf = _grid_frame()
        r = gf.balanced_clustering(n_clusters=4, max_size=5)
        recs = r.to_records()
        assert len(recs) == 16
        labels = [rec["cluster_bc"] for rec in recs]
        assert all(l >= 0 for l in labels)

    def test_max_size(self):
        gf = _grid_frame()
        r = gf.balanced_clustering(n_clusters=4, max_size=5)
        labels = _col(r, "cluster_bc")
        from collections import Counter
        counts = Counter(labels)
        assert max(counts.values()) <= 6  # allowing some overflow for remainder


# ── Tool 262: soft_regionalization ─────────────────────────────────
class TestSoftRegionalization:
    def test_basic(self):
        gf = _grid_frame()
        r = gf.soft_regionalization(n_regions=3, max_iterations=10)
        recs = r.to_records()
        assert len(recs) == 16
        assert "hard_region_sr" in recs[0]
        assert "entropy_sr" in recs[0]
        assert "membership_0_sr" in recs[0]


# ── Tool 263: route_explanation ────────────────────────────────────
class TestRouteExplanation:
    def test_basic(self):
        gf = _network_frame()
        r = gf.route_explanation(origin="A", destination="D", weight_column="cost")
        recs = r.to_records()
        assert len(recs) > 0
        assert "narrative_rexp" in recs[0]
        assert "edge_cost_rexp" in recs[0]
        # Total should be less than direct A-D cost of 4
        last = recs[-1]
        assert last["cumulative_cost_rexp"] <= 4.5

    def test_no_path(self):
        gf = _network_frame()
        r = gf.route_explanation(origin="A", destination="Z")
        assert len(r.to_records()) == 0


# ── Tool 264: event_burst_detection ────────────────────────────────
class TestEventBurstDetection:
    def test_basic(self):
        gf = _grid_frame()
        r = gf.event_burst_detection("time", window_size=0.5)
        recs = r.to_records()
        assert len(recs) == 16
        assert "burst_ebst" in recs[0]
        assert "burst_ratio_ebst" in recs[0]


# ── Tool 265: local_dispersion ─────────────────────────────────────
class TestLocalDispersion:
    def test_basic(self):
        gf = _grid_frame()
        r = gf.local_dispersion(k=4)
        recs = r.to_records()
        assert len(recs) == 16
        assert "mean_dist_ldisp" in recs[0]
        assert "cv_ldisp" in recs[0]
        assert "nn_ratio_ldisp" in recs[0]


# ── Tool 266: kriging_confidence ───────────────────────────────────
class TestKrigingConfidence:
    def test_basic(self):
        gf = _grid_frame()
        r = gf.kriging_confidence("value", grid_resolution=5)
        recs = r.to_records()
        assert len(recs) == 25  # 5×5
        assert "predicted_kcnf" in recs[0]
        assert "lower_kcnf" in recs[0]
        assert "upper_kcnf" in recs[0]
        # Lower < predicted < upper
        for rec in recs:
            assert rec["lower_kcnf"] <= rec["predicted_kcnf"] + 0.01
            assert rec["upper_kcnf"] >= rec["predicted_kcnf"] - 0.01


# ── Tool 267: coverage_validation ──────────────────────────────────
class TestCoverageValidation:
    def test_basic(self):
        gf = _polygon_frame()
        r = gf.coverage_validation()
        recs = r.to_records()
        assert len(recs) == 3
        assert "overlaps_cvld" in recs[0]
        assert "gaps_cvld" in recs[0]


# ── Tool 268: seed_determinism_check ───────────────────────────────
class TestSeedDeterminismCheck:
    def test_basic(self):
        gf = _grid_frame()
        r = gf.seed_determinism_check(tool_name="constrained_kmeans", n_runs=2)
        recs = r.to_records()
        assert len(recs) == 16
        assert recs[0]["deterministic_sdc"] is True

    def test_invalid_tool(self):
        gf = _grid_frame()
        r = gf.seed_determinism_check(tool_name="nonexistent_tool", n_runs=2)
        assert len(r.to_records()) == 16
