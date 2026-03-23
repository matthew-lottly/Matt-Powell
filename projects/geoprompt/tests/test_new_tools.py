"""Tests for tools 86–100."""
import math

from geoprompt import GeoPromptFrame


def _pt_frame(coords, val=None, val2=None, pop=None, factor=None, elev=None):
    rows = []
    for i, (x, y) in enumerate(coords):
        row = {
            "site_id": f"p{i}",
            "geometry": {"type": "Point", "coordinates": (x, y)},
        }
        if val is not None:
            row["val"] = val[i]
        if val2 is not None:
            row["val2"] = val2[i]
        if pop is not None:
            row["pop"] = pop[i]
        if factor is not None:
            row["factor"] = factor[i]
        if elev is not None:
            row["elev"] = elev[i]
        rows.append(row)
    return GeoPromptFrame.from_records(rows)


# Tool 86: bivariate_morans_i
class TestBivariateMoransI:
    def test_positive_correlation(self):
        # Clustered: similar values near each other
        coords = [(0, 0), (0.1, 0), (0.2, 0), (5, 0), (5.1, 0), (5.2, 0)]
        result = _pt_frame(coords, val=[10, 10, 10, 100, 100, 100], val2=[10, 10, 10, 100, 100, 100]).bivariate_morans_i("val", "val2", k=2)
        assert "I" in result
        assert result["I"] > 0  # positive spatial correlation

    def test_returns_fields(self):
        coords = [(0, 0), (1, 0), (2, 0), (3, 0)]
        result = _pt_frame(coords, val=[1, 2, 3, 4], val2=[4, 3, 2, 1]).bivariate_morans_i("val", "val2")
        assert "I" in result
        assert "p_value" in result
        assert result["n"] == 4

    def test_empty_frame(self):
        f = GeoPromptFrame.from_records([])
        # bivariate_morans_i requires columns; with < 3 rows returns defaults
        rows = [{"site_id": "a", "geometry": {"type": "Point", "coordinates": (0, 0)}, "val": 1, "val2": 1}]
        f = GeoPromptFrame.from_records(rows)
        result = f.bivariate_morans_i("val", "val2")
        assert result["n"] == 1

    def test_modes(self):
        coords = [(i, 0) for i in range(6)]
        f = _pt_frame(coords, val=[1, 2, 3, 4, 5, 6], val2=[2, 3, 4, 5, 6, 7])
        r_knn = f.bivariate_morans_i("val", "val2", mode="k_nearest", k=2)
        r_db = f.bivariate_morans_i("val", "val2", mode="distance_band", max_distance=2.0)
        assert isinstance(r_knn["I"], float)
        assert isinstance(r_db["I"], float)


# Tool 87: local_gearys_c
class TestLocalGearysC:
    def test_basic(self):
        coords = [(0, 0), (1, 0), (2, 0), (3, 0)]
        f = _pt_frame(coords, val=[10, 10, 10, 10])
        result = f.local_gearys_c("val")
        assert len(result) == 4
        for row in result:
            assert row["c_local_geary"] == 0.0  # identical values => zero

    def test_outlier(self):
        coords = [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0)]
        f = _pt_frame(coords, val=[10, 10, 10, 10, 100])
        result = f.local_gearys_c("val")
        assert len(result) == 5
        records = list(result)
        # Last point should have higher c (dissimilar to neighbors)
        assert records[-1]["c_local_geary"] > records[0]["c_local_geary"]

    def test_empty(self):
        f = GeoPromptFrame.from_records([{"site_id": "a", "geometry": {"type": "Point", "coordinates": (0, 0)}, "val": 1}])
        result = f.local_gearys_c("val")
        assert len(result) == 1


# Tool 88: loess_regression
class TestLoessRegression:
    def test_perfect_linear(self):
        coords = [(i, 0) for i in range(10)]
        f = _pt_frame(coords, val=[i * 2.0 for i in range(10)], val2=[float(i) for i in range(10)])
        result = f.loess_regression("val", "val2", fraction=0.5)
        assert len(result) == 10
        for row in result:
            assert abs(row["residual_loess"]) < 1.0  # close to perfect fit

    def test_degree_zero(self):
        coords = [(i, 0) for i in range(5)]
        f = _pt_frame(coords, val=[10, 10, 10, 10, 100], val2=[1, 2, 3, 4, 5])
        result = f.loess_regression("val", "val2", fraction=0.5, degree=0)
        assert len(result) == 5

    def test_empty(self):
        f = GeoPromptFrame.from_records([{"site_id": "a", "geometry": {"type": "Point", "coordinates": (0, 0)}, "val": 1, "val2": 1}])
        result = f.loess_regression("val", "val2")
        assert len(result) == 1


