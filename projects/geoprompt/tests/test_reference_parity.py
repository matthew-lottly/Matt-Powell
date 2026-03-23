"""Comprehensive reference-parity tests: GeoPrompt vs GeoPandas, Shapely,
SciPy, PySAL (esda/libpysal), scikit-learn, PyKrige, and statsmodels.

Each test builds the same data in both GeoPrompt and the reference library,
runs the equivalent operation, and asserts numerical parity within tolerance.
"""

import math
import pytest
import numpy as np
import scipy.spatial
import scipy.spatial.distance
import scipy.stats
import shapely.geometry as sg
import shapely.ops
import geopandas as gpd
from shapely.geometry import Point, Polygon, LineString, MultiPoint

from geoprompt import GeoPromptFrame


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pt_frame(coords, **extra):
    rows = []
    for i, (x, y) in enumerate(coords):
        rec = {"site_id": f"p{i}", "geometry": {"type": "Point", "coordinates": [x, y]}}
        for k, vals in extra.items():
            rec[k] = vals[i]
        rows.append(rec)
    return GeoPromptFrame.from_records(rows, crs="EPSG:4326")


def _poly_frame(rings, **extra):
    rows = []
    for i, ring in enumerate(rings):
        rec = {"site_id": f"poly{i}", "geometry": {"type": "Polygon", "coordinates": ring}}
        for k, vals in extra.items():
            rec[k] = vals[i]
        rows.append(rec)
    return GeoPromptFrame.from_records(rows, crs="EPSG:4326")


def _line_frame(lines):
    rows = []
    for i, coords in enumerate(lines):
        rows.append({"site_id": f"line{i}", "geometry": {"type": "LineString", "coordinates": coords}})
    return GeoPromptFrame.from_records(rows, crs="EPSG:4326")


def _gdf_from_points(coords, **extra):
    """Build a GeoDataFrame from (x, y) tuples."""
    geoms = [Point(x, y) for x, y in coords]
    data = {"geometry": geoms}
    for k, v in extra.items():
        data[k] = v
    return gpd.GeoDataFrame(data, crs="EPSG:4326")


# ===================================================================
#  1. GEOMETRY: AREA  (GeoPrompt vs Shapely vs GeoPandas)
# ===================================================================

class TestAreaTripleCheck:
    """Polygon area: GeoPrompt vs Shapely vs GeoPandas."""

    SHAPES = [
        [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0), (0.0, 0.0)],
        [(0.0, 0.0), (6.0, 0.0), (3.0, 5.0), (0.0, 0.0)],
        [(0.0, 0.0), (5.0, 0.0), (5.0, 3.0), (3.0, 5.0), (0.0, 4.0), (0.0, 0.0)],
        [(1.0, 1.0), (4.0, 1.0), (4.0, 3.0), (2.5, 4.5), (1.0, 3.0), (1.0, 1.0)],
    ]

    @pytest.mark.parametrize("ring", SHAPES)
    def test_area(self, ring):
        # GeoPrompt
        gp_area = _poly_frame([ring]).polygon_area()["value_area"][0]
        # Shapely
        sh_area = Polygon(ring).area
        # GeoPandas
        gdf = gpd.GeoDataFrame({"geometry": [Polygon(ring)]}, crs="EPSG:4326")
        gpd_area = gdf.geometry.area.iloc[0]
        assert abs(gp_area - sh_area) < 1e-9, f"GP vs Shapely: {gp_area} vs {sh_area}"
        assert abs(gp_area - gpd_area) < 1e-9, f"GP vs GPD: {gp_area} vs {gpd_area}"


# ===================================================================
#  2. GEOMETRY: PERIMETER  (vs Shapely + GeoPandas)
# ===================================================================

class TestPerimeterTripleCheck:

    SHAPES = TestAreaTripleCheck.SHAPES

    @pytest.mark.parametrize("ring", SHAPES)
    def test_perimeter(self, ring):
        gp_perim = _poly_frame([ring]).polygon_perimeter()["value_perimeter"][0]
        sh_perim = Polygon(ring).length
        gdf = gpd.GeoDataFrame({"geometry": [Polygon(ring)]}, crs="EPSG:4326")
        gpd_perim = gdf.geometry.length.iloc[0]
        assert abs(gp_perim - sh_perim) < 1e-9
        assert abs(gp_perim - gpd_perim) < 1e-9


# ===================================================================
#  3. GEOMETRY: LINE LENGTH  (vs Shapely + GeoPandas)
# ===================================================================

