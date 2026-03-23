"""Tests for tools 379-400."""

import pytest
from geoprompt import GeoPromptFrame


def _col(n, name="v", vals=None):
    rows = []
    for i in range(n):
        rows.append({
            "geometry": {"type": "Point", "coordinates": (float(i), float(i % 3))},
            name: vals[i] if vals else float(i),
        })
    return GeoPromptFrame(rows)


def _network_frame():
    rows = []
    edges = [(0, 1), (1, 2), (2, 3), (3, 0), (0, 2)]
    for s, t in edges:
        rows.append({
            "geometry": {"type": "LineString", "coordinates": ((float(s), 0.0), (float(t), 1.0))},
            "source": s,
            "target": t,
            "weight": 1.0,
        })
    return GeoPromptFrame(rows)


def _polygon_frame(n=5):
    rows = []
    for i in range(n):
        x, y = float(i * 2), float(i * 2)
        rows.append({
            "geometry": {
                "type": "Polygon",
                "coordinates": ((x, y), (x + 1, y), (x + 1, y + 1), (x, y + 1), (x, y)),
            },
            "v": float(i),
        })
    return GeoPromptFrame(rows)


class TestTool379EmptyFrameGuard:
    def test_basic(self):
        gf = _col(5)
        out = gf.empty_frame_guard()
        r = out.to_records()[0]
        assert r["is_empty_efg"] == 0
        assert r["n_rows_efg"] == 5


class TestTool380OneRowGuard:
    def test_basic(self):
        gf = _col(1)
        out = gf.one_row_guard()
        r = out.to_records()[0]
        assert r["is_single_org"] == 1
        assert r["distance_safe_org"] == 0


class TestTool381TwoRowGuard:
    def test_basic(self):
        gf = _col(2)
        out = gf.two_row_guard()
        r = out.to_records()[0]
        assert r["has_pair_trg"] == 1
        assert r["pair_distance_trg"] > 0


class TestTool382DuplicateCoordGuard:
    def test_with_duplicates(self):
        rows = [
            {"geometry": {"type": "Point", "coordinates": (1.0, 2.0)}, "v": 1},
            {"geometry": {"type": "Point", "coordinates": (1.0, 2.0)}, "v": 2},
            {"geometry": {"type": "Point", "coordinates": (3.0, 4.0)}, "v": 3},
        ]
        gf = GeoPromptFrame(rows)
        out = gf.duplicate_coord_guard()
        r = out.to_records()[0]
        assert r["has_duplicates_dcg"] == 1
        assert r["n_duplicates_dcg"] == 2


class TestTool383CollinearGuard:
    def test_collinear(self):
        rows = [
            {"geometry": {"type": "Point", "coordinates": (0.0, 0.0)}, "v": 1},
            {"geometry": {"type": "Point", "coordinates": (1.0, 1.0)}, "v": 2},
            {"geometry": {"type": "Point", "coordinates": (2.0, 2.0)}, "v": 3},
        ]
        gf = GeoPromptFrame(rows)
        out = gf.collinear_guard()
        r = out.to_records()[0]
        assert r["is_collinear_clg"] == 1

    def test_not_collinear(self):
        gf = _col(5)
        out = gf.collinear_guard()
        r = out.to_records()[0]
        assert r["is_collinear_clg"] == 0


class TestTool384NullGeometryGuard:
    def test_all_valid(self):
        gf = _col(5)
        out = gf.null_geometry_guard()
        r = out.to_records()[0]
        assert r["all_valid_ngg"] == 1


class TestTool385MultipartGuard:
    def test_no_multipart(self):
        gf = _col(5)
        out = gf.multipart_guard()
        r = out.to_records()[0]
        assert r["all_single_mpg"] == 1
        assert r["n_multipart_mpg"] == 0


class TestTool386PolygonHoleGuard:
    def test_simple_polygons(self):
        gf = _polygon_frame()
        out = gf.polygon_hole_guard()
        r = out.to_records()[0]
        assert r["all_simple_phg"] == 1


class TestTool387SelfIntersectionGuard:
    def test_clean_polygons(self):
        gf = _polygon_frame()
        out = gf.self_intersection_guard()
        r = out.to_records()[0]
        assert r["n_self_intersecting_sig"] == 0


class TestTool388DisconnectedNetworkGuard:
    def test_connected(self):
        gf = _network_frame()
        out = gf.disconnected_network_guard("source", "target")
        r = out.to_records()[0]
        assert r["is_connected_dng"] == 1


class TestTool389CoordRangeGuard:
    def test_basic(self):
        gf = _col(10)
        out = gf.coord_range_guard()
        r = out.to_records()[0]
        assert r["very_small_crg"] == 0
        assert r["x_range_crg"] > 0


class TestTool390DeterministicSeedGuard:
    def test_deterministic(self):
        gf = _col(10)
        out = gf.deterministic_seed_guard("v")
        r = out.to_records()[0]
        assert r["deterministic_dsg"] == 1


class TestTool391NeighborCacheReport:
    def test_basic(self):
        gf = _col(10)
        out = gf.neighbor_cache_report()
        r = out.to_records()[0]
        assert r["entries_ncr"] == 10
        assert r["compute_ms_ncr"] >= 0


class TestTool392SparseAdjacencyReport:
    def test_basic(self):
        gf = _col(10)
        out = gf.sparse_adjacency_report()
        r = out.to_records()[0]
        assert 0 <= r["density_sar"] <= 1.0


class TestTool393ChunkedInterpolationReport:
    def test_basic(self):
        gf = _col(12)
        out = gf.chunked_interpolation_report("v", chunk_size=4)
        recs = out.to_records()
        assert len(recs) == 3  # 12 / 4 = 3 chunks


class TestTool394ConfigCentral:
    def test_basic(self):
        gf = _col(5)
        out = gf.config_central()
        r = out.to_records()[0]
        assert r["n_rows_cfg"] == 5
        assert "geometry_column_cfg" in r


class TestTool395PluginRegistryReport:
    def test_basic(self):
        gf = _col(3)
        out = gf.plugin_registry_report()
        r = out.to_records()[0]
        assert r["n_methods_prr"] > 0


class TestTool396StableApiReview:
    def test_basic(self):
        gf = _col(3)
        out = gf.stable_api_review()
        r = out.to_records()[0]
        assert r["n_public_apir"] > 0


class TestTool397InplaceStrategyReview:
    def test_immutability(self):
        gf = _col(5)
        out = gf.inplace_strategy_review("v")
        r = out.to_records()[0]
        assert r["immutable_isr"] == 1


class TestTool398VoronoiSemanticsReview:
    def test_basic(self):
        gf = _col(10)
        out = gf.voronoi_semantics_review()
        r = out.to_records()[0]
        assert r["voronoi_possible_vsr"] == 1


class TestTool399ParityEdgeCaseAudit:
    def test_basic(self):
        gf = _col(10)
        out = gf.parity_edge_case_audit("v")
        r = out.to_records()[0]
        assert r["n_peca"] == 10
        assert r["n_null_peca"] == 0


class TestTool400ReleaseChecklist:
    def test_basic(self):
        gf = _col(3)
        out = gf.release_checklist(expected_tool_count=1)
        r = out.to_records()[0]
        assert r["meets_target_rc"] == 1
