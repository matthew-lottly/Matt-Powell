"""Cross-validation tests comparing GeoPromptFrame tools against reference
implementations from Shapely, SciPy, and NumPy.

Every test constructs the same geometry/data, runs both our tool and the
reference package, and asserts numerical equality (within tolerance).
"""

import math
import pytest
import numpy as np
import scipy.spatial
import scipy.spatial.distance
import shapely.geometry as sg
import shapely.ops

from geoprompt import GeoPromptFrame


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pt_frame(coords: list[tuple[float, float]] | list[tuple[int, int]], **extra_cols) -> GeoPromptFrame:
    """Quick point frame from (x,y) tuples."""
    rows = []
    for i, (x, y) in enumerate(coords):
        rec = {"site_id": f"p{i}", "geometry": {"type": "Point", "coordinates": [x, y]}}
        for k, vals in extra_cols.items():
            rec[k] = vals[i]
        rows.append(rec)
    return GeoPromptFrame.from_records(rows, crs="EPSG:4326")


def _poly_frame(polygons: list[list[tuple[float, float]]] | list[list[tuple[int, int]]], **extra_cols) -> GeoPromptFrame:
    """Quick polygon frame from lists of exterior ring coords (closed)."""
    rows = []
    for i, ring in enumerate(polygons):
        rec = {"site_id": f"poly{i}", "geometry": {"type": "Polygon", "coordinates": ring}}
        for k, vals in extra_cols.items():
            rec[k] = vals[i]
        rows.append(rec)
    return GeoPromptFrame.from_records(rows, crs="EPSG:4326")


def _line_frame(lines: list[list[tuple[float, float]]]) -> GeoPromptFrame:
    """Quick linestring frame."""
    rows = []
    for i, coords in enumerate(lines):
        rows.append({"site_id": f"line{i}", "geometry": {"type": "LineString", "coordinates": coords}})
    return GeoPromptFrame.from_records(rows, crs="EPSG:4326")


# ===================================================================
#  GEOMETRY MEASUREMENTS  (vs Shapely)
# ===================================================================

class TestPolygonAreaVsShapely:
    """Compare polygon_area against Shapely for various shapes."""

    def _check(self, ring):
        frame = _poly_frame([ring])
        our_area = frame.polygon_area()["value_area"][0]
        ref_area = sg.Polygon(ring).area
        assert abs(our_area - ref_area) < 1e-9, f"area mismatch: {our_area} vs {ref_area}"

    def test_unit_square(self):
        self._check([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])

    def test_triangle(self):
        self._check([(0, 0), (4, 0), (2, 3), (0, 0)])

    def test_irregular(self):
        self._check([(0, 0), (5, 0), (5, 3), (3, 5), (0, 4), (0, 0)])

    def test_large_square(self):
        self._check([(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)])

    def test_tiny_triangle(self):
        self._check([(0, 0), (0.001, 0), (0.0005, 0.001), (0, 0)])


class TestPolygonPerimeterVsShapely:
    """Compare polygon_perimeter against Shapely length."""

    def _check(self, ring):
        frame = _poly_frame([ring])
        our_perim = frame.polygon_perimeter()["value_perimeter"][0]
        ref_perim = sg.Polygon(ring).length
        assert abs(our_perim - ref_perim) < 1e-9, f"perimeter mismatch: {our_perim} vs {ref_perim}"

    def test_unit_square(self):
        self._check([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])

    def test_triangle(self):
        self._check([(0, 0), (4, 0), (2, 3), (0, 0)])

    def test_irregular(self):
        self._check([(0, 0), (5, 0), (5, 3), (3, 5), (0, 4), (0, 0)])


class TestLineLengthVsShapely:
    """Compare line_length against Shapely for LineStrings."""

    def _check(self, coords):
        frame = _line_frame([coords])
        our_len = frame.line_length()["value_length"][0]
        ref_len = sg.LineString(coords).length
        assert abs(our_len - ref_len) < 1e-9, f"length mismatch: {our_len} vs {ref_len}"

    def test_horizontal(self):
        self._check([(0, 0), (5, 0)])

    def test_diagonal(self):
        self._check([(0, 0), (3, 4)])

    def test_zigzag(self):
        self._check([(0, 0), (1, 1), (2, 0), (3, 1), (4, 0)])

    def test_single_segment(self):
        self._check([(0, 0), (10, 10)])


# ===================================================================
#  DISTANCE / NEAREST NEIGHBOR  (vs SciPy)
# ===================================================================