# Tool 89: spatial_scan_statistic
class TestSpatialScanStatistic:
    def test_cluster_detection(self):
        coords = [(0, 0), (0.1, 0), (0.2, 0), (5, 5), (5.1, 5), (5.2, 5)]
        cases = [10, 10, 10, 0, 0, 0]
        pops = [10, 10, 10, 100, 100, 100]
        f = _pt_frame(coords, val=cases, pop=pops)
        result = f.spatial_scan_statistic("val", "pop", n_simulations=9, seed=42)
        assert len(result) == 6
        records = list(result)
        cluster_members = [r for r in records if r["in_cluster_scan"]]
        assert len(cluster_members) > 0

    def test_empty(self):
        f = GeoPromptFrame.from_records([{"site_id": "a", "geometry": {"type": "Point", "coordinates": (0, 0)}, "val": 0}])
        result = f.spatial_scan_statistic("val")
        assert len(result) == 1


# Tool 90: optics_clustering
class TestOpticsClustering:
    def test_two_clusters(self):
        coords = [(0, 0), (0.1, 0), (0.2, 0), (10, 10), (10.1, 10), (10.2, 10)]
        f = _pt_frame(coords)
        result = f.optics_clustering(min_samples=2)
        assert len(result) == 6
        records = list(result)
        for r in records:
            assert "cluster_optics" in r
            assert "reachability_optics" in r

    def test_empty(self):
        result = GeoPromptFrame.from_records([]).optics_clustering()
        assert len(result) == 0


# Tool 91: geographic_detector
class TestGeographicDetector:
    def test_perfect_factor(self):
        coords = [(i, 0) for i in range(8)]
        vals = [10.0, 10.0, 10.0, 10.0, 100.0, 100.0, 100.0, 100.0]
        factors = ["A", "A", "A", "A", "B", "B", "B", "B"]
        f = _pt_frame(coords, val=vals, factor=factors)
        result = f.geographic_detector("val", "factor")
        assert result["q_statistic"] > 0.5  # factor explains significant variance
        assert result["strata_count"] == 2

    def test_random_factor(self):
        coords = [(i, 0) for i in range(8)]
        vals = [1, 100, 2, 99, 3, 98, 4, 97]
        factors = ["A", "A", "A", "A", "B", "B", "B", "B"]
        f = _pt_frame(coords, val=vals, factor=factors)
        result = f.geographic_detector("val", "factor")
        assert 0.0 <= result["q_statistic"] <= 1.0

    def test_empty(self):
        f = GeoPromptFrame.from_records([{"site_id": "a", "geometry": {"type": "Point", "coordinates": (0, 0)}, "val": 1, "factor": "A"}])
        result = f.geographic_detector("val", "factor")
        assert result["n"] == 1


# Tool 92: terrain_ruggedness_index
class TestTerrainRuggednessIndex:
    def test_flat(self):
        coords = [(0, 0), (1, 0), (2, 0), (3, 0)]
        f = _pt_frame(coords, elev=[100, 100, 100, 100])
        result = f.terrain_ruggedness_index("elev")
        for row in result:
            assert row["tri_tri"] == 0.0

    def test_rugged(self):
        coords = [(0, 0), (1, 0), (2, 0), (3, 0)]
        f = _pt_frame(coords, elev=[0, 100, 0, 100])
        result = f.terrain_ruggedness_index("elev")
        records = list(result)
        assert all(r["tri_tri"] > 0 for r in records)


# Tool 93: topographic_position_index
class TestTopographicPositionIndex:
    def test_ridge(self):
        coords = [(0, 0), (1, 0), (2, 0), (0, 1), (1, 1), (2, 1)]
        f = _pt_frame(coords, elev=[10, 100, 10, 10, 100, 10])
        result = f.topographic_position_index("elev", k=4)
        records = list(result)
        # Point 1 and 4 are ridges (high center, low surround)
        assert records[1]["tpi_tpi"] > 0  # middle-top is higher than neighbors

    def test_valley(self):
        coords = [(0, 0), (1, 0), (2, 0), (0, 1), (1, 1), (2, 1)]
        f = _pt_frame(coords, elev=[100, 10, 100, 100, 10, 100])
        result = f.topographic_position_index("elev", k=4)
        records = list(result)
        assert records[1]["tpi_tpi"] < 0  # middle is valley