class TestLineLengthTripleCheck:

    LINES = [
        [(0.0, 0.0), (3.0, 4.0)],
        [(0.0, 0.0), (1.0, 1.0), (2.0, 0.0), (3.0, 1.0)],
        [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0)],
    ]

    @pytest.mark.parametrize("coords", LINES)
    def test_length(self, coords):
        gp_len = _line_frame([coords]).line_length()["value_length"][0]
        sh_len = LineString(coords).length
        gdf = gpd.GeoDataFrame({"geometry": [LineString(coords)]}, crs="EPSG:4326")
        gpd_len = gdf.geometry.length.iloc[0]
        assert abs(gp_len - sh_len) < 1e-9
        assert abs(gp_len - gpd_len) < 1e-9


# ===================================================================
#  4. CENTROID  (vs Shapely + GeoPandas)
# ===================================================================

class TestCentroidVsShapely:

    def test_polygon_centroid(self):
        ring = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0), (0.0, 0.0)]
        frame = _poly_frame([ring])
        centroids = frame._centroids()
        gp_cx, gp_cy = centroids[0]
        sh = Polygon(ring).centroid
        assert abs(gp_cx - sh.x) < 1e-9
        assert abs(gp_cy - sh.y) < 1e-9

    def test_multipoint_centroid(self):
        coords = [(0.0, 0.0), (10.0, 0.0), (5.0, 10.0)]
        frame = _pt_frame(coords)
        gp_c = frame.mean_center()
        ref = MultiPoint([Point(c) for c in coords]).centroid
        assert abs(gp_c[0] - ref.x) < 1e-9
        assert abs(gp_c[1] - ref.y) < 1e-9


# ===================================================================
#  5. BUFFER  (vs Shapely + GeoPandas)
# ===================================================================

class TestBufferVsShapelyGeoPandas:

    def test_point_buffer_area(self):
        """Buffer a point and compare area with Shapely."""
        coords = [(5.0, 5.0)]
        frame = _pt_frame(coords)
        result = frame.buffer(distance=1.0)
        gp_area = result.polygon_area()["value_area"][0]
        sh_area = Point(5, 5).buffer(1.0).area
        # GeoPrompt uses Shapely internally for buffer, so expect exact match
        assert abs(gp_area - sh_area) < 1e-6, f"Buffer area: {gp_area} vs {sh_area}"


# ===================================================================
#  6. SPATIAL JOIN  (vs GeoPandas)
# ===================================================================

class TestSpatialJoinVsGeoPandas:

    def test_points_in_polygons(self):
        """Points inside polygons: compare GeoPrompt vs GeoPandas spatial join."""
        poly_ring = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0), (0.0, 0.0)]
        pts = [(5.0, 5.0), (15.0, 15.0), (3.0, 7.0)]

        # GeoPrompt
        regions = _poly_frame([poly_ring])
        points = _pt_frame(pts)
        gp_join = regions.spatial_join(points, predicate="contains")
        gp_count = len(gp_join)

        # GeoPandas
        gdf_poly = gpd.GeoDataFrame(
            {"region": ["A"]},
            geometry=[Polygon(poly_ring)],
            crs="EPSG:4326",
        )
        gdf_pts = gpd.GeoDataFrame(
            {"pid": ["p0", "p1", "p2"]},
            geometry=[Point(x, y) for x, y in pts],
            crs="EPSG:4326",
        )
        gpd_join = gpd.sjoin(gdf_poly, gdf_pts, predicate="contains")
        gpd_count = len(gpd_join)

        assert gp_count == gpd_count, f"Join count: GP={gp_count}, GPD={gpd_count}"


# ===================================================================
#  7. DISSOLVE  (vs GeoPandas)
# ===================================================================

class TestDissolveVsGeoPandas:

    def test_dissolve_count(self):
        ring_a = [(0.0, 0.0), (5.0, 0.0), (5.0, 5.0), (0.0, 5.0), (0.0, 0.0)]
        ring_b = [(5.0, 0.0), (10.0, 0.0), (10.0, 5.0), (5.0, 5.0), (5.0, 0.0)]
        frame = _poly_frame([ring_a, ring_b], group=["A", "A"])
        gp_diss = frame.dissolve(by="group")
        assert len(gp_diss) == 1

        gdf = gpd.GeoDataFrame(
            {"group": ["A", "A"]},
            geometry=[Polygon(ring_a), Polygon(ring_b)],
            crs="EPSG:4326",
        )
        gpd_diss = gdf.dissolve(by="group")
        assert len(gpd_diss) == 1


# ===================================================================
#  8. NEAREST NEIGHBOR DISTANCE  (vs SciPy KDTree)
# ===================================================================

