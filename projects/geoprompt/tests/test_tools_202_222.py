"""Tests for tools 202-222 (constrained Delaunay, introspection,
nearest-neighbor surface, trend surface, local Getis-Ord G, MEM,
community detection, roughness, ruggedness, aspect classify, multi-hillshade,
flow length, sink diagnostics, line offset, polygon smooth, polygon simplify,
turn restrictions, multi-destination routing, interpolation uncertainty,
spatial diversity index, accessibility score).
"""
from __future__ import annotations
import math, pytest
from geoprompt import GeoPromptFrame


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _point(x: float, y: float) -> dict:
    return {"type": "Point", "coordinates": (x, y)}

def _line(coords: list) -> dict:
    return {"type": "LineString", "coordinates": coords}

def _polygon(coords: list) -> dict:
    return {"type": "Polygon", "coordinates": [coords]}

def _col(gf: GeoPromptFrame, name: str) -> list:
    """Extract a column from records."""
    return [r[name] for r in gf.to_records() if name in r]

def _grid_frame(n: int = 16):
    """4x4 grid of points with elevation."""
    rows = []
    for i in range(n):
        x, y = float(i % 4), float(i // 4)
        rows.append({"geometry": _point(x, y), "elevation": x + y, "category": ["A", "B", "C", "D"][i % 4], "value": x * 10 + y})
    return GeoPromptFrame.from_records(rows)

def _network_frame():
    """Simple directed network edges."""
    rows = [
        {"geometry": _line([[0, 0], [1, 0]]), "from_node": "A", "to_node": "B", "cost": 1.0},
        {"geometry": _line([[1, 0], [2, 0]]), "from_node": "B", "to_node": "C", "cost": 2.0},
        {"geometry": _line([[2, 0], [3, 0]]), "from_node": "C", "to_node": "D", "cost": 1.0},
        {"geometry": _line([[0, 0], [0, 1]]), "from_node": "A", "to_node": "E", "cost": 3.0},
        {"geometry": _line([[0, 1], [1, 1]]), "from_node": "E", "to_node": "F", "cost": 1.0},
        {"geometry": _line([[1, 1], [2, 0]]), "from_node": "F", "to_node": "C", "cost": 1.0},
    ]
    return GeoPromptFrame.from_records(rows)


# ---------------------------------------------------------------------------
# Tool 202: constrained_delaunay
# ---------------------------------------------------------------------------
class TestConstrainedDelaunay:
    def test_basic_triangulation(self):
        gf = _grid_frame()
        result = gf.constrained_delaunay()
        assert len(result) > 0
        recs = result.to_records()
        assert "triangle_id_cdt" in recs[0]

    def test_returns_polygons(self):
        gf = _grid_frame()
        result = gf.constrained_delaunay()
        for r in result.to_records():
            assert r["geometry"]["type"] == "Polygon"

    def test_has_area(self):
        gf = _grid_frame()
        result = gf.constrained_delaunay()
        areas = _col(result, "area_cdt")
        assert all(a >= 0 for a in areas)

    def test_small_input(self):
        gf = GeoPromptFrame.from_records([{"geometry": _point(0, 0)}, {"geometry": _point(1, 0)}])
        result = gf.constrained_delaunay()
        assert len(result) == 2  # passthrough

    def test_custom_suffix(self):
        gf = _grid_frame()
        result = gf.constrained_delaunay(cdt_suffix="tri")
        assert "triangle_id_tri" in result.to_records()[0]


# ---------------------------------------------------------------------------
# Tool 203: describe_tool & list_tools
# ---------------------------------------------------------------------------
class TestDescribeTool:
    def test_describe_known_tool(self):
        gf = _grid_frame()
        info = gf.describe_tool("buffer")
        assert info["method"] == "buffer"
        assert "doc" in info
        assert "parameters" in info

    def test_describe_unknown_tool(self):
        gf = _grid_frame()
        info = gf.describe_tool("nonexistent_tool_xyz")
        assert "error" in info

    def test_list_tools(self):
        tools = GeoPromptFrame.list_tools()
        assert isinstance(tools, list)
        assert len(tools) >= 220
        assert "buffer" in tools
        assert "constrained_delaunay" in tools

    def test_describe_new_tool(self):
        gf = _grid_frame()
        info = gf.describe_tool("constrained_delaunay")
        assert info["method"] == "constrained_delaunay"
        assert len(info["parameters"]) > 0


# ---------------------------------------------------------------------------
# Tool 204: nearest_neighbor_surface
# ---------------------------------------------------------------------------
class TestNearestNeighborSurface:
    def test_basic(self):
        gf = _grid_frame()
        result = gf.nearest_neighbor_surface("value", grid_resolution=5)
        assert len(result) == 25
        vals = _col(result, "value_nns")
        assert all(isinstance(v, (int, float)) for v in vals)

    def test_distance_nonneg(self):
        gf = _grid_frame()
        result = gf.nearest_neighbor_surface("value", grid_resolution=4)
        dists = _col(result, "distance_nns")
        assert all(d >= 0 for d in dists)


# ---------------------------------------------------------------------------
# Tool 205: trend_surface_analysis
# ---------------------------------------------------------------------------
class TestTrendSurfaceAnalysis:
    def test_basic(self):
        gf = _grid_frame()
        result = gf.trend_surface_analysis("value", order=1, grid_resolution=5)
        assert len(result) == 25
        r2 = _col(result, "r_squared_tsa")
        assert all(isinstance(v, float) for v in r2)

    def test_order_2(self):
        gf = _grid_frame()
        result = gf.trend_surface_analysis("value", order=2, grid_resolution=4)
        assert len(result) == 16

    def test_small_input(self):
        gf = GeoPromptFrame.from_records([{"geometry": _point(0, 0), "v": 1}, {"geometry": _point(1, 1), "v": 2}])
        result = gf.trend_surface_analysis("v")
        assert len(result) == 2  # passthrough


# ---------------------------------------------------------------------------
# Tool 206: local_getis_ord_g
# ---------------------------------------------------------------------------
class TestLocalGetisOrdG:
    def test_basic(self):
        gf = _grid_frame()
        result = gf.local_getis_ord_g("value", k=4, permutations=19)
        assert len(result) == 16
        gi = _col(result, "gi_star_lgo")
        assert all(isinstance(v, float) for v in gi)

    def test_p_values(self):
        gf = _grid_frame()
        result = gf.local_getis_ord_g("value", k=4, permutations=19)
        pvals = _col(result, "p_value_lgo")
        assert all(0 <= p <= 1 for p in pvals)

    def test_hotspot_labels(self):
        gf = _grid_frame()
        result = gf.local_getis_ord_g("value", k=4, permutations=19)
        labels = _col(result, "hotspot_lgo")
        assert all(l in ("hot", "cold", "ns") for l in labels)


# ---------------------------------------------------------------------------
# Tool 207: moran_eigenvector_maps
# ---------------------------------------------------------------------------
class TestMoranEigenvectorMaps:
    def test_basic(self):
        gf = _grid_frame()
        result = gf.moran_eigenvector_maps(k=4, n_vectors=3)
        assert len(result) == 16
        assert "mem_1_mem" in result.to_records()[0]
        assert "mem_2_mem" in result.to_records()[0]
        assert "mem_3_mem" in result.to_records()[0]

    def test_eigenvalues(self):
        gf = _grid_frame()
        result = gf.moran_eigenvector_maps(k=4, n_vectors=2)
        ev1 = _col(result, "eigenvalue_1_mem")
        ev2 = _col(result, "eigenvalue_2_mem")
        # First eigenvalue should be >= second (by magnitude)
        assert abs(ev1[0]) >= abs(ev2[0]) - 1e-6

    def test_small_input(self):
        gf = GeoPromptFrame.from_records([{"geometry": _point(0, 0)}, {"geometry": _point(1, 1)}, {"geometry": _point(2, 2)}])
        result = gf.moran_eigenvector_maps()
        assert len(result) == 3  # passthrough (< 4)


# ---------------------------------------------------------------------------
# Tool 208: community_detection
# ---------------------------------------------------------------------------
class TestCommunityDetection:
    def test_basic(self):
        gf = _grid_frame()
        result = gf.community_detection(k=4)
        assert len(result) == 16
        comms = _col(result, "community_cd")
        assert all(isinstance(c, int) for c in comms)

    def test_community_count(self):
        gf = _grid_frame()
        result = gf.community_detection(k=4)
        comms = set(_col(result, "community_cd"))
        assert 1 <= len(comms) <= 16


# ---------------------------------------------------------------------------
# Tool 209: roughness
# ---------------------------------------------------------------------------
class TestRoughness:
    def test_basic(self):
        gf = _grid_frame()
        result = gf.roughness("elevation", k=4)
        assert len(result) == 16
        vals = _col(result, "roughness_rough")
        assert all(v >= 0 for v in vals)

    def test_flat_terrain(self):
        rows = [{"geometry": _point(i, 0), "elevation": 10.0} for i in range(5)]
        gf = GeoPromptFrame.from_records(rows)
        result = gf.roughness("elevation", k=3)
        vals = _col(result, "roughness_rough")
        assert all(abs(v) < 1e-10 for v in vals)


# ---------------------------------------------------------------------------
# Tool 210: ruggedness
# ---------------------------------------------------------------------------
class TestRuggedness:
    def test_basic(self):
        gf = _grid_frame()
        result = gf.ruggedness("elevation", k=4)
        assert len(result) == 16
        vrm = _col(result, "vrm_rug")
        assert all(0 <= v <= 1 + 1e-6 for v in vrm)


# ---------------------------------------------------------------------------
# Tool 211: aspect_classify
# ---------------------------------------------------------------------------
class TestAspectClassify:
    def test_from_elevation(self):
        gf = _grid_frame()
        result = gf.aspect_classify(elevation_column="elevation", k=4)
        assert len(result) == 16
        dirs = _col(result, "direction_ac")
        valid = {"N", "NE", "E", "SE", "S", "SW", "W", "NW"}
        assert all(d in valid for d in dirs)

    def test_from_column(self):
        rows = [{"geometry": _point(i, 0), "aspect": i * 45.0} for i in range(8)]
        gf = GeoPromptFrame.from_records(rows)
        result = gf.aspect_classify(aspect_column="aspect")
        assert len(result) == 8


# ---------------------------------------------------------------------------
# Tool 212: multi_hillshade
# ---------------------------------------------------------------------------
class TestMultiHillshade:
    def test_basic(self):
        gf = _grid_frame()
        result = gf.multi_hillshade("elevation", k=4)
        assert len(result) == 16
        hs = _col(result, "hillshade_mh")
        assert all(0 <= v <= 255 for v in hs)

    def test_custom_azimuths(self):
        gf = _grid_frame()
        result = gf.multi_hillshade("elevation", azimuths=[0.0, 90.0, 180.0, 270.0])
        assert len(result) == 16


# ---------------------------------------------------------------------------
# Tool 213: flow_length
# ---------------------------------------------------------------------------
class TestFlowLength:
    def test_downstream(self):
        gf = _grid_frame()
        result = gf.flow_length("elevation", direction="downstream")
        assert len(result) == 16
        lengths = _col(result, "flow_length_fl")
        assert all(l >= 0 for l in lengths)

    def test_upstream(self):
        gf = _grid_frame()
        result = gf.flow_length("elevation", direction="upstream")
        assert len(result) == 16

    def test_direction_tag(self):
        gf = _grid_frame()
        r_dn = gf.flow_length("elevation", direction="downstream")
        r_up = gf.flow_length("elevation", direction="upstream")
        assert all(d == "downstream" for d in _col(r_dn, "direction_fl"))
        assert all(d == "upstream" for d in _col(r_up, "direction_fl"))


# ---------------------------------------------------------------------------
# Tool 214: sink_diagnostics
# ---------------------------------------------------------------------------
class TestSinkDiagnostics:
    def test_basic(self):
        gf = _grid_frame()
        result = gf.sink_diagnostics("elevation")
        assert len(result) == 16
        recs = result.to_records()
        assert "is_sink_sink" in recs[0]
        assert "is_flat_sink" in recs[0]

    def test_flat_terrain_detects_flat(self):
        rows = [{"geometry": _point(i, 0), "elevation": 5.0} for i in range(5)]
        gf = GeoPromptFrame.from_records(rows)
        result = gf.sink_diagnostics("elevation", k=3)
        flats = _col(result, "is_flat_sink")
        assert all(f is True for f in flats)


# ---------------------------------------------------------------------------
# Tool 215: line_offset
# ---------------------------------------------------------------------------
class TestLineOffset:
    def test_basic(self):
        rows = [{"geometry": _line([[0, 0], [10, 0], [10, 10]])}]
        gf = GeoPromptFrame.from_records(rows)
        result = gf.line_offset(offset_distance=2.0, side="left")
        assert len(result) == 1
        assert result.to_records()[0]["geometry"]["type"] == "LineString"

    def test_right_side(self):
        rows = [{"geometry": _line([[0, 0], [10, 0]])}]
        gf = GeoPromptFrame.from_records(rows)
        result = gf.line_offset(offset_distance=1.0, side="right")
        coords = result.to_records()[0]["geometry"]["coordinates"]
        # Right side should go negative y for a left-to-right line
        assert coords[0][1] < 0 or coords[1][1] < 0


# ---------------------------------------------------------------------------
# Tool 216: polygon_smooth
# ---------------------------------------------------------------------------
class TestPolygonSmooth:
    def test_basic(self):
        rows = [{"geometry": _polygon([[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]])}]
        gf = GeoPromptFrame.from_records(rows)
        result = gf.polygon_smooth(iterations=2)
        assert len(result) == 1
        assert result.to_records()[0]["geometry"]["type"] == "Polygon"
        # Should have more vertices after smoothing
        n_smooth = len(result.to_records()[0]["geometry"]["coordinates"][0])
        assert n_smooth > 5


# ---------------------------------------------------------------------------
# Tool 217: polygon_simplify_topo
# ---------------------------------------------------------------------------
class TestPolygonSimplifyTopo:
    def test_basic(self):
        coords = [[0, 0], [5, 0.1], [10, 0], [10, 10], [5, 9.9], [0, 10], [0, 0]]
        rows = [{"geometry": _polygon(coords)}]
        gf = GeoPromptFrame.from_records(rows)
        result = gf.polygon_simplify_topo(tolerance=10.0)
        assert len(result) == 1
        n_verts = len(result.to_records()[0]["geometry"]["coordinates"][0])
        assert n_verts <= len(coords)

    def test_low_tolerance(self):
        coords = [[0, 0], [5, 0.1], [10, 0], [10, 10], [5, 9.9], [0, 10], [0, 0]]
        rows = [{"geometry": _polygon(coords)}]
        gf = GeoPromptFrame.from_records(rows)
        result = gf.polygon_simplify_topo(tolerance=0.001)
        n_verts = len(result.to_records()[0]["geometry"]["coordinates"][0])
        assert n_verts == len(coords)


# ---------------------------------------------------------------------------
# Tool 218: turn_restrictions
# ---------------------------------------------------------------------------
class TestTurnRestrictions:
    def test_basic_routing(self):
        nf = _network_frame()
        result = nf.turn_restrictions(origin="A", destination="D")
        assert len(result) > 0
        steps = _col(result, "step_tr")
        assert steps == list(range(len(steps)))

    def test_with_restriction(self):
        nf = _network_frame()
        result = nf.turn_restrictions(origin="A", destination="D", restricted_turns=[("A", "B", "C")])
        assert len(result) > 0


# ---------------------------------------------------------------------------
# Tool 219: multi_destination_routing
# ---------------------------------------------------------------------------
class TestMultiDestinationRouting:
    def test_basic(self):
        nf = _network_frame()
        result = nf.multi_destination_routing(origins=["A", "B"], destinations=["C", "D"])
        assert len(result) == 4  # 2 origins * 2 destinations
        costs = _col(result, "cost_mdr")
        assert all(isinstance(c, float) for c in costs)

    def test_reachability(self):
        nf = _network_frame()
        result = nf.multi_destination_routing(origins=["A"], destinations=["D"])
        reachable = _col(result, "reachable_mdr")
        assert reachable[0] is True


# ---------------------------------------------------------------------------
# Tool 220: interpolation_uncertainty
# ---------------------------------------------------------------------------
class TestInterpolationUncertainty:
    def test_basic(self):
        gf = _grid_frame()
        result = gf.interpolation_uncertainty("value", grid_resolution=5, k=4)
        assert len(result) == 25
        conf = _col(result, "confidence_iu")
        assert all(0 <= c <= 1 for c in conf)

    def test_density(self):
        gf = _grid_frame()
        result = gf.interpolation_uncertainty("value", grid_resolution=4, k=3)
        density = _col(result, "data_density_iu")
        assert all(d >= 0 for d in density)


# ---------------------------------------------------------------------------
# Tool 221: spatial_diversity_index
# ---------------------------------------------------------------------------
class TestSpatialDiversityIndex:
    def test_basic(self):
        gf = _grid_frame()
        result = gf.spatial_diversity_index("category", k=4)
        assert len(result) == 16
        shannon = _col(result, "shannon_sdi")
        assert all(s >= 0 for s in shannon)

    def test_simpson(self):
        gf = _grid_frame()
        result = gf.spatial_diversity_index("category", k=4)
        simpson = _col(result, "simpson_sdi")
        assert all(0 <= s <= 1 for s in simpson)

    def test_richness(self):
        gf = _grid_frame()
        result = gf.spatial_diversity_index("category", k=4)
        richness = _col(result, "richness_sdi")
        assert all(r >= 1 for r in richness)


# ---------------------------------------------------------------------------
# Tool 222: accessibility_score
# ---------------------------------------------------------------------------
class TestAccessibilityScore:
    def test_basic(self):
        nf = _network_frame()
        result = nf.accessibility_score(max_cost=5.0)
        assert len(result) > 0
        scores = _col(result, "score_acc")
        assert all(0 <= s <= 1 for s in scores)

    def test_reachable_count(self):
        nf = _network_frame()
        result = nf.accessibility_score(max_cost=100.0)
        reachable = _col(result, "reachable_acc")
        assert all(r >= 0 for r in reachable)
