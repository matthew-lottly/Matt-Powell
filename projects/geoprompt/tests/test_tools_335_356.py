"""Tests for tools 335-356."""

import math
import os
import tempfile
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
                      "time": float(i % 4),
                      "elevation": float(10 + i)})
    return GeoPromptFrame.from_records(rows)


def _polygon_frame():
    rows = [
        {"geometry": {"type": "Polygon", "coordinates": ((0, 0), (2, 0), (2, 2), (0, 2))}, "value": 1},
        {"geometry": {"type": "Polygon", "coordinates": ((3, 0), (5, 0), (5, 2), (3, 2))}, "value": 2},
    ]
    return GeoPromptFrame.from_records(rows)


def _network_frame():
    rows = [
        {"geometry": {"type": "Point", "coordinates": (0, 0)}, "from_node": 0, "to_node": 1, "cost": 2.0, "capacity": 5.0},
        {"geometry": {"type": "Point", "coordinates": (1, 0)}, "from_node": 1, "to_node": 2, "cost": 3.0, "capacity": 3.0},
        {"geometry": {"type": "Point", "coordinates": (2, 0)}, "from_node": 0, "to_node": 2, "cost": 10.0, "capacity": 4.0},
    ]
    return GeoPromptFrame.from_records(rows)


# Tool 335: tps_smoothing_select
def test_tps_smoothing_select():
    gf = _grid_frame()
    result = gf.tps_smoothing_select("value")
    assert len(result) >= 2
    rec = result.to_records()[0]
    assert "lambda_tpsel" in rec
    assert "cv_mse_tpsel" in rec
    # Exactly one should be selected
    assert sum(_col(result, "selected_tpsel")) == 1


# Tool 336: nn_fallback_quality
def test_nn_fallback_quality():
    gf = _grid_frame()
    result = gf.nn_fallback_quality("value")
    rec = result.to_records()[0]
    assert "rmse_nnfq" in rec
    assert "quality_nnfq" in rec
    assert rec["rmse_nnfq"] >= 0


# Tool 337: regression_kriging_diagnostics
def test_regression_kriging_diagnostics():
    gf = _grid_frame()
    result = gf.regression_kriging_diagnostics("value", "secondary")
    rec = result.to_records()[0]
    assert "r2_rkd" in rec
    assert "residual_moran_rkd" in rec
    assert 0 <= rec["r2_rkd"] <= 1.0


# Tool 338: indicator_kriging_diagnostics
def test_indicator_kriging_diagnostics():
    gf = _grid_frame()
    result = gf.indicator_kriging_diagnostics("value")
    assert len(result) >= 2  # Multiple thresholds
    rec = result.to_records()[0]
    assert "threshold_ikd" in rec
    assert "prob_exceed_ikd" in rec


# Tool 339: terrain_tiebreak
def test_terrain_tiebreak():
    gf = _grid_frame()
    result = gf.terrain_tiebreak("elevation")
    assert len(result) == 16
    rec = result.to_records()[0]
    assert "n_downhill_ttb" in rec
    assert "tied_ttb" in rec


# Tool 340: min_cut_residual
def test_min_cut_residual():
    gf = _network_frame()
    result = gf.min_cut_residual("from_node", "to_node", "capacity", source=0, sink=2)
    rec = result.to_records()[0]
    assert "max_flow_mcr" in rec
    assert rec["max_flow_mcr"] > 0


# Tool 341: centrality_directed
def test_centrality_directed():
    gf = _network_frame()
    result = gf.centrality_directed("from_node", "to_node")
    assert len(result) == 3  # 3 unique nodes
    rec = result.to_records()[0]
    assert "in_degree_cdir" in rec
    assert "out_degree_cdir" in rec
    assert "betweenness_cdir" in rec


# Tool 342: kmz_export
def test_kmz_export():
    gf = _grid_frame(4)
    with tempfile.NamedTemporaryFile(suffix=".kml", delete=False) as f:
        path = f.name
    try:
        result = gf.kmz_export(path)
        assert os.path.isfile(path)
        assert os.path.getsize(path) > 0
        rec = result.to_records()[0]
        assert rec["n_features_kmz"] == 4
    finally:
        os.unlink(path)


# Tool 343: metadata_roundtrip
def test_metadata_roundtrip():
    gf = _grid_frame()
    result = gf.metadata_roundtrip()
    rec = result.to_records()[0]
    assert rec["roundtrip_ok_mrt"] == 1
    assert rec["rows_match_mrt"] == 1
    assert rec["geom_match_mrt"] == 1


# Tool 344: dependency_report
def test_dependency_report():
    gf = _grid_frame(4)
    result = gf.dependency_report()
    assert len(result) == 10  # 10 modules checked
    rec = result.to_records()[0]
    assert "module_drpt" in rec
    assert "available_drpt" in rec


