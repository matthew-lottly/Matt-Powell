"""Tests for tools 313-334."""

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


def _line_frame():
    rows = [
        {"geometry": {"type": "LineString", "coordinates": ((0, 0), (1, 0))}, "v": 1},
        {"geometry": {"type": "LineString", "coordinates": ((1, 0), (2, 0))}, "v": 2},
        {"geometry": {"type": "LineString", "coordinates": ((3, 0), (4, 0))}, "v": 3},
    ]
    return GeoPromptFrame.from_records(rows)


def _network_frame():
    rows = [
        {"geometry": {"type": "Point", "coordinates": (0, 0)}, "from_node": 0, "to_node": 1, "cost": 1.0, "origin": 0, "dest": 2},
        {"geometry": {"type": "Point", "coordinates": (1, 0)}, "from_node": 1, "to_node": 2, "cost": 2.0, "origin": 0, "dest": 2},
        {"geometry": {"type": "Point", "coordinates": (2, 0)}, "from_node": 0, "to_node": 2, "cost": 5.0, "origin": 0, "dest": 2},
    ]
    return GeoPromptFrame.from_records(rows)


# ------------------------------------------------------------------
# Tool 313: local_cluster_persistence
# ------------------------------------------------------------------
def test_local_cluster_persistence():
    gf = _grid_frame()
    result = gf.local_cluster_persistence("value", "time")
    rec = result.to_records()[0]
    assert "hot_lcp" in rec
    assert "persistence_lcp" in rec
    assert len(result) == 16


# ------------------------------------------------------------------
# Tool 314: time_slice_comparison
# ------------------------------------------------------------------
def test_time_slice_comparison():
    gf = _grid_frame()
    result = gf.time_slice_comparison("value", "time")
    rec = result.to_records()[0]
    assert "mean_tsc" in rec
    assert "std_tsc" in rec
    assert len(result) == 4  # 4 unique time values


# ------------------------------------------------------------------
# Tool 315: event_density_trend
# ------------------------------------------------------------------
def test_event_density_trend():
    gf = _grid_frame()
    result = gf.event_density_trend("time", grid_resolution=3)
    rec = result.to_records()[0]
    assert "density_edt" in rec
    assert "time_edt" in rec


# ------------------------------------------------------------------
# Tool 316: event_anisotropy
# ------------------------------------------------------------------
def test_event_anisotropy():
    gf = _grid_frame()
    result = gf.event_anisotropy(n_directions=4)
    assert len(result) == 4
    rec = result.to_records()[0]
    assert "angle_deg_eanis" in rec
    assert "ratio_eanis" in rec


# ------------------------------------------------------------------
# Tool 317: medial_axis_refine
# ------------------------------------------------------------------
def test_medial_axis_refine():
    gf = _polygon_frame()
    result = gf.medial_axis_refine(n_samples=5)
    rec = result.to_records()[0]
    assert "radius_mar" in rec


# ------------------------------------------------------------------
# Tool 318: mesh_quality
# ------------------------------------------------------------------
def test_mesh_quality():
    gf = _polygon_frame()
    result = gf.mesh_quality()
    rec = result.to_records()[0]
    assert "quality_mqual" in rec
    assert "min_angle_mqual" in rec
    assert rec["quality_mqual"] > 0


# ------------------------------------------------------------------
# Tool 319: boundary_generalize
# ------------------------------------------------------------------
def test_boundary_generalize():
    # Polygon with extra vertex
    rows = [{"geometry": {"type": "Polygon", "coordinates": ((0, 0), (1, 0.001), (2, 0), (2, 2), (0, 2))}}]
    gf = GeoPromptFrame.from_records(rows)
    result = gf.boundary_generalize(tolerance=0.1)
    rec = result.to_records()[0]
    assert "n_removed_bgen" in rec


# ------------------------------------------------------------------
# Tool 320: topology_normalize
# ------------------------------------------------------------------
def test_topology_normalize():
    gf = _polygon_frame()
    result = gf.topology_normalize()
    rec = result.to_records()[0]
    assert "normalized_tnrm" in rec
    assert rec["normalized_tnrm"] == 1


# ------------------------------------------------------------------
# Tool 321: feather_export
# ------------------------------------------------------------------
def test_feather_export():
    gf = _grid_frame(4)
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        result = gf.feather_export(path)
        assert os.path.isfile(path)
        assert os.path.getsize(path) > 0
        assert len(result) == 4
    finally:
        os.unlink(path)


# ------------------------------------------------------------------
# Tool 322: schema_report
# ------------------------------------------------------------------
def test_schema_report():
    gf = _grid_frame()
    result = gf.schema_report()
    rec = result.to_records()[0]
    assert "n_rows_srpt" in rec
    assert rec["n_rows_srpt"] == 16
    assert "columns_srpt" in rec