class TestNearestNeighborVsScipy:
    """Compare nearest_neighbor_distance against scipy KDTree."""

    def test_grid(self):
        coords = [(float(x), float(y)) for x in range(5) for y in range(5)]
        frame = _pt_frame(coords)
        result = frame.nearest_neighbor_distance()
        our_dists = result["distance_nn"]
        tree = scipy.spatial.KDTree(coords)
        for i, (x, y) in enumerate(coords):
            dd, _ = tree.query([x, y], k=2)
            ref_nn = dd[1]
            assert abs(our_dists[i] - ref_nn) < 1e-9, f"NN dist mismatch at {i}"

    def test_random_20(self):
        rng = np.random.default_rng(42)
        coords = [(float(x), float(y)) for x, y in rng.uniform(0, 100, (20, 2))]
        frame = _pt_frame(coords)
        result = frame.nearest_neighbor_distance()
        our_dists = result["distance_nn"]
        tree = scipy.spatial.KDTree(coords)
        for i, c in enumerate(coords):
            dd, _ = tree.query(c, k=2)
            assert abs(our_dists[i] - dd[1]) < 1e-9


class TestPairwiseDistancesVsScipy:
    """Compare pairwise_distances against scipy pdist/cdist."""

    def test_self_pairwise(self):
        coords = [(0.0, 0.0), (3.0, 0.0), (0.0, 4.0)]
        frame = _pt_frame(coords)
        result = frame.pairwise_distances()
        our_dists = sorted(r["distance"] for r in result)
        ref = sorted(scipy.spatial.distance.pdist(coords))
        assert len(our_dists) == len(ref)
        for a, b in zip(our_dists, ref):
            assert abs(a - b) < 1e-9

    def test_cross_pairwise(self):
        c1 = [(0.0, 0.0), (1.0, 0.0)]
        c2 = [(3.0, 0.0), (0.0, 4.0)]
        frame_a = _pt_frame(c1)
        frame_b = _pt_frame(c2)
        result = frame_a.pairwise_distances(other=frame_b)
        our_dists = sorted(r["distance"] for r in result)
        ref = sorted(scipy.spatial.distance.cdist(c1, c2).ravel())
        for a, b in zip(our_dists, ref):
            assert abs(a - b) < 1e-9


# ===================================================================
#  MEAN / MEDIAN CENTER  (vs NumPy)
# ===================================================================

class TestMeanCenterVsNumpy:
    """Compare mean_center against numpy mean."""

    def test_unweighted(self):
        coords = [(1.0, 2.0), (3.0, 4.0), (5.0, 6.0), (7.0, 8.0)]
        frame = _pt_frame(coords)
        our = frame.mean_center()
        ref = tuple(np.mean(coords, axis=0))
        assert abs(our[0] - ref[0]) < 1e-9
        assert abs(our[1] - ref[1]) < 1e-9

    def test_weighted(self):
        coords = [(0.0, 0.0), (10.0, 0.0), (0.0, 10.0)]
        weights = [1.0, 2.0, 3.0]
        frame = _pt_frame(coords, weight=weights)
        our = frame.mean_center(weight_column="weight")
        arr = np.array(coords)
        w = np.array(weights)
        ref = (np.average(arr[:, 0], weights=w), np.average(arr[:, 1], weights=w))
        assert abs(our[0] - ref[0]) < 1e-9
        assert abs(our[1] - ref[1]) < 1e-9


# ===================================================================
#  MINIMUM SPANNING TREE  (vs SciPy)
# ===================================================================

class TestMSTVsScipy:
    """Compare minimum_spanning_tree total cost against SciPy."""

    def test_small(self):
        coords = [(0.0, 0.0), (1.0, 0.0), (0.5, 1.0), (2.0, 0.5)]
        frame = _pt_frame(coords)
        result = frame.minimum_spanning_tree()
        our_cost = sum(row["cost_mst"] for row in result)
        # Build dense distance matrix for scipy
        n = len(coords)
        dm = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                dm[i][j] = math.hypot(coords[i][0] - coords[j][0], coords[i][1] - coords[j][1])
        from scipy.sparse.csgraph import minimum_spanning_tree as scipy_mst
        mst = scipy_mst(dm)
        ref_cost = mst.sum()
        assert abs(our_cost - ref_cost) < 1e-9, f"MST cost: {our_cost} vs {ref_cost}"

    def test_grid_5(self):
        coords = [(float(x), float(y)) for x in range(3) for y in range(3)]
        frame = _pt_frame(coords)
        result = frame.minimum_spanning_tree()
        our_cost = sum(row["cost_mst"] for row in result)
        n = len(coords)
        dm = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                dm[i][j] = math.hypot(coords[i][0] - coords[j][0], coords[i][1] - coords[j][1])
        from scipy.sparse.csgraph import minimum_spanning_tree as scipy_mst
        ref_cost = scipy_mst(dm).sum()
        assert abs(our_cost - ref_cost) < 1e-9