# Tool 345: encoding_diagnostics
def test_encoding_diagnostics():
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w", encoding="utf-8") as f:
        f.write("Hello world\n")
        path = f.name
    try:
        gf = _grid_frame(4)
        result = gf.encoding_diagnostics(path)
        rec = result.to_records()[0]
        assert rec["exists_ediag"] == 1
        assert rec["encoding_ediag"] == "utf-8"
    finally:
        os.unlink(path)


def test_encoding_diagnostics_missing():
    gf = _grid_frame(4)
    result = gf.encoding_diagnostics("/nonexistent/file.txt")
    rec = result.to_records()[0]
    assert rec["exists_ediag"] == 0


# Tool 346: path_normalize
def test_path_normalize():
    rows = [
        {"geometry": {"type": "Point", "coordinates": (0, 0)}, "path": "C:\\Users\\test\\data.shp"},
        {"geometry": {"type": "Point", "coordinates": (1, 0)}, "path": "/home/user/data.geojson"},
    ]
    gf = GeoPromptFrame.from_records(rows)
    result = gf.path_normalize("path")
    recs = result.to_records()
    assert "normalized_pnrm" in recs[0]
    assert "extension_pnrm" in recs[0]
    assert recs[0]["extension_pnrm"] == ".shp"
    assert recs[1]["extension_pnrm"] == ".geojson"


# Tool 347: config_defaults
def test_config_defaults():
    gf = _grid_frame()
    result = gf.config_defaults()
    rec = result.to_records()[0]
    assert rec["n_rows_cfg"] == 16
    assert "geometry_column_cfg" in rec


# Tool 348: diagnostics_unified
def test_diagnostics_unified():
    gf = _grid_frame()
    result = gf.diagnostics_unified("value")
    rec = result.to_records()[0]
    assert "mean_diag" in rec
    assert "moran_i_diag" in rec
    assert "skewness_diag" in rec
    assert rec["n_diag"] == 16


# Tool 349: provenance_track
def test_provenance_track():
    gf = _grid_frame()
    result = gf.provenance_track("test_operation", input_columns=["value"])
    assert len(result) == 16
    rec = result.to_records()[0]
    assert rec["operation_prov"] == "test_operation"
    assert "timestamp_prov" in rec


# Tool 350: moran_review_diagnostics
def test_moran_review_diagnostics():
    gf = _grid_frame()
    result = gf.moran_review_diagnostics("value", k=3)
    rec = result.to_records()[0]
    assert "moran_i_binary_mrev" in rec
    assert "moran_i_row_std_mrev" in rec
    assert rec["k_mrev"] == 3


# Tool 351: geary_review_diagnostics
def test_geary_review_diagnostics():
    gf = _grid_frame()
    result = gf.geary_review_diagnostics("value", k=3)
    rec = result.to_records()[0]
    assert "geary_c_grev" in rec
    assert rec["expected_c_grev"] == 1.0


# Tool 352: getis_review_diagnostics
def test_getis_review_diagnostics():
    gf = _grid_frame()
    result = gf.getis_review_diagnostics("value")
    assert len(result) == 16
    rec = result.to_records()[0]
    assert "gi_star_girev" in rec
    assert "hot_girev" in rec


# Tool 353: variogram_review_diagnostics
def test_variogram_review_diagnostics():
    gf = _grid_frame()
    result = gf.variogram_review_diagnostics("value", n_lags=5)
    assert len(result) >= 1
    rec = result.to_records()[0]
    assert "lag_vrev" in rec
    assert "gamma_vrev" in rec
    assert "monotonic_vrev" in rec


# Tool 354: ols_review_diagnostics
def test_ols_review_diagnostics():
    gf = _grid_frame()
    result = gf.ols_review_diagnostics("value", "secondary")
    rec = result.to_records()[0]
    assert "r2_orev" in rec
    assert "durbin_watson_orev" in rec
    assert "aic_orev" in rec
    assert 0 <= rec["r2_orev"] <= 1.0


# Tool 355: kriging_review_diagnostics
def test_kriging_review_diagnostics():
    gf = _grid_frame()
    result = gf.kriging_review_diagnostics("value")
    rec = result.to_records()[0]
    assert "cv_rmse_krev" in rec
    assert "quality_krev" in rec


# Tool 356: terrain_review_diagnostics
def test_terrain_review_diagnostics():
    gf = _grid_frame()
    result = gf.terrain_review_diagnostics("elevation")
    rec = result.to_records()[0]
    assert "slope_min_trev" in rec
    assert "slope_sign_ok_trev" in rec
    assert rec["slope_negative_count_trev"] == 0