# ------------------------------------------------------------------
# Tool 323: format_autodetect
# ------------------------------------------------------------------
def test_format_autodetect():
    gf = _grid_frame(4)
    result = gf.format_autodetect("data.geojson")
    rec = result.to_records()[0]
    assert rec["format_fdet"] == "geojson"


def test_format_autodetect_shp():
    gf = _grid_frame(4)
    result = gf.format_autodetect("data.shp")
    rec = result.to_records()[0]
    assert rec["format_fdet"] == "shapefile"


# ------------------------------------------------------------------
# Tool 324: export_validation
# ------------------------------------------------------------------
def test_export_validation():
    gf = _grid_frame(4)
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
        f.write('{"test": 1}')
        path = f.name
    try:
        result = gf.export_validation(path)
        rec = result.to_records()[0]
        assert rec["exists_eval"] == 1
        assert rec["valid_json_eval"] == 1
    finally:
        os.unlink(path)


# ------------------------------------------------------------------
# Tool 325: grid_provenance
# ------------------------------------------------------------------
def test_grid_provenance():
    gf = _grid_frame()
    result = gf.grid_provenance("value", grid_resolution=3)
    assert len(result) == 9
    rec = result.to_records()[0]
    assert "sources_gprov" in rec
    assert "weights_gprov" in rec


# ------------------------------------------------------------------
# Tool 326: flow_direction_diagnostics
# ------------------------------------------------------------------
def test_flow_direction_diagnostics():
    gf = _grid_frame()
    result = gf.flow_direction_diagnostics("elevation")
    rec = result.to_records()[0]
    assert "flat_count_fdd" in rec
    assert "steepest_slope_fdd" in rec


# ------------------------------------------------------------------
# Tool 327: route_failure_diagnostics
# ------------------------------------------------------------------
def test_route_failure_diagnostics():
    gf = _network_frame()
    result = gf.route_failure_diagnostics("from_node", "to_node", "cost", source=0, target=2)
    rec = result.to_records()[0]
    assert rec["path_exists_rfd"] == 1
    assert rec["n_components_rfd"] >= 1


# ------------------------------------------------------------------
# Tool 328: tps_stability
# ------------------------------------------------------------------
def test_tps_stability():
    gf = _grid_frame()
    result = gf.tps_stability("value")
    rec = result.to_records()[0]
    assert "condition_tpss" in rec
    assert "ill_conditioned_tpss" in rec


# ------------------------------------------------------------------
# Tool 329: kriging_uncertainty
# ------------------------------------------------------------------
def test_kriging_uncertainty():
    gf = _grid_frame()
    result = gf.kriging_uncertainty("value", grid_resolution=3)
    assert len(result) == 9
    rec = result.to_records()[0]
    assert "variance_kunc" in rec
    assert "pi_width_kunc" in rec


# ------------------------------------------------------------------
# Tool 330: contour_stitch
# ------------------------------------------------------------------
def test_contour_stitch():
    gf = _grid_frame()
    result = gf.contour_stitch("value", n_levels=3)
    assert len(result) >= 1
    rec = result.to_records()[0]
    assert "level_cstch" in rec


# ------------------------------------------------------------------
# Tool 331: polygon_repair_strategy
# ------------------------------------------------------------------
def test_polygon_repair_strategy_buffer_zero():
    gf = _polygon_frame()
    result = gf.polygon_repair_strategy(strategy="buffer_zero")
    rec = result.to_records()[0]
    assert "repaired_prst" in rec
    assert "strategy_prst" in rec


def test_polygon_repair_strategy_remove_spikes():
    gf = _polygon_frame()
    result = gf.polygon_repair_strategy(strategy="remove_spikes")
    assert len(result) == 2


# ------------------------------------------------------------------
# Tool 332: topology_audit_extended
# ------------------------------------------------------------------
def test_topology_audit_extended():
    gf = _polygon_frame()
    result = gf.topology_audit_extended()
    rec = result.to_records()[0]
    assert "overlap_tae" in rec
    assert "self_intersects_tae" in rec


# ------------------------------------------------------------------
# Tool 333: line_merge_graph
# ------------------------------------------------------------------
def test_line_merge_graph():
    gf = _line_frame()
    result = gf.line_merge_graph()
    # Should merge first two lines, third is separate
    assert len(result) == 2
    rec = result.to_records()[0]
    assert "chain_id_lmg" in rec
    assert "length_lmg" in rec


# ------------------------------------------------------------------
# Tool 334: od_matrix_extended
# ------------------------------------------------------------------
def test_od_matrix_extended():
    gf = _network_frame()
    result = gf.od_matrix_extended("origin", "dest", "from_node", "to_node", "cost")
    rec = result.to_records()[0]
    assert "cost_ode" in rec
    assert "reachable_ode" in rec