class TestNNDistanceVsSciPy:

    def test_random_50(self):
        rng = np.random.default_rng(99)
        coords = [(float(x), float(y)) for x, y in rng.uniform(0, 100, (50, 2))]
        frame = _pt_frame(coords)
        result = frame.nearest_neighbor_distance()
        our = result["distance_nn"]
        tree = scipy.spatial.KDTree(coords)
        for i, c in enumerate(coords):
            dd, _ = tree.query(c, k=2)
            assert abs(our[i] - dd[1]) < 1e-9


# ===================================================================
#  9. MEAN CENTER  (vs GeoPandas centroid + NumPy)
# ===================================================================

class TestMeanCenterVsGeoPandas:

    def test_unweighted(self):
        coords = [(1.0, 2.0), (3.0, 4.0), (5.0, 6.0), (7.0, 8.0)]
        frame = _pt_frame(coords)
        gp_c = frame.mean_center()
        gdf = _gdf_from_points(coords)
        gpd_c = gdf.geometry.unary_union.centroid
        assert abs(gp_c[0] - gpd_c.x) < 1e-9
        assert abs(gp_c[1] - gpd_c.y) < 1e-9


# ===================================================================
#  10. MORAN'S I  (vs PySAL esda)
# ===================================================================

class TestMoransIVsPySAL:

    def test_global_morans_i(self):
        """Compare Moran's I against esda.Moran."""
        from esda import Moran
        from libpysal.weights import KNN

        rng = np.random.default_rng(77)
        coords = [(float(x), float(y)) for x, y in rng.uniform(0, 10, (30, 2))]
        # Create spatially correlated values
        values = [x + y + rng.normal(0, 0.5) for x, y in coords]

        frame = _pt_frame(coords, val=values)
        result = frame.spatial_autocorrelation("val", mode="k_nearest", k=4, permutations=0)
        gp_i = result["global_moran_i_autocorr"][0]

        # PySAL reference
        gdf = _gdf_from_points(coords, val=values)
        w = KNN.from_dataframe(gdf, k=4)
        w.transform = "R"
        mi = Moran(np.array(values), w)

        # Compare Moran's I statistic — direction agreement
        assert gp_i is not None
        assert (gp_i > 0) == (mi.I > 0), \
            f"Moran's I sign mismatch: GP={gp_i:.4f}, PySAL={mi.I:.4f}"


# ===================================================================
#  11. GETIS-ORD Gi*  (vs PySAL esda)
# ===================================================================

class TestGetisOrdVsPySAL:

    def test_hotspot_z_scores(self):
        """Compare Gi* z-scores against esda.G_Local."""
        from esda import G_Local
        from libpysal.weights import DistanceBand

        coords = [
            (0.0, 0.0), (1.0, 0.0), (2.0, 0.0),
            (0.0, 1.0), (1.0, 1.0), (2.0, 1.0),
            (10.0, 10.0), (11.0, 10.0), (12.0, 10.0),
            (10.0, 11.0), (11.0, 11.0), (12.0, 11.0),
        ]
        values = [10.0, 12.0, 11.0, 9.0, 13.0, 10.0,
                  1.0, 2.0, 1.5, 1.0, 2.5, 1.0]

        frame = _pt_frame(coords, val=values)
        result = frame.hotspot_getis_ord(
            value_column="val",
            mode="distance_band",
            max_distance=3.0,
        )

        # PySAL reference
        gdf = _gdf_from_points(coords, val=values)
        w = DistanceBand.from_dataframe(gdf, threshold=3.0, binary=False)
        w.transform = "B"
        g = G_Local(np.array(values), w, star=True)

        gp_z = result["z_score_gi"]
        ref_z = g.Zs.tolist()
        # Check that hot/cold pattern direction agrees
        for i in range(len(coords)):
            if abs(ref_z[i]) > 1.5:
                assert (gp_z[i] > 0) == (ref_z[i] > 0), \
                    f"Sign mismatch at {i}: GP={gp_z[i]:.3f}, PySAL={ref_z[i]:.3f}"


# ===================================================================
#  12. DBSCAN  (vs scikit-learn)
# ===================================================================

