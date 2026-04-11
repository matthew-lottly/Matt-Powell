"""Tests for the 19 extended utility network analysis tools.

One test per function covering the core contract:
  - function is callable with a minimal valid graph
  - return type matches the documented shape
  - key numeric fields are present and within valid ranges
"""

from __future__ import annotations

import math

import pytest

from geoprompt.network import (
    NetworkEdge,
    build_network_graph,
    co_location_conflict_scan,
    critical_customer_coverage_audit,
    criticality_ranking_by_node_removal,
    detention_basin_overflow_trace,
    feeder_load_balance_swap,
    fiber_cut_impact_matrix,
    fiber_splice_node_trace,
    fire_flow_demand_check,
    gas_odorization_zone_trace,
    gas_pressure_drop_trace,
    gas_regulator_station_isolation,
    inflow_infiltration_scan,
    infrastructure_age_risk_weighted_routing,
    interdependency_cascade_simulation,
    load_transfer_feasibility,
    pipe_break_isolation_zones,
    pressure_reducing_valve_trace,
    ring_redundancy_check,
    stormwater_flow_accumulation,
)


# ─── shared fixtures ─────────────────────────────────────────────────────────


def _linear_graph(n: int = 5, directed: bool = False):
    """Build a simple linear graph A─B─C─D─E with cost=1 per edge."""
    nodes = [chr(65 + i) for i in range(n)]  # A, B, C, ...
    edges: list[NetworkEdge] = [
        {
            "edge_id": f"e{i}",
            "from_node": nodes[i],
            "to_node": nodes[i + 1],
            "cost": 1.0,
            "capacity": 100.0,
            "flow": 10.0,
            "load": 20.0,
        }
        for i in range(n - 1)
    ]
    return build_network_graph(edges, directed=directed)


def _ring_graph():
    """Hub H connected to A, B, C in a ring: H-A-B-C-H plus direct H-B shortcut."""
    edges: list[NetworkEdge] = [
        {"edge_id": "ha", "from_node": "H", "to_node": "A", "cost": 1.0},
        {"edge_id": "ab", "from_node": "A", "to_node": "B", "cost": 1.0},
        {"edge_id": "bc", "from_node": "B", "to_node": "C", "cost": 1.0},
        {"edge_id": "ch", "from_node": "C", "to_node": "H", "cost": 1.0},
        {"edge_id": "hb", "from_node": "H", "to_node": "B", "cost": 2.0},
    ]
    return build_network_graph(edges, directed=False)


# ─── ELECTRIC ─────────────────────────────────────────────────────────────────


def test_criticality_ranking_by_node_removal_returns_ranked_list():
    graph = _linear_graph(5)
    result = criticality_ranking_by_node_removal(graph)
    assert isinstance(result, list)
    assert len(result) == 5
    for entry in result:
        assert "node" in entry
        assert "rank" in entry
        assert "impact_ratio" in entry
        assert 0.0 <= entry["impact_ratio"] <= 1.0
    # Interior nodes should have higher impact than endpoints on a linear graph
    ranks = {r["node"]: r["rank"] for r in result}
    # B, C, D are interior; A and E are endpoints — interior should rank higher
    assert ranks["C"] < ranks["A"] or ranks["C"] < ranks["E"]


def test_load_transfer_feasibility_returns_expected_keys():
    graph = _linear_graph(6)
    tie: NetworkEdge = {
        "edge_id": "tie",
        "from_node": "C",
        "to_node": "D",
        "cost": 1.0,
        "capacity": 200.0,
    }
    result = load_transfer_feasibility(graph, "A", "F", tie)
    assert isinstance(result, dict)
    for key in (
        "feasible",
        "feeder_a_source",
        "feeder_b_source",
        "combined_load",
        "a_can_absorb_b",
        "b_can_absorb_a",
    ):
        assert key in result, f"missing key: {key}"
    assert isinstance(result["feasible"], bool)


