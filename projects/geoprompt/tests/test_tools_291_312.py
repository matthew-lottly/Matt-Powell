"""Tests for tools 291-312."""

import math
import pytest

from geoprompt import GeoPromptFrame


def _col(gf, name):
    return [r[name] for r in gf.to_records()]


def _grid_frame(n=16):
    side = int(math.sqrt(n))
    rows = []
    for i in range(n):
        x, y = float(i % side), float(i // side)
        rows.append({"geometry": {"type": "Point", "coordinates": (x, y)},
                      "value": float(i), "secondary": float(n - i),
                      "category": "A" if i % 2 == 0 else "B",
                      "time": float(i % 4)})
    return GeoPromptFrame.from_records(rows)


def _network_frame():
    rows = [
        {"geometry": {"type": "Point", "coordinates": (0, 0)}, "from_node": 0, "to_node": 1, "cost": 1.0, "dep": 0, "arr": 1},
        {"geometry": {"type": "Point", "coordinates": (1, 0)}, "from_node": 1, "to_node": 2, "cost": 2.0, "dep": 1, "arr": 3},
        {"geometry": {"type": "Point", "coordinates": (2, 0)}, "from_node": 0, "to_node": 2, "cost": 5.0, "dep": 0, "arr": 5},
    ]
    return GeoPromptFrame.from_records(rows)


# ------------------------------------------------------------------
# Tool 291: cokriging_cross_variogram
# ------------------------------------------------------------------
def test_cokriging_cross_variogram():
    gf = _grid_frame()
    result = gf.cokriging_cross_variogram("value", "secondary", grid_resolution=4)
    assert len(result) == 16  # 4x4 grid
    rec = result.to_records()[0]
    assert "predicted_ccv" in rec
    assert "cross_sill_ccv" in rec


# ------------------------------------------------------------------
# Tool 292: breakline_interpolation
# ------------------------------------------------------------------
def test_breakline_interpolation():
    gf = _grid_frame()
    bl_rows = [{"geometry": {"type": "LineString", "coordinates": ((1.5, 0), (1.5, 4))}}]
    bl = GeoPromptFrame.from_records(bl_rows)
    result = gf.breakline_interpolation("value", bl, grid_resolution=3)
    assert len(result) == 9
    assert "value_bli" in result.to_records()[0]


# ------------------------------------------------------------------
# Tool 293: surface_resample
# ------------------------------------------------------------------
def test_surface_resample_nearest():
    gf = _grid_frame()
    result = gf.surface_resample("value", target_resolution=3, method="nearest")
    assert len(result) == 9
    assert "value_sres" in result.to_records()[0]


def test_surface_resample_bilinear():
    gf = _grid_frame()
    result = gf.surface_resample("value", target_resolution=3, method="bilinear")
    assert len(result) == 9


# ------------------------------------------------------------------
# Tool 294: surface_comparison
# ------------------------------------------------------------------
def test_surface_comparison():
    rows = [{"geometry": {"type": "Point", "coordinates": (i, 0)},
             "s1": float(i), "s2": float(i * 2), "s3": float(i + 1)} for i in range(5)]
    gf = GeoPromptFrame.from_records(rows)
    result = gf.surface_comparison(["s1", "s2", "s3"])
    rec = result.to_records()[0]
    assert "mean_scmp" in rec
    assert "range_scmp" in rec
    assert "std_scmp" in rec
    assert len(result) == 5


# ------------------------------------------------------------------
# Tool 295: drift_diagnostics
# ------------------------------------------------------------------
def test_drift_diagnostics():
    gf = _grid_frame()
    result = gf.drift_diagnostics("value")
    rec = result.to_records()[0]
    assert "resid_order1_drft" in rec
    assert "r2_order1_drft" in rec
    assert "r2_order2_drft" in rec
    assert len(result) == 16


# ------------------------------------------------------------------
# Tool 296: interpolator_recommendation
# ------------------------------------------------------------------
def test_interpolator_recommendation():
    gf = _grid_frame()
    result = gf.interpolator_recommendation("value")
    rec = result.to_records()[0]
    assert "recommended_irec" in rec
    assert "reason_irec" in rec
    assert rec["recommended_irec"] in ("idw", "rbf", "kriging", "natural_neighbor")


# ------------------------------------------------------------------
# Tool 297: redcap_regionalization
# ------------------------------------------------------------------
def test_redcap_regionalization():
    gf = _grid_frame()
    result = gf.redcap_regionalization("value", n_regions=3)
    labels = _col(result, "region_rcap")
    assert len(set(labels)) <= 3
    assert len(labels) == 16


# ------------------------------------------------------------------
# Tool 298: region_compactness_diagnostics
# ------------------------------------------------------------------
def test_region_compactness_diagnostics():
    rows = [{"geometry": {"type": "Point", "coordinates": (float(i), 0.0)},
             "region": i // 3} for i in range(9)]
    gf = GeoPromptFrame.from_records(rows)
    result = gf.region_compactness_diagnostics("region")
    rec = result.to_records()[0]
    assert "ipq_rcpd" in rec
    assert "elongation_rcpd" in rec


# ------------------------------------------------------------------
# Tool 299: panel_spatial_regression
# ------------------------------------------------------------------
def test_panel_spatial_regression():
    rows = [
        {"geometry": {"type": "Point", "coordinates": (float(i % 4), float(i // 4))},
         "y": float(i) + 1.0, "x1": float(i) * 0.5, "time": i % 3, "entity": i // 3}
        for i in range(12)
    ]
    gf = GeoPromptFrame.from_records(rows)
    result = gf.panel_spatial_regression("y", ["x1"], "time", "entity")
    rec = result.to_records()[0]
    assert "predicted_psr" in rec
    assert "residual_psr" in rec
    assert "n_periods_psr" in rec


# ------------------------------------------------------------------
# Tool 300: local_leverage
# ------------------------------------------------------------------
def test_local_leverage():
    gf = _grid_frame()
    result = gf.local_leverage("value", ["secondary"])
    rec = result.to_records()[0]
    assert "leverage_llev" in rec
    assert "high_leverage_llev" in rec
    # leverage should be non-negative
    assert all(v >= -0.001 for v in _col(result, "leverage_llev"))


# ------------------------------------------------------------------
# Tool 301: model_family_comparison
# ------------------------------------------------------------------
def test_model_family_comparison():
    gf = _grid_frame()
    result = gf.model_family_comparison("value", ["secondary"])
    rec = result.to_records()[0]
    assert "best_model_mfc" in rec
    assert rec["best_model_mfc"] in ("ols", "spatial_lag", "trend")
    assert "ols_r2_mfc" in rec


# ------------------------------------------------------------------
# Tool 302: bandwidth_recommendation
# ------------------------------------------------------------------
def test_bandwidth_recommendation():
    gf = _grid_frame()
    result = gf.bandwidth_recommendation("value")
    rec = result.to_records()[0]
    assert "bandwidth_bwr" in rec
    assert rec["bandwidth_bwr"] > 0


# ------------------------------------------------------------------
# Tool 303: roughness_segmentation
# ------------------------------------------------------------------
def test_roughness_segmentation():
    gf = _grid_frame()
    result = gf.roughness_segmentation("value", n_classes=3)
    classes = _col(result, "class_rseg")
    assert all(0 <= c <= 2 for c in classes)
    assert "roughness_rseg" in result.to_records()[0]


# ------------------------------------------------------------------
# Tool 304: pickup_delivery_routing
# ------------------------------------------------------------------
def test_pickup_delivery_routing():
    rows = [
        {"geometry": {"type": "Point", "coordinates": (float(i), 0.0)},
         "pickup": i + 1 if i < 3 else 0,
         "delivery": i - 2 if i >= 3 else 0}
        for i in range(6)
    ]
    gf = GeoPromptFrame.from_records(rows)
    result = gf.pickup_delivery_routing("pickup", "delivery")
    rec = result.to_records()[0]
    assert "order_pdr" in rec
    assert "total_dist_pdr" in rec


# ------------------------------------------------------------------
# Tool 305: transit_routing
# ------------------------------------------------------------------
def test_transit_routing():
    gf = _network_frame()
    result = gf.transit_routing("from_node", "to_node", "cost", "dep", "arr")
    rec = result.to_records()[0]
    assert "arrival_cost_trt" in rec
    assert "reachable_trt" in rec


# ------------------------------------------------------------------
# Tool 306: nn_contingency
# ------------------------------------------------------------------
def test_nn_contingency():
    gf = _grid_frame()
    result = gf.nn_contingency("category")
    rec = result.to_records()[0]
    assert "from_cat_nnc" in rec
    assert "to_cat_nnc" in rec
    assert "count_nnc" in rec
    assert len(result) >= 4  # at least 2x2 contingency


# ------------------------------------------------------------------
# Tool 307: pairwise_directionality
# ------------------------------------------------------------------
def test_pairwise_directionality():
    gf = _grid_frame()
    result = gf.pairwise_directionality("value", n_sectors=4)
    assert len(result) == 4
    rec = result.to_records()[0]
    assert "angle_deg_pdir" in rec
    assert "mean_diff_pdir" in rec


# ------------------------------------------------------------------
# Tool 308: inhomogeneous_pair_correlation
# ------------------------------------------------------------------
def test_inhomogeneous_pair_correlation():
    gf = _grid_frame()
    result = gf.inhomogeneous_pair_correlation(n_bins=5)
    assert len(result) == 5
    rec = result.to_records()[0]
    assert "g_ipcf" in rec
    assert "distance_ipcf" in rec


# ------------------------------------------------------------------
# Tool 309: covariate_intensity
# ------------------------------------------------------------------
def test_covariate_intensity():
    gf = _grid_frame()
    result = gf.covariate_intensity("value")
    vals = _col(result, "intensity_cint")
    assert len(vals) == 16
    assert all(isinstance(v, float) for v in vals)


# ------------------------------------------------------------------
# Tool 310: hotspot_duration
# ------------------------------------------------------------------
def test_hotspot_duration():
    rows = [
        {"geometry": {"type": "Point", "coordinates": (0.0, 0.0)},
         "value": float(10 if t < 3 else 1), "time": float(t)}
        for t in range(5)
    ]
    gf = GeoPromptFrame.from_records(rows)
    result = gf.hotspot_duration("value", "time")
    rec = result.to_records()[0]
    assert "streak_hdur" in rec
    assert "is_hot_hdur" in rec


# ------------------------------------------------------------------
# Tool 311: point_process_simulation
# ------------------------------------------------------------------
def test_point_process_simulation_poisson():
    gf = _grid_frame()
    result = gf.point_process_simulation(n_points=20, pattern="poisson")
    assert len(result) == 20
    assert _col(result, "pattern_pps")[0] == "poisson"


def test_point_process_simulation_clustered():
    gf = _grid_frame()
    result = gf.point_process_simulation(n_points=20, pattern="clustered")
    assert len(result) == 20


def test_point_process_simulation_regular():
    gf = _grid_frame()
    result = gf.point_process_simulation(n_points=20, pattern="regular")
    assert len(result) >= 20  # may produce side*side >= n_points


# ------------------------------------------------------------------
# Tool 312: multitype_interaction
# ------------------------------------------------------------------
def test_multitype_interaction():
    gf = _grid_frame()
    result = gf.multitype_interaction("category", n_bins=3)
    rec = result.to_records()[0]
    assert "type_a_mti" in rec
    assert "k_obs_mti" in rec
    assert "interaction_mti" in rec