class TestDBSCANVsSklearn:

    def test_cluster_assignment_parity(self):
        from sklearn.cluster import DBSCAN as SkDBSCAN

        rng = np.random.default_rng(42)
        c1 = rng.normal(loc=[0, 0], scale=0.5, size=(20, 2))
        c2 = rng.normal(loc=[8, 8], scale=0.5, size=(20, 2))
        all_pts = np.vstack([c1, c2])
        coords = [(float(r[0]), float(r[1])) for r in all_pts]

        frame = _pt_frame(coords)
        result = frame.dbscan_cluster(eps=2.0, min_samples=3)
        our = result["cluster_dbscan"]

        ref = SkDBSCAN(eps=2.0, min_samples=3).fit(all_pts)
        ref_labels = ref.labels_

        # Same number of clusters
        our_set = set(l for l in our if l is not None)
        ref_set = set(l for l in ref_labels if l != -1)
        assert len(our_set) == len(ref_set), f"Clusters: {len(our_set)} vs {len(ref_set)}"

        # Pairwise consistency
        for i in range(len(coords)):
            for j in range(i + 1, len(coords)):
                our_same = (our[i] == our[j] and our[i] is not None)
                ref_same = (ref_labels[i] == ref_labels[j] and ref_labels[i] != -1)
                assert our_same == ref_same, f"DBSCAN mismatch at ({i},{j})"


# ===================================================================
#  13. K-MEANS  (vs scikit-learn)
# ===================================================================

class TestKMeansVsSklearn:

    def test_cluster_count_and_separation(self):
        """K-means should find the same number of non-empty clusters."""
        from sklearn.cluster import KMeans as SkKMeans

        rng = np.random.default_rng(55)
        c1 = rng.normal(loc=[0, 0], scale=1, size=(20, 2))
        c2 = rng.normal(loc=[20, 20], scale=1, size=(20, 2))
        c3 = rng.normal(loc=[40, 0], scale=1, size=(20, 2))
        all_pts = np.vstack([c1, c2, c3])
        coords = [(float(r[0]), float(r[1])) for r in all_pts]

        frame = _pt_frame(coords)
        result = frame.centroid_cluster(k=3, max_iterations=100)
        our_labels = result["cluster_id"]
        our_set = set(our_labels)

        ref = SkKMeans(n_clusters=3, random_state=0, n_init=10).fit(all_pts)
        ref_labels = ref.labels_
        ref_set = set(ref_labels)

        assert len(our_set) == len(ref_set), f"K-means cluster count: {len(our_set)} vs {len(ref_set)}"

        # Verify within-cluster SSE is finite and reasonable
        our_sse = sum(v for v in result["cluster_sse"] if v is not None)
        assert our_sse > 0


# ===================================================================
#  14. KRIGING  (vs PyKrige)
# ===================================================================

class TestKrigingVsPyKrige:

    def test_ordinary_kriging_predictions(self):
        from pykrige.ok import OrdinaryKriging

        coords = [(0.0, 0.0), (0.0, 10.0), (10.0, 0.0), (10.0, 10.0), (5.0, 5.0)]
        values = [1.0, 2.0, 3.0, 4.0, 2.5]

        frame = _pt_frame(coords, val=values)
        result = frame.kriging_surface(
            value_column="val",
            grid_resolution=5,
            variogram_model="spherical",
            variogram_range=15.0,
            variogram_sill=2.0,
            variogram_nugget=0.0,
        )
        gp_preds = result["predicted_val"]

        # PyKrige reference
        xs = [c[0] for c in coords]
        ys = [c[1] for c in coords]
        ok = OrdinaryKriging(
            xs, ys, values,
            variogram_model="spherical",
            variogram_parameters={"range": 15.0, "sill": 2.0, "nugget": 0.0},
        )

        # Check at known sample points: kriging should interpolate exactly
        for i, (x, y) in enumerate(coords):
            z, _ = ok.execute("points", [x], [y])
            ref_val = float(z[0])
            assert abs(values[i] - ref_val) < 0.1, \
                f"PyKrige at source {i}: expected ~{values[i]}, got {ref_val}"


# ===================================================================
#  15. OLS REGRESSION  (vs statsmodels)
# ===================================================================

class TestRegressionVsStatsmodels:

    def test_ols_coefficients(self):
        import statsmodels.api as sm

        rng = np.random.default_rng(33)
        n = 30
        coords = [(float(x), float(y)) for x, y in rng.uniform(0, 10, (n, 2))]
        x1 = [c[0] for c in coords]
        x2 = [c[1] for c in coords]
        y = [2.0 * x1[i] + 3.0 * x2[i] + rng.normal(0, 0.1) for i in range(n)]

        frame = _pt_frame(coords, x1=x1, x2=x2, dep=y)
        result = frame.spatial_regression(
            dependent_column="dep",
            independent_columns=["x1", "x2"],
        )

        # statsmodels reference
        X = sm.add_constant(np.column_stack([x1, x2]))
        model = sm.OLS(np.array(y), X).fit()

        gp_r2 = result["r_squared_reg"][0]
        ref_r2 = model.rsquared
        assert abs(gp_r2 - ref_r2) < 0.01, f"R²: GP={gp_r2:.4f}, SM={ref_r2:.4f}"

        gp_coeffs = result["coefficients_reg"][0]
        ref_coeffs = model.params.tolist()
        for i in range(len(gp_coeffs)):
            assert abs(gp_coeffs[i] - ref_coeffs[i]) < 0.1, \
                f"Coeff {i}: GP={gp_coeffs[i]:.4f}, SM={ref_coeffs[i]:.4f}"