# Tool 94: flow_direction
class TestFlowDirection:
    def test_downhill(self):
        coords = [(0, 0), (1, 0), (2, 0)]
        f = _pt_frame(coords, elev=[100, 50, 10])
        result = f.flow_direction("elev")
        records = list(result)
        assert records[0]["flow_to_flow"] == 1  # flows from high to medium
        assert records[1]["flow_to_flow"] == 2  # flows from medium to low
        assert records[2]["is_sink_flow"] is True  # lowest point is sink

    def test_sink(self):
        coords = [(0, 0), (1, 0), (2, 0)]
        f = _pt_frame(coords, elev=[50, 10, 50])
        result = f.flow_direction("elev")
        records = list(result)
        assert records[1]["is_sink_flow"] is True


# Tool 95: flow_accumulation
class TestFlowAccumulation:
    def test_linear_slope(self):
        coords = [(0, 0), (1, 0), (2, 0), (3, 0)]
        f = _pt_frame(coords, elev=[40, 30, 20, 10])
        result = f.flow_accumulation("elev")
        records = list(result)
        # Point at bottom should have highest accumulation
        assert records[3]["accumulation_accum"] > records[0]["accumulation_accum"]

    def test_is_channel(self):
        coords = [(i, 0) for i in range(20)]
        f = _pt_frame(coords, elev=[20 - i for i in range(20)])
        result = f.flow_accumulation("elev")
        records = list(result)
        # At least the bottom should be flagged as channel
        assert records[-1]["is_channel_accum"] is True


# Tool 96: mark_correlation_function
class TestMarkCorrelation:
    def test_basic(self):
        coords = [(0, 0), (1, 0), (2, 0), (3, 0)]
        f = _pt_frame(coords, val=[10, 10, 10, 10])
        result = f.mark_correlation_function("val")
        assert len(result) > 0
        for r in result:
            assert "distance" in r
            assert "mark_correlation" in r

    def test_empty(self):
        result = GeoPromptFrame.from_records([{"site_id": "a", "geometry": {"type": "Point", "coordinates": (0, 0)}, "val": 1}]).mark_correlation_function("val")
        assert result == []


# Tool 97: point_pattern_intensity
class TestPointPatternIntensity:
    def test_basic(self):
        coords = [(0.5, 0.5)]
        f = _pt_frame(coords)
        result = f.point_pattern_intensity(grid_resolution=3)
        assert len(result) > 0
        records = list(result)
        for r in records:
            assert "intensity_intensity" in r
            assert "global_intensity_intensity" in r

    def test_empty(self):
        result = GeoPromptFrame.from_records([]).point_pattern_intensity()
        assert len(result) == 0


# Tool 98: location_allocation
class TestLocationAllocation:
    def test_basic(self):
        coords = [(0, 0), (1, 0), (5, 0), (6, 0), (10, 0), (11, 0)]
        f = _pt_frame(coords)
        result = f.location_allocation(p=2, seed=42)
        assert len(result) == 6
        records = list(result)
        facilities = [r for r in records if r["facility_pmedian"]]
        assert len(facilities) == 2
        for r in records:
            assert "assigned_to_pmedian" in r
            assert "distance_to_facility_pmedian" in r

    def test_single(self):
        coords = [(0, 0)]
        f = _pt_frame(coords)
        result = f.location_allocation(p=1, seed=1)
        assert len(result) == 1


# Tool 99: spatial_durbin_model
class TestSpatialDurbinModel:
    def test_basic(self):
        coords = [(i, 0) for i in range(6)]
        f = _pt_frame(coords, val=[i * 2.0 for i in range(6)], val2=[float(i) for i in range(6)])
        result = f.spatial_durbin_model("val", ["val2"])
        assert len(result) == 6
        for row in result:
            assert "predicted_sdm" in row
            assert "residual_sdm" in row
            assert "spatial_lag_y_sdm" in row

    def test_empty(self):
        f = GeoPromptFrame.from_records([{"site_id": "a", "geometry": {"type": "Point", "coordinates": (0, 0)}, "val": 1, "val2": 1}])
        result = f.spatial_durbin_model("val", ["val2"])
        assert len(result) == 1


# Tool 100: kriging_cross_validation
class TestKrigingCrossValidation:
    def test_basic(self):
        coords = [(0, 0), (1, 0), (0, 1), (1, 1), (0.5, 0.5)]
        f = _pt_frame(coords, val=[1, 2, 3, 4, 2.5])
        result = f.kriging_cross_validation("val")
        assert "rmse" in result
        assert "mae" in result
        assert result["rmse"] >= 0
        assert result["mae"] >= 0
        assert result["n"] == 5

    def test_small_frame(self):
        coords = [(0, 0)]
        f = _pt_frame(coords, val=[10])
        result = f.kriging_cross_validation("val")
        assert result["n"] == 1