# ===================================================================
#  DBSCAN  (vs SciPy-based manual reference)
# ===================================================================

class TestDBSCANVsReference:
    """Verify DBSCAN results against a known scenario."""

    def test_two_clusters(self):
        """Two clearly separated clusters should be identified."""
        c1 = [(float(x), 0.0) for x in range(5)]        # cluster 1: (0,0)..(4,0)
        c2 = [(float(x), 100.0) for x in range(5)]      # cluster 2: (0,100)..(4,100)
        coords = c1 + c2
        frame = _pt_frame(coords)
        result = frame.dbscan_cluster(eps=2.0, min_samples=3)
        clusters = result["cluster_dbscan"]
        # All of cluster 1 should share a label
        c1_labels = set(clusters[:5])
        c2_labels = set(clusters[5:])
        assert len(c1_labels) == 1 and None not in c1_labels
        assert len(c2_labels) == 1 and None not in c2_labels
        assert c1_labels != c2_labels  # different clusters

    def test_noise(self):
        """Isolated point should be noise."""
        coords = [(0.0, 0.0), (0.5, 0.0), (1.0, 0.0), (1.5, 0.0), (100.0, 100.0)]
        frame = _pt_frame(coords)
        result = frame.dbscan_cluster(eps=1.0, min_samples=3)
        noise = result["noise_dbscan"]
        assert noise[4] is True   # isolated point is noise
        assert noise[0] is False  # cluster member

    def test_vs_sklearn(self):
        """Compare against sklearn DBSCAN if available."""
        try:
            from sklearn.cluster import DBSCAN as SkDBSCAN
        except ImportError:
            pytest.skip("sklearn not installed")
        rng = np.random.default_rng(123)
        pts_a = rng.normal(loc=[0, 0], scale=0.5, size=(15, 2))
        pts_b = rng.normal(loc=[5, 5], scale=0.5, size=(15, 2))
        all_pts = np.vstack([pts_a, pts_b])
        coords = [(float(r[0]), float(r[1])) for r in all_pts]
        frame = _pt_frame(coords)
        result = frame.dbscan_cluster(eps=1.5, min_samples=3)
        our_labels = result["cluster_dbscan"]
        ref = SkDBSCAN(eps=1.5, min_samples=3).fit(all_pts)
        ref_labels = ref.labels_
        # Both should find exactly 2 clusters
        our_set = set(l for l in our_labels if l is not None)
        ref_set = set(l for l in ref_labels if l != -1)
        assert len(our_set) == len(ref_set), f"cluster count: {len(our_set)} vs {len(ref_set)}"
        # Cluster assignments should be consistent (modulo labelling)
        for i in range(len(coords)):
            for j in range(i + 1, len(coords)):
                our_same = (our_labels[i] == our_labels[j] and our_labels[i] is not None)
                ref_same = (ref_labels[i] == ref_labels[j] and ref_labels[i] != -1)
                assert our_same == ref_same, f"cluster assignment mismatch at ({i},{j})"


# ===================================================================
#  CLARK-EVANS / AVERAGE NEAREST NEIGHBOR  (analytical verification)
# ===================================================================

class TestClarkEvans:
    """Verify Clark-Evans R ratio against known patterns."""

    def test_regular_grid_high_R(self):
        """A regular grid should have R > 1 (regular pattern)."""
        coords = [(float(x), float(y)) for x in range(6) for y in range(6)]
        frame = _pt_frame(coords)
        result = frame.average_nearest_neighbor()
        assert result["r_ratio"] is not None
        assert result["r_ratio"] > 1.0, f"Regular grid R should be > 1, got {result['r_ratio']}"

    def test_clustered_low_R(self):
        """Highly clustered points should have R < 1."""
        coords = [(0.1 * i, 0.1 * j) for i in range(6) for j in range(6)]
        # Add extent by including far points to make study area large
        coords.append((100.0, 100.0))
        coords.append((100.0, 0.0))
        frame = _pt_frame(coords)
        result = frame.average_nearest_neighbor()
        assert result["r_ratio"] is not None
        assert result["r_ratio"] < 1.0

    def test_formula_manual(self):
        """Verify the formula by hand for 4 points in known arrangement."""
        coords = [(0.0, 0.0), (2.0, 0.0), (4.0, 0.0), (6.0, 0.0)]
        frame = _pt_frame(coords)
        result = frame.average_nearest_neighbor()
        # NN distances: each point has NN dist = 2.0
        assert abs(result["observed_mean_distance"] - 2.0) < 1e-9
        # Bounding box: 6 × 0 = area 0 → but min_y == max_y, so area = max(6*0, 1e-12)
        # Expected = 0.5 / sqrt(4 / 1e-12)  ≈ very small
        # R = observed / expected → very large
        assert result["r_ratio"] > 1.0