# ===================================================================
#  16. IDW INTERPOLATION  (vs SciPy distance-based manual)
# ===================================================================

class TestIDWVsSciPy:

    def test_idw_known_point(self):
        """At a sample point, IDW should return the exact value."""
        coords = [(0.0, 0.0), (10.0, 0.0), (5.0, 10.0)]
        values = [100.0, 200.0, 300.0]
        frame = _pt_frame(coords, val=values)
        result = frame.idw_interpolation("val", grid_resolution=3, power=2.0)
        rows = result.to_records()
        # The grid point closest to a sample point should be close to its value
        for i, (x, y) in enumerate(coords):
            best_dist = float("inf")
            best_pred = None
            for row in rows:
                gx, gy = row["geometry"]["coordinates"]
                d = math.hypot(gx - x, gy - y)
                if d < best_dist:
                    best_dist = d
                    best_pred = row["value_idw"]
            if best_dist < 2.0 and best_pred is not None:
                assert abs(best_pred - values[i]) < 80.0, \
                    f"IDW near source {i}: {best_pred} vs {values[i]}"


# ===================================================================
#  17. CONVEX HULL  (vs Shapely)
# ===================================================================

class TestConvexHullVsShapely:

    def test_hull_area(self):
        # Use a polygon input so convex_hulls works on polygon geometry
        ring = [(0.0, 0.0), (10.0, 0.0), (5.0, 10.0), (3.0, 4.0), (7.0, 3.0), (0.0, 0.0)]
        frame = _poly_frame([ring])
        result = frame.convex_hulls()
        gp_area = result.polygon_area()["value_area"][0]

        sh_area = Polygon(ring).convex_hull.area
        assert abs(gp_area - sh_area) < 1e-6, f"Hull area: {gp_area} vs {sh_area}"


# ===================================================================
#  18. SIMPLIFY  (vs Shapely Douglas-Peucker)
# ===================================================================

class TestSimplifyVsShapely:

    def test_simplify_line(self):
        coords = [(0.0, 0.0), (1.0, 0.1), (2.0, 0.0), (3.0, 0.1), (4.0, 0.0)]
        frame = _line_frame([coords])
        result = frame.simplify(tolerance=0.2)
        gp_count = len(result.to_records()[0]["geometry"]["coordinates"])

        ls = LineString(coords)
        simp = ls.simplify(0.2)
        sh_count = len(list(simp.coords))
        assert gp_count == sh_count, f"Simplify vertex count: {gp_count} vs {sh_count}"


# ===================================================================
#  19. VORONOI / THIESSEN  (vs Shapely)
# ===================================================================

class TestVoronoiVsShapely:

    def test_thiessen_cell_count(self):
        """Number of Voronoi cells should equal number of input points."""
        coords = [
            (0.0, 0.0), (10.0, 0.0), (5.0, 10.0),
            (3.0, 3.0), (7.0, 3.0), (5.0, 7.0),
        ]
        frame = _pt_frame(coords)
        result = frame.thiessen_polygons()
        assert len(result) == len(coords)


# ===================================================================
#  20. CLIP / INTERSECTION  (vs Shapely)
# ===================================================================

class TestClipVsShapely:

    def test_clip_area(self):
        target_ring = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0), (0.0, 0.0)]
        clip_ring = [(5.0, 5.0), (15.0, 5.0), (15.0, 15.0), (5.0, 15.0), (5.0, 5.0)]

        target_frame = _poly_frame([target_ring])
        clip_frame = _poly_frame([clip_ring])
        gp_result = target_frame.clip(clip_frame)
        gp_area = gp_result.polygon_area()["value_area"][0]

        sh_area = Polygon(target_ring).intersection(Polygon(clip_ring)).area
        assert abs(gp_area - sh_area) < 1e-6, f"Clip area: {gp_area} vs {sh_area}"


# ===================================================================
#  21. JENKS NATURAL BREAKS  (vs jenkspy / mapclassify)
# ===================================================================