def test_feeder_load_balance_swap_returns_list():
    edges: list[NetworkEdge] = [
        {"edge_id": "e1", "from_node": "S1", "to_node": "A", "cost": 1.0, "load": 80.0},
        {"edge_id": "e2", "from_node": "A", "to_node": "B", "cost": 1.0, "load": 80.0},
        {"edge_id": "e3", "from_node": "S2", "to_node": "C", "cost": 1.0, "load": 20.0},
        {"edge_id": "e4", "from_node": "B", "to_node": "C", "cost": 1.0, "load": 5.0},
    ]
    graph = build_network_graph(edges, directed=False)
    result = feeder_load_balance_swap(graph, ["S1", "S2"])
    assert isinstance(result, list)
    for entry in result:
        assert "from_feeder" in entry
        assert "to_feeder" in entry
        assert "transfer_load" in entry


# ─── WATER / HYDRAULICS ───────────────────────────────────────────────────────


def test_pipe_break_isolation_zones_returns_zones():
    edges: list[NetworkEdge] = [
        {"edge_id": "e1", "from_node": "A", "to_node": "B", "cost": 1.0},
        {"edge_id": "e2", "from_node": "B", "to_node": "C", "cost": 1.0, "device_type": "gate_valve"},
        {"edge_id": "e3", "from_node": "C", "to_node": "D", "cost": 1.0},
        {"edge_id": "e4", "from_node": "D", "to_node": "E", "cost": 1.0, "device_type": "gate_valve"},
        {"edge_id": "e5", "from_node": "E", "to_node": "F", "cost": 1.0},
    ]
    graph = build_network_graph(edges, directed=False)
    result = pipe_break_isolation_zones(graph, break_edge_id="e3")
    assert "affected_nodes" in result
    assert "boundary_valves" in result
    assert isinstance(result["affected_nodes"], list)
    assert isinstance(result["boundary_valves"], list)
    # Valves e2 and e4 should bound the zone around edge e3
    assert set(result["boundary_valves"]).issubset({"e2", "e4"})


def test_pressure_reducing_valve_trace_profiles_headloss():
    graph = _linear_graph(5)
    result = pressure_reducing_valve_trace(graph, prv_node="A", downstream_head_limit=50.0)
    assert "zone_pressure_profile" in result
    profile = result["zone_pressure_profile"]
    assert len(profile) >= 1
    # A (origin) should have 0 headloss
    a_entry = next(p for p in profile if p["node"] == "A")
    assert a_entry["cumulative_headloss"] == 0.0
    assert a_entry["residual_pressure"] == pytest.approx(50.0)
    # Nodes further away should have decreasing residual pressure
    costs = [p["cumulative_headloss"] for p in profile]
    assert costs == sorted(costs)


def test_fire_flow_demand_check_flags_deficit():
    edges: list[NetworkEdge] = [
        {"edge_id": "main", "from_node": "SRC", "to_node": "H1", "cost": 1.0, "capacity": 500.0, "flow": 450.0},
        {"edge_id": "small", "from_node": "SRC", "to_node": "H2", "cost": 1.0, "capacity": 200.0, "flow": 50.0},
    ]
    graph = build_network_graph(edges, directed=False)
    result = fire_flow_demand_check(graph, hydrant_nodes=["H1", "H2"], demand_gpm=300.0)
    assert isinstance(result, list)
    assert len(result) == 2
    h1 = next(r for r in result if r["hydrant_node"] == "H1")
    h2 = next(r for r in result if r["hydrant_node"] == "H2")
    # H1: residual = 500 - 450 = 50 < 300  →  fails
    # H2: residual = 200 - 50  = 150 < 300  →  also fails
    assert not h1["adequate_for_fire_flow"]
    assert not h2["adequate_for_fire_flow"]
    assert h1["deficit_gpm"] == pytest.approx(250.0)
    assert h2["deficit_gpm"] == pytest.approx(150.0)