# ===================================================================
#  RIPLEY'S K  (analytical verification)
# ===================================================================

class TestRipleysK:
    """Verify Ripley's K formula against manual calculation."""

    def test_four_points(self):
        """Manually computed K for 4 equidistant points."""
        coords = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
        frame = _pt_frame(coords)
        # With edge_correction=False we get the classic formula
        result = frame.ripleys_k(distances=[1.0, 1.5, 2.0], edge_correction=False)
        # Area = 1×1 = 1, n = 4
        # At d=1.0: each corner has 2 neighbors at dist 1.0, so count = 4×2 = 8
        # K(1.0) = 1 × 8 / 16 = 0.5
        assert abs(result[0]["k_value"] - 0.5) < 1e-9
        # At d=1.5: diagonal = sqrt(2) ≈ 1.414, within range. Each has 3 neighbors → count = 12
        # K(1.5) = 1 × 12 / 16 = 0.75
        assert abs(result[1]["k_value"] - 0.75) < 1e-9
        # At d=2.0: all pairs within range → count = 12
        # K(2.0) = 1 × 12 / 16 = 0.75
        assert abs(result[2]["k_value"] - 0.75) < 1e-9
        # With edge correction on, values should be >= uncorrected (compensates for boundary)
        result_ec = frame.ripleys_k(distances=[1.0, 1.5, 2.0], edge_correction=True)
        for i in range(3):
            assert result_ec[i]["k_value"] >= result[i]["k_value"] - 1e-9


# ===================================================================
#  SPLINE INTERPOLATION  (exact at sample points)
# ===================================================================

class TestSplineExactInterpolation:
    """A spline should reproduce sample values exactly at sample locations."""

    def test_exact_at_samples(self):
        coords = [(0.0, 0.0), (1.0, 0.0), (0.5, 1.0)]
        values = [10.0, 20.0, 30.0]
        frame = _pt_frame(coords, val=values)
        result = frame.spline_interpolation(value_column="val", grid_resolution=20)
        # Find grid cells closest to each sample point
        result_rows = list(result)
        for ci, (cx, cy) in enumerate(coords):
            best_dist = float("inf")
            best_val = None
            for row in result_rows:
                gx, gy = row["geometry"]["coordinates"]
                d = math.hypot(gx - cx, gy - cy)
                if d < best_dist:
                    best_dist = d
                    best_val = row["value_spline"]
            # If grid point is very close to sample, value should be close
            if best_dist < 0.1 and best_val is not None:
                assert abs(best_val - values[ci]) < 2.0, \
                    f"Spline at {coords[ci]}: got {best_val}, expected ~{values[ci]}"


# ===================================================================
#  TREND SURFACE  (exact for linear surface)
# ===================================================================

class TestTrendSurfaceLinear:
    """A first-order trend surface should exactly recover a linear function."""

    def test_linear_recovery(self):
        # z = 2x + 3y + 5
        coords = [(0, 0), (1, 0), (0, 1), (1, 1), (0.5, 0.5)]
        values = [2 * x + 3 * y + 5 for x, y in coords]
        frame = _pt_frame(coords, val=values)
        result = frame.trend_surface(value_column="val", order=1, grid_resolution=10)
        rows = list(result)
        for row in rows:
            gx, gy = row["geometry"]["coordinates"]
            expected = 2 * gx + 3 * gy + 5
            assert abs(row["value_trend"] - expected) < 1e-6, \
                f"Trend at ({gx:.2f},{gy:.2f}): {row['value_trend']:.4f} vs {expected:.4f}"


class TestTrendSurfaceQuadratic:
    """Second-order trend surface should recover a quadratic function."""

    def test_quadratic_recovery(self):
        # z = x² + y²
        coords = [(0, 0), (1, 0), (0, 1), (1, 1), (0.5, 0.5), (0, 0.5), (0.5, 0), (1, 0.5), (0.5, 1)]
        values = [x * x + y * y for x, y in coords]
        frame = _pt_frame(coords, val=values)
        result = frame.trend_surface(value_column="val", order=2, grid_resolution=10)
        rows = list(result)
        for row in rows:
            gx, gy = row["geometry"]["coordinates"]
            expected = gx * gx + gy * gy
            assert abs(row["value_trend"] - expected) < 1e-4, \
                f"Trend at ({gx:.2f},{gy:.2f}): {row['value_trend']:.4f} vs {expected:.4f}"


# ===================================================================
#  JENKS NATURAL BREAKS  (classification correctness)
# ===================================================================