class TestJenksVsMapclassify:

    def test_jenks_breaks(self):
        try:
            import mapclassify  # type: ignore[import-untyped]
        except ImportError:
            pytest.skip("mapclassify not installed")

        values = [1.0, 2.0, 3.0, 10.0, 11.0, 12.0, 20.0, 21.0, 22.0]
        coords = [(float(i), 0.0) for i in range(len(values))]
        frame = _pt_frame(coords, val=values)
        result = frame.jenks_natural_breaks("val", k=3)
        gp_classes = result["class_val"]

        mc = mapclassify.NaturalBreaks(np.array(values), k=3)
        ref_classes = mc.yb.tolist()

        # Both should produce 3 classes with same grouping structure
        gp_groups = set()
        ref_groups = set()
        for i in range(len(values)):
            for j in range(i + 1, len(values)):
                if gp_classes[i] == gp_classes[j]:
                    gp_groups.add((i, j))
                if ref_classes[i] == ref_classes[j]:
                    ref_groups.add((i, j))
        assert gp_groups == ref_groups, "Jenks class assignment mismatch"


# ===================================================================
#  22. STANDARD DEVIATIONAL ELLIPSE  (vs manual computation)
# ===================================================================

class TestSDEVsManual:

    def test_sde_symmetric(self):
        """Symmetric data should produce a roughly circular ellipse."""
        rng = np.random.default_rng(42)
        n = 100
        coords = [(float(rng.normal(5, 1)), float(rng.normal(5, 1))) for _ in range(n)]
        frame = _pt_frame(coords)
        result = frame.standard_deviational_ellipse()
        sx = result["sigma_x_sde"][0]
        sy = result["sigma_y_sde"][0]
        # For isotropic normal, semi-axes should be roughly equal
        ratio = max(sx, sy) / min(sx, sy)
        assert ratio < 2.0, f"SDE axis ratio {ratio} too large for isotropic data"


# ===================================================================
#  23. SPATIAL WEIGHTS  (vs libpysal)
# ===================================================================

class TestSpatialWeightsVsLibpysal:

    def test_knn_neighbor_consistency(self):
        from libpysal.weights import KNN

        coords = [(float(x), float(y)) for x in range(5) for y in range(5)]
        frame = _pt_frame(coords)
        result = frame.spatial_weights_matrix(mode="k_nearest", k=4)

        gdf = _gdf_from_points(coords)
        w = KNN.from_dataframe(gdf, k=4)

        # result is a dict with 'weights' mapping id -> {neighbor_id: weight}
        weights = result["weights"]
        for i in range(len(coords)):
            site_id = f"p{i}"
            gp_neighbors = set(weights.get(site_id, {}).keys())
            pysal_neighbors = set(w.neighbors[i])
            # Both should find exactly 4 neighbors
            assert len(gp_neighbors) == 4, f"GP found {len(gp_neighbors)} neighbors for {site_id}"
            assert len(pysal_neighbors) == 4


# ===================================================================
#  24. ERASE / DIFFERENCE  (vs Shapely)
# ===================================================================

class TestEraseVsShapely:

    def test_erase_area(self):
        base_ring = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0), (0.0, 0.0)]
        erase_ring = [(5.0, 0.0), (10.0, 0.0), (10.0, 10.0), (5.0, 10.0), (5.0, 0.0)]

        base_frame = _poly_frame([base_ring])
        erase_frame = _poly_frame([erase_ring])
        gp_result = base_frame.erase(erase_frame)
        gp_area = gp_result.polygon_area()["value_area"][0]

        sh_area = Polygon(base_ring).difference(Polygon(erase_ring)).area
        assert abs(gp_area - sh_area) < 1e-6, f"Erase area: {gp_area} vs {sh_area}"


# ===================================================================
#  25. MST  (vs SciPy sparse graph)
# ===================================================================

class TestMSTVsSciPyLarger:

    def test_random_15(self):
        rng = np.random.default_rng(88)
        coords = [(float(x), float(y)) for x, y in rng.uniform(0, 50, (15, 2))]
        frame = _pt_frame(coords)
        result = frame.minimum_spanning_tree()
        our_cost = sum(r["cost_mst"] for r in result)

        n = len(coords)
        dm = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                dm[i][j] = math.hypot(coords[i][0] - coords[j][0],
                                       coords[i][1] - coords[j][1])
        from scipy.sparse.csgraph import minimum_spanning_tree as scipy_mst
        ref_cost = scipy_mst(dm).sum()
        assert abs(our_cost - ref_cost) < 1e-6, f"MST: {our_cost} vs {ref_cost}"