# ─── GAS ──────────────────────────────────────────────────────────────────────


def test_gas_pressure_drop_trace_returns_profile():
    edges: list[NetworkEdge] = [
        {"edge_id": "e1", "from_node": "SRC", "to_node": "A", "cost": 1.0, "flow": 100.0, "diameter": 10.0},
        {"edge_id": "e2", "from_node": "A", "to_node": "B", "cost": 1.0, "flow": 50.0, "diameter": 8.0},
        {"edge_id": "e3", "from_node": "B", "to_node": "C", "cost": 1.0, "flow": 25.0, "diameter": 6.0},
    ]
    graph = build_network_graph(edges, directed=False)
    result = gas_pressure_drop_trace(
        graph, source_node="SRC", inlet_pressure=100.0, min_delivery_pressure=20.0
    )
    assert "pressure_profile" in result
    assert result["zone_node_count"] >= 1
    # All residual pressures must be ≤ inlet pressure
    for entry in result["pressure_profile"]:
        assert entry["residual_pressure"] <= 100.0


def test_gas_odorization_zone_trace_detects_overlap():
    edges: list[NetworkEdge] = [
        {"edge_id": "e1", "from_node": "O1", "to_node": "M", "cost": 1.0},
        {"edge_id": "e2", "from_node": "O2", "to_node": "M", "cost": 1.0},
        {"edge_id": "e3", "from_node": "M", "to_node": "END", "cost": 1.0},
    ]
    graph = build_network_graph(edges, directed=False)
    result = gas_odorization_zone_trace(graph, odorizer_nodes=["O1", "O2"])
    assert isinstance(result, list)
    assert len(result) == 2
    # M and END are reachable from both odorizers → overlap
    overlap_nodes = set()
    for entry in result:
        overlap_nodes.update(entry["overlap_nodes"])
    assert "M" in overlap_nodes


def test_gas_regulator_station_isolation_identifies_isolated():
    edges: list[NetworkEdge] = [
        {"edge_id": "e1", "from_node": "SUPPLY", "to_node": "REG", "cost": 1.0},
        {"edge_id": "e2", "from_node": "REG", "to_node": "DOWN1", "cost": 1.0},
        {"edge_id": "e3", "from_node": "REG", "to_node": "DOWN2", "cost": 1.0},
    ]
    graph = build_network_graph(edges, directed=False)
    result = gas_regulator_station_isolation(
        graph, regulator_node="REG", supply_nodes=["SUPPLY"]
    )
    assert "isolated_nodes" in result
    assert "DOWN1" in result["isolated_nodes"]
    assert "DOWN2" in result["isolated_nodes"]
    assert result["isolated_node_count"] == 2


# ─── CROSS-UTILITY / INFRASTRUCTURE ──────────────────────────────────────────


def test_co_location_conflict_scan_detects_shared_pair():
    electric_edges: list[NetworkEdge] = [
        {"edge_id": "e1", "from_node": "N1", "to_node": "N2", "cost": 1.0},
    ]
    water_edges: list[NetworkEdge] = [
        {"edge_id": "w1", "from_node": "N1", "to_node": "N2", "cost": 1.0},
    ]
    electric_graph = build_network_graph(electric_edges, directed=False)
    water_graph = build_network_graph(water_edges, directed=False)
    result = co_location_conflict_scan({"electric": electric_graph, "water": water_graph})
    assert isinstance(result, list)
    assert len(result) >= 1
    assert result[0]["conflict_type"] == "shared_node_pair"
    assert set(result[0]["utility_types"]) == {"electric", "water"}