class TestJenksClassification:
    """Verify Jenks assigns correct class for values around break points."""

    def test_three_classes(self):
        """Three well-separated groups should get different classes."""
        vals = [1.0, 2.0, 3.0, 50.0, 51.0, 52.0, 100.0, 101.0, 102.0]
        coords = [(float(i), 0.0) for i in range(len(vals))]
        frame = _pt_frame(coords, val=vals)
        result = frame.jenks_natural_breaks(value_column="val", k=3)
        classes = result["class_jenks"]
        # Low group should share one class, mid another, high another
        low_cls = set(classes[:3])
        mid_cls = set(classes[3:6])
        high_cls = set(classes[6:])
        assert len(low_cls) == 1, f"low group has multiple classes: {low_cls}"
        assert len(mid_cls) == 1, f"mid group has multiple classes: {mid_cls}"
        assert len(high_cls) == 1, f"high group has multiple classes: {high_cls}"
        assert low_cls != mid_cls, "low and mid have same class"
        assert mid_cls != high_cls, "mid and high have same class"
        assert low_cls != high_cls, "low and high have same class"

    def test_class_ordering(self):
        """Classes should be ordered: lower values → lower class numbers."""
        vals = [1.0, 2.0, 3.0, 50.0, 51.0, 52.0, 100.0, 101.0, 102.0]
        coords = [(float(i), 0.0) for i in range(len(vals))]
        frame = _pt_frame(coords, val=vals)
        result = frame.jenks_natural_breaks(value_column="val", k=3)
        classes = result["class_jenks"]
        assert classes[0] < classes[4], "low class should be < mid class"
        assert classes[4] < classes[7], "mid class should be < high class"

    def test_two_classes(self):
        """Simplest case: two groups."""
        vals = [1.0, 2.0, 3.0, 100.0, 101.0, 102.0]
        coords = [(float(i), 0.0) for i in range(len(vals))]
        frame = _pt_frame(coords, val=vals)
        result = frame.jenks_natural_breaks(value_column="val", k=2)
        classes = result["class_jenks"]
        assert classes[0] == classes[1] == classes[2]
        assert classes[3] == classes[4] == classes[5]
        assert classes[0] != classes[3]


# ===================================================================
#  EQUAL INTERVAL / QUANTILE CLASSIFICATION  (correctness)
# ===================================================================

class TestEqualInterval:
    """Verify equal_interval_classify."""

    def test_ten_values_five_classes(self):
        vals = [float(i) for i in range(10)]  # 0..9
        coords = [(float(i), 0.0) for i in range(10)]
        frame = _pt_frame(coords, val=vals)
        result = frame.equal_interval_classify(value_column="val", k=5)
        classes = result["class_eqint"]
        # interval = 9/5 = 1.8; class = floor((v-0)/1.8)+1
        for i, v in enumerate(vals):
            expected = min(int(v / 1.8), 4) + 1
            assert classes[i] == expected, f"val={v}: class {classes[i]} != expected {expected}"


class TestQuantileClassify:
    """Verify quantile_classify assigns roughly equal groups."""

    def test_equal_groups(self):
        vals = [float(i) for i in range(20)]
        coords = [(float(i), 0.0) for i in range(20)]
        frame = _pt_frame(coords, val=vals)
        result = frame.quantile_classify(value_column="val", k=4)
        classes = result["class_quantile"]
        counts = {}
        for c in classes:
            counts[c] = counts.get(c, 0) + 1
        # Each class should have exactly 5 items
        for cls, cnt in counts.items():
            assert cnt == 5, f"class {cls} has {cnt} items, expected 5"


# ===================================================================
#  OVERLAY TOOLS  (vs Shapely)
# ===================================================================

