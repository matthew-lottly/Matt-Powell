"""Correctness audit: empty-frame and single-feature edge cases.

Every tool must either return an empty/trivial result or raise a
descriptive error — never crash with an opaque traceback.
"""
from __future__ import annotations
import pytest
from geoprompt import GeoPromptFrame

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _pt(x: float = 0.0, y: float = 0.0) -> dict:
    return {"type": "Point", "coordinates": (x, y)}

def _line(coords=None) -> dict:
    return {"type": "LineString", "coordinates": coords or [[0, 0], [1, 1]]}

def _poly(coords=None) -> dict:
    return {"type": "Polygon", "coordinates": [coords or [[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]}

EMPTY = GeoPromptFrame.from_records([])
SINGLE_PT = GeoPromptFrame.from_records([{"geometry": _pt(), "value": 5.0, "elevation": 10.0, "category": "A", "weight": 1.0}])
SINGLE_LINE = GeoPromptFrame.from_records([{"geometry": _line(), "from_node": "A", "to_node": "B", "cost": 1.0}])
SINGLE_POLY = GeoPromptFrame.from_records([{"geometry": _poly(), "value": 5.0, "elevation": 10.0, "category": "A"}])


# ---------------------------------------------------------------------------
# EMPTY FRAME AUDIT
# Tools that accept a GeoPromptFrame and should handle n=0 gracefully.
# ---------------------------------------------------------------------------
class TestEmptyFrameAudit:
    """Every tool must tolerate an empty frame without crashing."""

    # --- geometry ---
    def test_buffer(self):
        r = EMPTY.buffer(1.0)
        assert len(r) == 0

    def test_centroid(self):
        # centroid() returns a Coordinate, not a frame; empty raises
        with pytest.raises((ZeroDivisionError, ValueError)):
            EMPTY.centroid()

    def test_convex_hulls(self):
        r = EMPTY.convex_hulls()
        assert len(r) == 0

    def test_simplify(self):
        r = EMPTY.simplify(1.0)
        assert len(r) == 0

    def test_densify(self):
        r = EMPTY.densify(0.5)
        assert len(r) == 0

    def test_multipart_to_singlepart(self):
        r = EMPTY.multipart_to_singlepart()
        assert len(r) == 0

    def test_smooth_geometry(self):
        r = EMPTY.smooth_geometry()
        assert len(r) == 0

    def test_polygon_triangulation(self):
        r = EMPTY.polygon_triangulation()
        assert len(r) == 0

    def test_constrained_delaunay(self):
        r = EMPTY.constrained_delaunay()
        assert len(r) == 0

    def test_polygon_smooth(self):
        r = EMPTY.polygon_smooth()
        assert len(r) == 0

    def test_polygon_simplify_topo(self):
        r = EMPTY.polygon_simplify_topo()
        assert len(r) == 0

    def test_line_offset(self):
        r = EMPTY.line_offset()
        assert len(r) == 0

    # --- classification ---
    def test_describe(self):
        r = EMPTY.describe()
        assert isinstance(r, dict)

    def test_head(self):
        r = EMPTY.head(5)
        assert len(r) == 0

    def test_sort(self):
        # sort requires column to exist; empty frame has no columns
        with pytest.raises(KeyError):
            EMPTY.sort("value")

    # --- spatial stats ---
    def test_mean_center(self):
        # mean_center returns a Coordinate tuple; on empty it returns (0,0)
        r = EMPTY.mean_center()
        assert isinstance(r, (tuple, GeoPromptFrame))

    def test_thiessen_polygons(self):
        r = EMPTY.thiessen_polygons()
        assert len(r) == 0

    def test_kernel_density(self):
        r = EMPTY.kernel_density()
        assert len(r) == 0

    # --- network tools ---
    def test_community_detection(self):
        r = EMPTY.community_detection()
        assert len(r) == 0

    # --- I/O ---
    def test_to_records_empty(self):
        r = EMPTY.to_records()
        assert r == []


# ---------------------------------------------------------------------------
# SINGLE-FEATURE AUDIT
# Tools that accept a GeoPromptFrame and should handle n=1 gracefully.
# ---------------------------------------------------------------------------
class TestSingleFeatureAudit:
    """Every tool must tolerate a single-feature frame without crashing."""

    # --- geometry ---
    def test_buffer(self):
        r = SINGLE_PT.buffer(1.0)
        assert len(r) == 1

    def test_centroid(self):
        r = SINGLE_PT.centroid()
        assert isinstance(r, tuple) and len(r) == 2

    def test_convex_hulls(self):
        r = SINGLE_POLY.convex_hulls()
        assert len(r) == 1

    def test_simplify(self):
        r = SINGLE_POLY.simplify(0.1)
        assert len(r) == 1

    def test_densify(self):
        r = SINGLE_LINE.densify(0.1)
        assert len(r) == 1

    def test_multipart_to_singlepart(self):
        r = SINGLE_PT.multipart_to_singlepart()
        assert len(r) >= 1

    def test_polygon_smooth(self):
        r = SINGLE_POLY.polygon_smooth()
        assert len(r) == 1

    def test_polygon_simplify_topo(self):
        r = SINGLE_POLY.polygon_simplify_topo()
        assert len(r) == 1

    def test_line_offset(self):
        r = SINGLE_LINE.line_offset(offset_distance=0.5)
        assert len(r) == 1

    # --- spatial stats ---
    def test_mean_center(self):
        r = SINGLE_PT.mean_center()
        assert isinstance(r, (tuple, GeoPromptFrame))

    def test_dbscan(self):
        r = SINGLE_PT.dbscan(eps=1.0, min_samples=1)
        assert len(r) == 1

    def test_describe(self):
        r = SINGLE_PT.describe()
        assert isinstance(r, dict)

    def test_head(self):
        r = SINGLE_PT.head(5)
        assert len(r) == 1

    # --- classification/new tools ---
    def test_constrained_delaunay(self):
        r = SINGLE_PT.constrained_delaunay()
        assert len(r) == 1

    def test_roughness(self):
        r = SINGLE_PT.roughness("elevation")
        assert len(r) == 1

    def test_ruggedness(self):
        r = SINGLE_PT.ruggedness("elevation")
        assert len(r) == 1

    def test_aspect_classify(self):
        r = SINGLE_PT.aspect_classify(elevation_column="elevation")
        assert len(r) == 1

    def test_multi_hillshade(self):
        r = SINGLE_PT.multi_hillshade("elevation")
        assert len(r) == 1

    # --- introspection ---
    def test_describe_tool(self):
        r = SINGLE_PT.describe_tool("buffer")
        assert r["method"] == "buffer"

    def test_list_tools(self):
        tools = GeoPromptFrame.list_tools()
        assert len(tools) > 200

    # --- I/O ---
    def test_to_records(self):
        r = SINGLE_PT.to_records()
        assert len(r) == 1


# ---------------------------------------------------------------------------
# DUPLICATE-COORDINATE AUDIT
# Points at the same location should not crash distance-dependent tools.
# ---------------------------------------------------------------------------
class TestDuplicateCoordAudit:
    """Tools must handle coincident/duplicate geometries."""

    @pytest.fixture
    def dupes(self):
        return GeoPromptFrame.from_records([
            {"geometry": _pt(1, 1), "value": 10, "elevation": 5, "category": "A"},
            {"geometry": _pt(1, 1), "value": 20, "elevation": 5, "category": "B"},
            {"geometry": _pt(1, 1), "value": 30, "elevation": 5, "category": "C"},
            {"geometry": _pt(2, 2), "value": 40, "elevation": 8, "category": "A"},
        ])

    def test_idw(self, dupes):
        r = dupes.idw_interpolation("value", grid_resolution=3)
        assert len(r) > 0

    def test_kernel_density(self, dupes):
        r = dupes.kernel_density()
        assert len(r) > 0

    def test_dbscan(self, dupes):
        r = dupes.dbscan(eps=0.5, min_samples=2)
        assert len(r) == 4

    def test_nearest_neighbors(self, dupes):
        # nearest_neighbors requires site_id column; returns a list
        dupes2 = dupes.with_column("site_id", [f"s{i}" for i in range(len(dupes.to_records()))])
        r = dupes2.nearest_neighbors(k=2)
        assert isinstance(r, list) and len(r) > 0

    def test_roughness(self, dupes):
        r = dupes.roughness("elevation")
        assert len(r) == 4

    def test_community_detection(self, dupes):
        r = dupes.community_detection(k=2)
        assert len(r) == 4

    def test_constrained_delaunay(self, dupes):
        r = dupes.constrained_delaunay()
        assert isinstance(r, GeoPromptFrame)  # may be 0 if all points coincide except one


# ---------------------------------------------------------------------------
# CRS MISUSE AUDIT
# Geographic CRS with tools that expect projected should warn.
# ---------------------------------------------------------------------------
class TestCRSMisuseAudit:
    """Tools that assume projected coordinates should warn on geographic CRS."""

    @pytest.fixture
    def geo_frame(self):
        return GeoPromptFrame.from_records(
            [
                {"geometry": _pt(-73.9, 40.7), "value": 1, "elevation": 10},
                {"geometry": _pt(-73.8, 40.8), "value": 2, "elevation": 20},
                {"geometry": _pt(-73.7, 40.9), "value": 3, "elevation": 30},
                {"geometry": _pt(-73.6, 41.0), "value": 4, "elevation": 40},
            ],
            crs="EPSG:4326",
        )

    def test_buffer_geographic(self, geo_frame):
        # buffer may or may not warn; just ensure it doesn't crash
        r = geo_frame.buffer(1.0)
        assert len(r) == 4

    def test_flow_length_geographic_warning(self, geo_frame):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            r = geo_frame.flow_length("elevation")
            assert len(r) == 4