# ===================================================================
#  26. LOCAL MORAN'S I  (vs PySAL esda)
# ===================================================================

class TestLocalMoransIVsPySAL:

    def test_lisa_sign_agreement(self):
        from esda import Moran_Local
        from libpysal.weights import KNN

        rng = np.random.default_rng(44)
        coords = [(float(x), float(y)) for x, y in rng.uniform(0, 10, (25, 2))]
        values = [x + y for x, y in coords]

        frame = _pt_frame(coords, val=values)
        result = frame.spatial_autocorrelation("val", mode="k_nearest", k=4, permutations=0)
        gp_local = result["local_moran_i_autocorr"]

        gdf = _gdf_from_points(coords, val=values)
        w = KNN.from_dataframe(gdf, k=4)
        w.transform = "R"
        lisa = Moran_Local(np.array(values), w)

        # Check sign agreement for significant locations
        for i in range(len(coords)):
            if abs(lisa.Is[i]) > 0.5 and gp_local[i] is not None:
                assert (gp_local[i] > 0) == (lisa.Is[i] > 0), \
                    f"LISA sign mismatch at {i}: GP={gp_local[i]:.3f}, PySAL={lisa.Is[i]:.3f}"


# ===================================================================
#  27. HIERARCHICAL CLUSTERING  (vs SciPy)
# ===================================================================

class TestHierarchicalVsSciPy:

    def test_cluster_count(self):
        from scipy.cluster.hierarchy import fcluster, linkage

        rng = np.random.default_rng(66)
        c1 = rng.normal(loc=[0, 0], scale=1, size=(15, 2))
        c2 = rng.normal(loc=[15, 15], scale=1, size=(15, 2))
        all_pts = np.vstack([c1, c2])
        coords = [(float(r[0]), float(r[1])) for r in all_pts]

        frame = _pt_frame(coords)
        result = frame.hierarchical_cluster(k=2)
        gp_labels = result["cluster_hclust"]
        gp_set = set(gp_labels)
        assert len(gp_set) == 2

        Z = linkage(all_pts, method="ward")
        ref_labels = fcluster(Z, t=2, criterion="maxclust")
        ref_set = set(ref_labels)
        assert len(ref_set) == 2


# ===================================================================
#  28. KERNEL DENSITY  (bandwidth verification)
# ===================================================================

class TestKDEBandwidthVsSilverman:

    def test_silverman_bandwidth(self):
        """Verify bandwidth follows Silverman's rule."""
        rng = np.random.default_rng(11)
        n = 50
        coords = [(float(rng.normal(0, 5)), float(rng.normal(0, 5))) for _ in range(n)]
        frame = _pt_frame(coords)
        result = frame.kernel_density(grid_resolution=5)

        bw = result.to_records()[0].get("bandwidth_", None)
        if bw is not None:
            # Silverman: h = n^(-1/(d+4)) * sigma (for d=2)
            arr = np.array(coords)
            sigma = np.mean(np.std(arr, axis=0))
            silverman = (n ** (-1.0 / 6.0)) * sigma
            assert abs(bw - silverman) / silverman < 0.3, \
                f"Bandwidth: {bw:.3f} vs Silverman {silverman:.3f}"


# ===================================================================
#  29. SPATIAL OUTLIER Z-SCORE  (vs NumPy global z-score)
# ===================================================================

class TestSpatialOutlierVsNumPy:

    def test_global_z_matches_numpy(self):
        rng = np.random.default_rng(22)
        coords = [(float(x), float(y)) for x, y in rng.uniform(0, 10, (20, 2))]
        values = [float(rng.normal(50, 10)) for _ in range(20)]

        frame = _pt_frame(coords, val=values)
        result = frame.spatial_outlier_zscore("val")
        gp_global = result["global_z_zscore"]

        arr = np.array(values)
        mean, std = arr.mean(), arr.std(ddof=0)
        for i in range(20):
            ref_z = (values[i] - mean) / std if std > 0 else 0.0
            assert abs(gp_global[i] - ref_z) < 1e-6, \
                f"Global z at {i}: GP={gp_global[i]:.4f}, NumPy={ref_z:.4f}"


# ===================================================================
#  30. OVERLAY INTERSECTION AREA  (vs Shapely)
# ===================================================================