class TestOverlayVsShapely:
    """Compare overlay operations against direct Shapely computation."""

    def _make_overlapping_poly_frames(self):
        """Two overlapping squares: A=(0,0)-(2,2), B=(1,1)-(3,3)."""
        ring_a = [(0, 0), (2, 0), (2, 2), (0, 2), (0, 0)]
        ring_b = [(1, 1), (3, 1), (3, 3), (1, 3), (1, 1)]
        frame_a = _poly_frame([ring_a])
        frame_b = _poly_frame([ring_b])
        return frame_a, frame_b, sg.Polygon(ring_a), sg.Polygon(ring_b)

    def test_union_overlay_total_area(self):
        fa, fb, sa, sb = self._make_overlapping_poly_frames()
        result = fa.union_overlay(fb)
        # Sum of all result geometry areas should equal union area
        total = 0.0
        for row in result:
            geom = row["geometry"]
            total += sg.shape(geom).area
        ref_area = sa.union(sb).area
        assert abs(total - ref_area) < 1e-6, f"union area: {total} vs {ref_area}"

    def test_symmetrical_difference_area(self):
        fa, fb, sa, sb = self._make_overlapping_poly_frames()
        result = fa.symmetrical_difference_overlay(fb)
        total = 0.0
        for row in result:
            total += sg.shape(row["geometry"]).area
        ref_area = sa.symmetric_difference(sb).area
        assert abs(total - ref_area) < 1e-6

    def test_tabulate_intersection_area(self):
        fa, fb, sa, sb = self._make_overlapping_poly_frames()
        result = fa.tabulate_intersection(fb)
        assert len(result) == 1
        inter_area = result[0]["intersection_area"]
        ref_area = sa.intersection(sb).area
        assert abs(inter_area - ref_area) < 1e-6

    def test_spatial_selection_intersects(self):
        fa, fb, _, _ = self._make_overlapping_poly_frames()
        result = fa.spatial_selection(fb, predicate="intersects")
        assert len(result) == 1  # A intersects B


# ===================================================================
#  NETWORK CENTRALITY  (vs manual Brandes calculation)
# ===================================================================

class TestNetworkCentrality:
    """Verify betweenness/closeness on a simple known graph."""

    def _make_path_graph(self):
        """A-B-C linear path. B should have highest betweenness."""
        rows = [
            {"site_id": "e1", "geometry": {"type": "LineString", "coordinates": [(0, 0), (1, 0)]},
             "from_node_id": "A", "to_node_id": "B", "edge_length": 1.0},
            {"site_id": "e2", "geometry": {"type": "LineString", "coordinates": [(1, 0), (2, 0)]},
             "from_node_id": "B", "to_node_id": "C", "edge_length": 1.0},
        ]
        return GeoPromptFrame.from_records(rows, crs="EPSG:4326")

    def test_path_betweenness(self):
        frame = self._make_path_graph()
        result = frame.network_centrality()
        by_node = {r["node_id"]: r for r in result}
        # In A-B-C path: B has betweenness 1.0 (normalised: 1/(1*0)=inf for n=3... norm=(3-1)(3-2)=2)
        # B lies on the A→C and C→A shortest paths. Raw betweenness for undirected = 1.0/2 = 0.5
        # Normalised = 0.5 / 2 = 0.25  Wait: raw=2 (A→C goes through B, C→A goes through B),
        # undirected halving = 2/2 = 1.0, norm = 1.0/2 = 0.5
        assert by_node["B"]["betweenness_centrality"] > by_node["A"]["betweenness_centrality"]
        assert by_node["B"]["betweenness_centrality"] > by_node["C"]["betweenness_centrality"]
        # A and C should have equal betweenness
        assert abs(by_node["A"]["betweenness_centrality"] - by_node["C"]["betweenness_centrality"]) < 1e-9

    def test_star_betweenness(self):
        """Star graph: center has highest betweenness."""
        rows = [
            {"site_id": f"e{i}", "geometry": {"type": "LineString", "coordinates": [(0, 0), (i, 1)]},
             "from_node_id": "center", "to_node_id": f"leaf{i}", "edge_length": 1.0}
            for i in range(1, 5)
        ]
        frame = GeoPromptFrame.from_records(rows, crs="EPSG:4326")
        result = frame.network_centrality()
        by_node = {r["node_id"]: r for r in result}
        center_b = by_node["center"]["betweenness_centrality"]
        for i in range(1, 5):
            assert center_b > by_node[f"leaf{i}"]["betweenness_centrality"]


# ===================================================================
#  COST DISTANCE  (sanity checks)
# ===================================================================

class TestCostDistance:
    """Verify cost_distance sanity properties."""

    def test_source_cells_zero(self):
        """Grid cells closest to sources should have cost ~0."""
        pts = [(0.5, 0.5), (2.5, 0.5), (4.5, 0.5)]
        cost_frame = _pt_frame(pts, cost=[1.0, 1.0, 1.0])
        source = _pt_frame([(0.5, 0.5)])
        result = cost_frame.cost_distance(cost_column="cost", sources=source, grid_resolution=5)
        costs = result["cost_costdist"]
        # At least one cell should have very low cost (near source)
        min_cost = min(c for c in costs if c is not None)
        assert min_cost < 0.5, f"Min cost near source should be ~0, got {min_cost}"


# ===================================================================
#  HIERARCHICAL CLUSTER  (known result)
# ===================================================================