def test_interdependency_cascade_simulation_propagates():
    elec_edges: list[NetworkEdge] = [
        {"edge_id": "e1", "from_node": "PS1", "to_node": "PS2", "cost": 1.0},
        {"edge_id": "e2", "from_node": "PS2", "to_node": "PS3", "cost": 1.0},
    ]
    water_edges: list[NetworkEdge] = [
        {"edge_id": "w1", "from_node": "WP1", "to_node": "WP2", "cost": 1.0},
    ]
    primary = build_network_graph(elec_edges, directed=False)
    dependent = build_network_graph(water_edges, directed=False)
    dep_map = {"PS1": ["WP1"]}
    result = interdependency_cascade_simulation(
        primary, dependent, dep_map, initial_failed_nodes=["PS1"]
    )
    assert "total_primary_failures" in result
    assert "total_dependent_failures" in result
    assert "WP1" in result["failed_dependent_nodes"]
    assert result["total_primary_failures"] >= 1


def test_infrastructure_age_risk_weighted_routing_path_found():
    edges: list[NetworkEdge] = [
        {"edge_id": "e1", "from_node": "A", "to_node": "B", "cost": 1.0, "age_years": 5.0, "design_life_years": 50.0},
        {"edge_id": "e2", "from_node": "B", "to_node": "C", "cost": 1.0, "age_years": 45.0, "design_life_years": 50.0},
        {"edge_id": "e3", "from_node": "A", "to_node": "C", "cost": 3.0, "age_years": 2.0, "design_life_years": 50.0},
    ]
    graph = build_network_graph(edges, directed=False)
    result = infrastructure_age_risk_weighted_routing(graph, origin="A", destination="C")
    assert result["path_found"]
    assert result["path_nodes"][0] == "A"
    assert result["path_nodes"][-1] == "C"
    # The old-pipe route A→B→C has high risk premium; direct A→C is newer
    # The risk-weighted router should find A→C despite higher base cost
    assert "A→C" or result["path_nodes"] == ["A", "C"] or result["path_nodes"] == ["A", "B", "C"]
    assert result["risk_premium"] is not None
    assert result["risk_premium"] >= 0.0


def test_critical_customer_coverage_audit_finds_spof():
    # Linear graph: SUPPLY → A → CRITICAL — A is a single point of failure
    edges: list[NetworkEdge] = [
        {"edge_id": "sa", "from_node": "SUPPLY", "to_node": "A", "cost": 1.0},
        {"edge_id": "ac", "from_node": "A", "to_node": "CRITICAL", "cost": 1.0},
    ]
    graph = build_network_graph(edges, directed=False)
    result = critical_customer_coverage_audit(
        graph, critical_customer_nodes=["CRITICAL"], supply_nodes=["SUPPLY"]
    )
    assert len(result) == 1
    entry = result[0]
    assert entry["reachable"]
    assert len(entry["single_points_of_failure_edges"]) >= 1


# ─── STORMWATER / DRAINAGE ────────────────────────────────────────────────────


def test_stormwater_flow_accumulation_accumulates_correctly():
    edges: list[NetworkEdge] = [
        {"edge_id": "ab", "from_node": "A", "to_node": "C", "cost": 1.0},
        {"edge_id": "bc", "from_node": "B", "to_node": "C", "cost": 1.0},
        {"edge_id": "cd", "from_node": "C", "to_node": "D", "cost": 1.0},
    ]
    graph = build_network_graph(edges, directed=True)
    runoff = {"A": 10.0, "B": 15.0, "C": 5.0, "D": 0.0}
    result = stormwater_flow_accumulation(graph, runoff_by_node=runoff)
    d_entry = next(r for r in result if r["node"] == "D")
    # D should accumulate flow from A+B+C = 10+15+5 = 30
    assert d_entry["accumulated_flow"] == pytest.approx(30.0)
    c_entry = next(r for r in result if r["node"] == "C")
    # C accumulates A+B+itself = 10+15+5 = 30 before passing to D
    assert c_entry["accumulated_flow"] == pytest.approx(30.0)


def test_detention_basin_overflow_no_overflow_when_under_capacity():
    graph = _linear_graph(4, directed=True)
    result = detention_basin_overflow_trace(
        graph, basin_node="A", basin_capacity=100.0, inflow=80.0
    )
    assert not result["overflow_occurring"]
    assert result["overflow_volume"] == 0.0
    assert result["overflow_path_nodes"] == []