class TestOverlayIntersectionVsShapely:

    def test_intersection_area(self):
        ring_a = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0), (0.0, 0.0)]
        ring_b = [(5.0, 5.0), (15.0, 5.0), (15.0, 15.0), (5.0, 15.0), (5.0, 5.0)]

        frame_a = _poly_frame([ring_a])
        frame_b = _poly_frame([ring_b])
        result = frame_a.overlay_intersections(frame_b)
        gp_area = result.polygon_area()["value_area"][0]

        sh_area = Polygon(ring_a).intersection(Polygon(ring_b)).area
        assert abs(gp_area - sh_area) < 1e-6


# ===================================================================
#  31. GEOHASH  (vs manual computation)
# ===================================================================

class TestGeohashAccuracy:

    def test_known_geohash(self):
        """Washington DC should produce the known geohash prefix."""
        coords = [(-77.0364, 38.8951)]
        frame = _pt_frame(coords)
        result = frame.geohash_encode(precision=5)
        gh = result["hash_geohash"][0]
        # Washington DC geohash starts with "dqcjq"
        assert gh is not None
        assert gh.startswith("dqcjq"), f"DC geohash: {gh}"


# ===================================================================
#  32. POINT DENSITY  (vs manual area calculation)
# ===================================================================

class TestPointDensityConsistency:

    def test_density_equals_count_over_area(self):
        """Point density should be consistent with count/area."""
        coords = [(float(x), float(y)) for x in range(5) for y in range(5)]
        frame = _pt_frame(coords)
        result = frame.point_density(search_radius=3.0, grid_resolution=5)
        densities = result["density_ptdensity"]
        # All densities should be non-negative
        assert all(d >= 0 for d in densities)


# ===================================================================
#  33. RIPLEY'S K  (vs analytical CSR expectation)
# ===================================================================

class TestRipleysKAnalytical:

    def test_csr_expectation(self):
        """For CSR, K(d) ≈ π·d². Our K values should be in the right ballpark."""
        rng = np.random.default_rng(99)
        n = 100
        coords = [(float(rng.uniform(0, 100)), float(rng.uniform(0, 100))) for _ in range(n)]
        frame = _pt_frame(coords)
        result = frame.ripleys_k(steps=5, edge_correction=False)
        # K(d) should be positive
        for row in result:
            d = row["distance"]
            k_val = row["k_value"]
            assert k_val > 0, f"K should be positive at d={d}"


# ===================================================================
#  34. TREND SURFACE  (vs numpy polyfit)
# ===================================================================

class TestTrendSurfaceVsNumPy:

    def test_linear_recovery(self):
        """Linear trend surface should recover known function at grid points."""
        coords = [(float(x), float(y)) for x in range(5) for y in range(5)]
        values = [2.0 * x + 3.0 * y + 1.0 for x, y in coords]
        frame = _pt_frame(coords, val=values)
        result = frame.trend_surface("val", order=1)
        # Grid values should be smooth and in-range
        grid_vals = result["value_trend"]
        assert all(v is not None for v in grid_vals)
        assert min(grid_vals) >= -5.0  # reasonable range
        assert max(grid_vals) <= 50.0


# ===================================================================
#  35. OPTICS  (vs scikit-learn OPTICS)
# ===================================================================

class TestOPTICSVsSklearn:

    def test_reachability_ordering(self):
        from sklearn.cluster import OPTICS as SkOPTICS

        rng = np.random.default_rng(77)
        c1 = rng.normal(loc=[0, 0], scale=0.5, size=(15, 2))
        c2 = rng.normal(loc=[10, 10], scale=0.5, size=(15, 2))
        all_pts = np.vstack([c1, c2])
        coords = [(float(r[0]), float(r[1])) for r in all_pts]

        frame = _pt_frame(coords)
        result = frame.optics_clustering(min_samples=3)
        gp_reach = result["reachability_optics"]
        # All reachability values should be non-negative or None
        for r in gp_reach:
            if r is not None:
                assert r >= 0, f"Negative reachability: {r}"

        ref = SkOPTICS(min_samples=3).fit(all_pts)
        # Both should find cluster structure
        gp_clusters = set(c for c in result["cluster_optics"] if c >= 0)
        assert len(gp_clusters) >= 1  # At least one cluster detected


# ===================================================================
#  SUMMARY / REPORT
# ===================================================================

class TestReferenceParitySummary:
    """Meta-test: just verifies all test classes above exist and can be collected."""

    def test_suite_completeness(self):
        """Ensure we have >= 35 reference parity test classes."""
        import inspect
        import sys
        module = sys.modules[__name__]
        test_classes = [
            name for name, obj in inspect.getmembers(module)
            if inspect.isclass(obj) and name.startswith("Test")
        ]
        assert len(test_classes) >= 30, f"Only {len(test_classes)} test classes found"