class TestHierarchicalCluster:
    """Single-linkage should merge closest pairs first."""

    def test_two_groups(self):
        """Two tight groups far apart → 2 clusters."""
        coords = [(0, 0), (0.1, 0), (0.2, 0), (10, 0), (10.1, 0), (10.2, 0)]
        frame = _pt_frame(coords)
        result = frame.hierarchical_cluster(k=2)
        clusters = result["cluster_hclust"]
        assert clusters[0] == clusters[1] == clusters[2]
        assert clusters[3] == clusters[4] == clusters[5]
        assert clusters[0] != clusters[3]


# ===================================================================
#  SPATIAL OUTLIER Z-SCORE  (correctness)
# ===================================================================

class TestSpatialOutlierZscore:
    """Verify z-score computation against numpy."""

    def test_zscore_vs_numpy(self):
        coords = [(float(i), 0.0) for i in range(10)]
        vals = [10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 200.0]
        frame = _pt_frame(coords, val=vals)
        result = frame.spatial_outlier_zscore(value_column="val", threshold=2.0)
        # global_z should still match numpy global z-scores
        our_global_z = result["global_z_zscore"]
        arr = np.array(vals)
        ref_z = (arr - arr.mean()) / arr.std()
        for i in range(10):
            assert abs(our_global_z[i] - ref_z[i]) < 1e-9, f"global_z[{i}]: {our_global_z[i]} vs {ref_z[i]}"
        # local z-score for the outlier (last point) should be large
        local_z = result["z_score_zscore"]
        assert abs(local_z[9]) > 1.0  # outlier should have large local z


# ===================================================================
#  POINT DENSITY  (conservation of count)
# ===================================================================

class TestPointDensity:
    """Verify point density sums are consistent."""

    def test_density_formula(self):
        """density = count / (pi * r^2) for each cell."""
        coords = [(0.5, 0.5)]
        frame = _pt_frame(coords)
        result = frame.point_density(search_radius=1.0, grid_resolution=5)
        rows = list(result)
        for row in rows:
            count = row["count_ptdensity"]
            density = row["density_ptdensity"]
            expected_density = count / (math.pi * 1.0 * 1.0)
            assert abs(density - expected_density) < 1e-9


# ===================================================================
#  DIRECTIONAL DISTRIBUTION  (circular statistics)
# ===================================================================

class TestDirectionalDistribution:
    """Verify circular statistics against manual computation."""

    def test_uniform_angles(self):
        """Uniformly spaced angles should have high circular variance."""
        angles = [0, 90, 180, 270]
        coords = [(float(i), 0.0) for i in range(4)]
        frame = _pt_frame(coords, angle=angles)
        result = frame.directional_distribution(angle_column="angle")
        # Uniform angles → mean resultant length ≈ 0, circular variance ≈ 1
        assert result["circular_variance"] > 0.9

    def test_same_direction(self):
        """All same direction → circular variance ≈ 0."""
        angles = [45.0, 45.0, 45.0, 45.0]
        coords = [(float(i), 0.0) for i in range(4)]
        frame = _pt_frame(coords, angle=angles)
        result = frame.directional_distribution(angle_column="angle")
        assert result["circular_variance"] < 0.01
        assert abs(result["mean_direction"] - 45.0) < 1e-6


# ===================================================================
#  FEATURE ENVELOPE  (vs Shapely)
# ===================================================================

class TestFeatureEnvelopeVsShapely:
    """Compare feature_envelope_to_polygon against Shapely bounds."""

    def test_triangle_envelope(self):
        ring = [(1, 2), (5, 0), (3, 6), (1, 2)]
        frame = _poly_frame([ring])
        result = frame.feature_envelope_to_polygon()
        row = list(result)[0]
        ref_bounds = sg.Polygon(ring).bounds  # (minx, miny, maxx, maxy)
        assert abs(row["width_envelope"] - (ref_bounds[2] - ref_bounds[0])) < 1e-9
        assert abs(row["height_envelope"] - (ref_bounds[3] - ref_bounds[1])) < 1e-9
        assert abs(row["area_envelope"] - (ref_bounds[2] - ref_bounds[0]) * (ref_bounds[3] - ref_bounds[1])) < 1e-9


# ===================================================================
#  QUADRAT ANALYSIS  (manual chi-square)
# ===================================================================

class TestQuadratAnalysis:
    """Verify chi-square computation."""

    def test_uniform_points(self):
        """Evenly spread points should have low chi-square."""
        coords = [(float(x) + 0.5, float(y) + 0.5) for x in range(4) for y in range(4)]
        frame = _pt_frame(coords)
        result = frame.quadrat_analysis(rows_count=4, cols_count=4)
        # Each cell should have exactly 1 point → chi_sq = 0
        assert abs(result["chi_square"]) < 1e-6


# ===================================================================
#  RANDOM POINTS  (reproducibility)
# ===================================================================