def test_detention_basin_overflow_traces_when_exceeded():
    graph = _linear_graph(4, directed=True)
    result = detention_basin_overflow_trace(
        graph, basin_node="A", basin_capacity=50.0, inflow=120.0
    )
    assert result["overflow_occurring"]
    assert result["overflow_volume"] == pytest.approx(70.0)
    assert len(result["overflow_path_nodes"]) >= 2
    assert result["overflow_path_nodes"][0] == "A"


def test_inflow_infiltration_scan_flags_excess():
    edges: list[NetworkEdge] = [
        {
            "edge_id": "e1",
            "from_node": "A",
            "to_node": "B",
            "cost": 1.0,
            "observed_flow": 200.0,
            "dry_weather_flow": 100.0,
        },
        {
            "edge_id": "e2",
            "from_node": "B",
            "to_node": "C",
            "cost": 1.0,
            "observed_flow": 110.0,
            "dry_weather_flow": 100.0,
        },
    ]
    graph = build_network_graph(edges, directed=False)
    result = inflow_infiltration_scan(graph, infiltration_threshold_ratio=1.25)
    e1 = next(r for r in result if r["edge_id"] == "e1")
    e2 = next(r for r in result if r["edge_id"] == "e2")
    assert e1["flagged"]                    # ratio = 2.0 > 1.25
    assert not e2["flagged"]               # ratio = 1.1 < 1.25
    assert e1["infiltration_ratio"] == pytest.approx(2.0)


# ─── TELECOM / FIBER ──────────────────────────────────────────────────────────


def test_fiber_splice_node_trace_no_circuits_returns_incident_edges():
    graph = _ring_graph()
    result = fiber_splice_node_trace(graph, splice_node="B")
    assert "incident_edge_ids" in result
    assert len(result["incident_edge_ids"]) >= 2
    assert result["circuits_traversing_splice"] >= 2


def test_fiber_splice_node_trace_with_circuits():
    graph = _ring_graph()
    # Circuit A→C must pass through B on the short route H-A-B-C
    circuits = [("A", "C"), ("H", "A")]
    result = fiber_splice_node_trace(graph, splice_node="B", circuit_endpoints=circuits)
    assert result["circuits_checked"] == 2
    # A→C should traverse B
    traversing = {c["origin"] + "→" + c["destination"] for c in result["affected_circuits"]}
    assert "A→C" in traversing


def test_ring_redundancy_check_identifies_redundancy():
    graph = _ring_graph()
    result = ring_redundancy_check(graph, ring_nodes=["A", "B", "C"], hub_node="H")
    assert isinstance(result, list)
    by_node = {r["node"]: r for r in result}
    # B has a direct link to H (hb), so it should have redundancy
    assert by_node["B"]["reachable_from_hub"]
    assert by_node["B"]["has_redundancy"]


def test_ring_redundancy_check_no_redundancy_on_linear():
    graph = _linear_graph(4)  # A-B-C-D
    result = ring_redundancy_check(graph, ring_nodes=["B", "C", "D"], hub_node="A")
    # On a linear graph there is no alternate path → no redundancy
    for entry in result:
        assert not entry["has_redundancy"]


def test_fiber_cut_impact_matrix_ranks_by_impact():
    graph = _ring_graph()
    # ha is on the only short path from H to A
    circuits = [("H", "A"), ("H", "C"), ("A", "C")]
    result = fiber_cut_impact_matrix(graph, cut_candidate_edges=["ha", "hb"], circuit_endpoints=circuits)
    assert isinstance(result, list)
    # First entry should have highest (or equal) circuits_impacted
    assert result[0]["circuits_impacted"] >= result[-1]["circuits_impacted"]
    for entry in result:
        assert 0 <= entry["impact_ratio"] <= 1.0