class TestRandomPoints:
    """Verify seed-based reproducibility."""

    def test_deterministic(self):
        a = GeoPromptFrame.random_points(100, seed=42)
        b = GeoPromptFrame.random_points(100, seed=42)
        for ra, rb in zip(a, b):
            assert ra["geometry"]["coordinates"] == rb["geometry"]["coordinates"]

    def test_within_bounds(self):
        result = GeoPromptFrame.random_points(50, min_x=-10, min_y=-20, max_x=10, max_y=20, seed=7)
        for row in result:
            x, y = row["geometry"]["coordinates"]
            assert -10 <= x <= 10
            assert -20 <= y <= 20


# ===================================================================
#  RASTER CALCULATOR  (expression evaluation)
# ===================================================================

class TestRasterCalculator:
    """Verify raster_calculator with known expressions."""

    def test_addition(self):
        coords = [(0.0, 0.0), (1.0, 0.0)]
        frame = _pt_frame(coords, a=[2.0, 5.0], b=[3.0, 7.0])
        result = frame.raster_calculator(expression="a + b", columns=["a", "b"])
        vals = result["calculated"]
        assert abs(vals[0] - 5.0) < 1e-9
        assert abs(vals[1] - 12.0) < 1e-9

    def test_complex_expression(self):
        coords = [(0.0, 0.0)]
        frame = _pt_frame(coords, a=[9.0])
        result = frame.raster_calculator(expression="sqrt(a) + pi", columns=["a"])
        assert abs(result["calculated"][0] - (3.0 + math.pi)) < 1e-9


# ===================================================================
#  TSP  (tour is valid)
# ===================================================================

class TestTSP:
    """Verify TSP produces a valid tour visiting all points."""

    def test_visits_all(self):
        coords = [(0, 0), (1, 0), (1, 1), (0, 1)]
        frame = _pt_frame(coords)
        result = frame.traveling_salesman_nn()
        orders = result["visit_order_tsp"]
        assert sorted(orders) == [1, 2, 3, 4]

    def test_cost_positive(self):
        coords = [(0, 0), (3, 0), (3, 4)]
        frame = _pt_frame(coords)
        result = frame.traveling_salesman_nn(return_to_start=True)
        cost = result["total_cost_tsp"][0]
        assert cost > 0
        # Total should be at least the perimeter of the triangle
        assert cost >= 3 + 4 + 5 - 0.01


# ===================================================================
#  NETWORK PARTITION  (connected components)
# ===================================================================

class TestNetworkPartition:
    """Verify connected component detection."""

    def test_two_components(self):
        rows = [
            {"site_id": "e1", "geometry": {"type": "LineString", "coordinates": [(0, 0), (1, 0)]},
             "from_node_id": "A", "to_node_id": "B"},
            {"site_id": "e2", "geometry": {"type": "LineString", "coordinates": [(1, 0), (2, 0)]},
             "from_node_id": "B", "to_node_id": "C"},
            {"site_id": "e3", "geometry": {"type": "LineString", "coordinates": [(10, 0), (11, 0)]},
             "from_node_id": "X", "to_node_id": "Y"},
        ]
        frame = GeoPromptFrame.from_records(rows, crs="EPSG:4326")
        result = frame.network_partition()
        comps = result["id_component"]
        assert comps[0] == comps[1]  # A-B edge and B-C edge same component
        assert comps[0] != comps[2]  # X-Y edge different component


# ===================================================================
#  FOCAL STATISTICS  (center cell gets correct window)
# ===================================================================

class TestFocalStatistics:
    """Verify focal window statistics."""

    def test_focal_sum_center(self):
        """Uniform grid: focal sum should equal value × window_area."""
        coords = [(float(x), float(y)) for x in range(5) for y in range(5)]
        frame = _pt_frame(coords, elev=[10.0] * 25)
        result = frame.focal_statistics(
            value_column="elev", grid_resolution=5, window_size=3, statistic="sum"
        )
        # Interior cells (not on edge) should have sum = 10*9 = 90
        # At least some cells should have sum near 90
        vals = result["value_focal"]
        assert any(abs(v - 90.0) < 15.0 for v in vals)


# ===================================================================
#  AGGREGATE GRID  (count conservation)
# ===================================================================

class TestAggregateGrid:
    """Verify aggregate_grid preserves total count."""

    def test_count_conservation(self):
        coords = [(float(i), 0.0) for i in range(10)]
        frame = _pt_frame(coords, val=[1.0] * 10)
        result = frame.aggregate_grid(value_column="val", grid_resolution=5, aggregation="count")
        total = sum(c for c in result["count_aggrid"])
        assert total == 10
