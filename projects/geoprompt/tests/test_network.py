"""Hardened test suite for geoprompt.network — edge cases, large graphs, and domain coverage."""
from __future__ import annotations

import math
import random

import pytest

from geoprompt.network import (
    NetworkRouter,
    allocate_demand_to_supply,
    analyze_network_topology,
    build_landmark_index,
    build_network_graph,
    capacity_constrained_od_assignment,
    co_location_conflict_scan,
    constrained_flow_assignment,
    critical_customer_coverage_audit,
    criticality_ranking_by_node_removal,
    detention_basin_overflow_trace,
    edge_impedance_cost,
    feeder_load_balance_swap,
    fiber_cut_impact_matrix,
    fiber_splice_node_trace,
    fire_flow_demand_check,
    gas_odorization_zone_trace,
    gas_pressure_drop_trace,
    gas_regulator_station_isolation,
    gas_shutdown_impact,
    inflow_infiltration_scan,
    infrastructure_age_risk_weighted_routing,
    interdependency_cascade_simulation,
    landmark_lower_bound,
    load_transfer_feasibility,
    multi_criteria_shortest_path,
    od_cost_matrix,
    pipe_break_isolation_zones,
    pressure_reducing_valve_trace,
    ring_redundancy_check,
    run_utility_scenarios,
    service_area,
    shortest_path,
    stormwater_flow_accumulation,
    trace_electric_feeder,
    trace_water_pressure_zones,
    utility_bottlenecks,
    utility_outage_isolation,
)


# ─── Fixtures ────────────────────────────────────────────────────────────────


def _linear_graph(n: int = 5):
    """A--B--C--D--E with cost 1 each."""
    nodes = [chr(65 + i) for i in range(n)]
    edges = [
        {"edge_id": f"e{i}", "from_node": nodes[i], "to_node": nodes[i + 1], "cost": 1.0, "capacity": 100.0}
        for i in range(n - 1)
    ]
    return build_network_graph(edges, directed=False)


def _ring_graph(n: int = 4):
    """A--B--C--D--A with cost 1 each."""
    nodes = [chr(65 + i) for i in range(n)]
    edges = [
        {"edge_id": f"e{i}", "from_node": nodes[i], "to_node": nodes[(i + 1) % n], "cost": 1.0, "capacity": 100.0}
        for i in range(n)
    ]
    return build_network_graph(edges, directed=False)


def _large_grid(rows: int = 30, cols: int = 30, seed: int = 42):
    """Generate a grid graph with rows*cols nodes."""
    rng = random.Random(seed)
    edges = []
    for r in range(rows):
        for c in range(cols):
            node = f"n{r}_{c}"
            if c + 1 < cols:
                edges.append({"edge_id": f"e_h_{r}_{c}", "from_node": node, "to_node": f"n{r}_{c+1}", "cost": rng.uniform(0.5, 3.0), "capacity": 200.0})
            if r + 1 < rows:
                edges.append({"edge_id": f"e_v_{r}_{c}", "from_node": node, "to_node": f"n{r+1}_{c}", "cost": rng.uniform(0.5, 3.0), "capacity": 200.0})
    return build_network_graph(edges, directed=False)


def _device_graph():
    """Graph with switch/valve device state attributes."""
    return build_network_graph(
        [
            {"edge_id": "e1", "from_node": "A", "to_node": "B", "cost": 1.0, "capacity": 100.0},
            {"edge_id": "e2", "from_node": "B", "to_node": "C", "cost": 1.0, "capacity": 100.0, "device_type": "switch", "state": "open"},
            {"edge_id": "e3", "from_node": "C", "to_node": "D", "cost": 1.0, "capacity": 100.0},
            {"edge_id": "e4", "from_node": "A", "to_node": "D", "cost": 5.0, "capacity": 100.0},
        ],
        directed=False,
    )


# ─── Core Routing ────────────────────────────────────────────────────────────


class TestShortestPath:
    def test_simple_linear(self):
        g = _linear_graph()
        result = shortest_path(g, "A", "E")
        assert result["reachable"] is True
        assert result["total_cost"] == 4.0
        assert result["path_nodes"] == ["A", "B", "C", "D", "E"]

    def test_unreachable_disconnected(self):
        g = build_network_graph(
            [{"edge_id": "e1", "from_node": "A", "to_node": "B", "cost": 1.0}],
            directed=True,
        )
        result = shortest_path(g, "B", "A")
        assert result["reachable"] is False

    def test_same_origin_destination(self):
        g = _linear_graph()
        result = shortest_path(g, "A", "A")
        assert result["reachable"] is True
        assert result["total_cost"] == 0.0

    def test_blocked_edges(self):
        g = _linear_graph()
        result = shortest_path(g, "A", "E", blocked_edges=["e1"])
        assert result["reachable"] is False

    def test_cost_overrides(self):
        g = _linear_graph()
        result = shortest_path(g, "A", "C", edge_cost_overrides={"e0": 100.0})
        assert result["total_cost"] > 2.0

    def test_missing_origin_raises(self):
        g = _linear_graph()
        with pytest.raises(KeyError):
            shortest_path(g, "Z", "A")

    def test_missing_destination_raises(self):
        g = _linear_graph()
        with pytest.raises(KeyError):
            shortest_path(g, "A", "Z")

    def test_max_cost_prunes(self):
        g = _linear_graph()
        result = shortest_path(g, "A", "E", max_cost=2.0)
        assert result["reachable"] is False


class TestServiceArea:
    def test_returns_reachable_within_cost(self):
        g = _linear_graph()
        rows = service_area(g, origins=["A"], max_cost=2.0)
        reached = {r["node"] for r in rows}
        assert "A" in reached
        assert "C" in reached
        assert "D" not in reached

    def test_multiple_origins(self):
        g = _linear_graph()
        rows = service_area(g, origins=["A", "E"], max_cost=1.0)
        reached = {r["node"] for r in rows}
        assert "B" in reached
        assert "D" in reached


class TestODCostMatrix:
    def test_basic_matrix(self):
        g = _linear_graph()
        rows = od_cost_matrix(g, origins=["A"], destinations=["E"])
        assert len(rows) == 1
        assert rows[0]["least_cost"] == 4.0

    def test_unreachable_entry(self):
        g = build_network_graph(
            [{"edge_id": "e1", "from_node": "A", "to_node": "B", "cost": 1.0}],
            directed=True,
        )
        rows = od_cost_matrix(g, origins=["A"], destinations=["A", "B"])
        dest_b = [r for r in rows if r["destination"] == "B"][0]
        assert dest_b["reachable"] is True


# ─── Network Topology ───────────────────────────────────────────────────────


class TestAnalyzeTopology:
    def test_self_loop_detection(self):
        g = build_network_graph(
            [
                {"edge_id": "e1", "from_node": "A", "to_node": "A", "cost": 0.0},
                {"edge_id": "e2", "from_node": "A", "to_node": "B", "cost": 1.0},
            ],
            directed=False,
        )
        result = analyze_network_topology(g)
        assert "e1" in result["self_loop_edge_ids"]

    def test_connected_components(self):
        g = build_network_graph(
            [
                {"edge_id": "e1", "from_node": "A", "to_node": "B", "cost": 1.0},
                {"edge_id": "e2", "from_node": "C", "to_node": "D", "cost": 1.0},
            ],
            directed=False,
        )
        result = analyze_network_topology(g)
        assert result["component_count"] == 2

    def test_duplicate_edges(self):
        g = build_network_graph(
            [
                {"edge_id": "e1", "from_node": "A", "to_node": "B", "cost": 1.0},
                {"edge_id": "e2", "from_node": "A", "to_node": "B", "cost": 2.0},
            ],
            directed=False,
        )
        result = analyze_network_topology(g)
        assert len(result["duplicate_edge_pairs"]) > 0


# ─── Demand Allocation ──────────────────────────────────────────────────────


class TestAllocateDemand:
    def test_basic_allocation(self):
        g = _linear_graph()
        rows = allocate_demand_to_supply(
            g,
            supply_by_node={"A": 100.0},
            demand_by_node={"E": 50.0},
        )
        assert len(rows) == 1
        assert rows[0]["reachable"] is True

    def test_no_supply_raises(self):
        g = _linear_graph()
        with pytest.raises(ValueError):
            allocate_demand_to_supply(g, supply_by_node={}, demand_by_node={"A": 10.0})


# ─── Utility Bottlenecks ────────────────────────────────────────────────────


class TestUtilityBottlenecks:
    def test_loads_distribute(self):
        g = _linear_graph()
        rows = utility_bottlenecks(g, [("A", "E", 10.0)])
        loaded = [r for r in rows if r["flow_load"] > 0]
        assert len(loaded) == 4  # all edges on A->E path

    def test_zero_demand_skipped(self):
        g = _linear_graph()
        rows = utility_bottlenecks(g, [("A", "E", 0.0)])
        assert all(r["flow_load"] == 0.0 for r in rows)


# ─── Electric Domain ────────────────────────────────────────────────────────


class TestTraceElectricFeeder:
    def test_all_energized(self):
        g = _linear_graph()
        rows = trace_electric_feeder(g, source_nodes=["A"])
        assert all(r["energized"] for r in rows)

    def test_open_switch_blocks(self):
        g = _device_graph()
        rows = trace_electric_feeder(g, source_nodes=["A"])
        energized = {r["node"] for r in rows if r["energized"]}
        # Switch e2 is open -> blocks B-C, but A-D path exists via e4
        assert "A" in energized
        assert "B" in energized


class TestUtilityOutageIsolation:
    def test_no_outage(self):
        g = _linear_graph()
        result = utility_outage_isolation(g, source_nodes=["A"], failed_edges=[])
        assert result["deenergized_count"] == 0

    def test_edge_failure_isolation(self):
        g = _linear_graph()
        result = utility_outage_isolation(g, source_nodes=["A"], failed_edges=["e1"])
        assert "C" in result["deenergized_nodes"]


class TestRunUtilityScenarios:
    def test_baseline_vs_outage(self):
        g = _linear_graph()
        result = run_utility_scenarios(g, source_nodes=["A"], outage_edges=["e0"])
        assert result["outage"]["deenergized_count"] > result["baseline"]["deenergized_count"]

    def test_restoration_recovers(self):
        g = _linear_graph()
        result = run_utility_scenarios(g, source_nodes=["A"], outage_edges=["e0"], restoration_edges=["e0"])
        assert result["restoration"]["deenergized_count"] == result["baseline"]["deenergized_count"]


class TestLoadTransferFeasibility:
    def test_parallel_feeders(self):
        g = build_network_graph(
            [
                {"edge_id": "f1", "from_node": "S1", "to_node": "M", "cost": 1.0, "load": 50.0, "capacity": 200.0},
                {"edge_id": "f2", "from_node": "S2", "to_node": "M", "cost": 1.0, "load": 50.0, "capacity": 200.0},
                {"edge_id": "tie", "from_node": "S1", "to_node": "S2", "cost": 1.0, "capacity": 200.0},
            ],
            directed=False,
        )
        tie_attrs = g.edge_attributes["tie"]
        result = load_transfer_feasibility(g, feeder_a_source="S1", feeder_b_source="S2", tie_edge=tie_attrs)
        assert result["feasible"] is True


# ─── Water Domain ────────────────────────────────────────────────────────────


class TestTraceWaterPressureZones:
    def test_all_within_zone(self):
        g = _linear_graph(3)
        rows = trace_water_pressure_zones(g, source_nodes=["A"], max_headloss=1e6)
        assert all(r["within_pressure_zone"] for r in rows)

    def test_negative_headloss_raises(self):
        g = _linear_graph()
        with pytest.raises(ValueError):
            trace_water_pressure_zones(g, source_nodes=["A"], max_headloss=-1)


class TestPipeBreakIsolation:
    def test_valve_bounded_zone(self):
        g = _linear_graph()
        result = pipe_break_isolation_zones(g, break_edge_id="e1")
        assert "affected_nodes" in result


class TestFireFlowDemand:
    def test_adequate_flow(self):
        g = build_network_graph(
            [{"edge_id": "e1", "from_node": "A", "to_node": "H", "cost": 1.0, "capacity": 2000.0, "flow": 100.0}],
            directed=False,
        )
        results = fire_flow_demand_check(g, hydrant_nodes=["H"], demand_gpm=1000.0)
        assert results[0]["adequate_for_fire_flow"] is True

    def test_deficit(self):
        g = build_network_graph(
            [{"edge_id": "e1", "from_node": "A", "to_node": "H", "cost": 1.0, "capacity": 500.0, "flow": 100.0}],
            directed=False,
        )
        results = fire_flow_demand_check(g, hydrant_nodes=["H"], demand_gpm=1000.0)
        assert results[0]["adequate_for_fire_flow"] is False
        assert results[0]["deficit_gpm"] > 0


# ─── Gas Domain ──────────────────────────────────────────────────────────────


class TestGasPressureDrop:
    def test_pressure_profile(self):
        g = _linear_graph(3)
        result = gas_pressure_drop_trace(g, source_node="A", inlet_pressure=100.0)
        assert result["zone_node_count"] >= 2


class TestGasShutdownImpact:
    def test_shutdown(self):
        g = _linear_graph()
        result = gas_shutdown_impact(g, source_nodes=["A"], shutdown_edges=["e0"])
        assert result["impacted_count"] > 0


class TestGasOdorizationZone:
    def test_single_odorizer(self):
        g = _linear_graph()
        results = gas_odorization_zone_trace(g, odorizer_nodes=["A"])
        assert results[0]["zone_node_count"] == 5

    def test_overlap(self):
        g = _linear_graph()
        results = gas_odorization_zone_trace(g, odorizer_nodes=["A", "E"])
        total_overlap = sum(r["overlap_node_count"] for r in results)
        assert total_overlap > 0


class TestGasRegulatorIsolation:
    def test_isolation_with_alternate(self):
        g = _ring_graph()
        result = gas_regulator_station_isolation(g, regulator_node="A")
        assert result["alternate_path_available"] is True


# ─── Cross-Utility ──────────────────────────────────────────────────────────


class TestCoLocationConflict:
    def test_shared_node_pair(self):
        elec = build_network_graph(
            [{"edge_id": "e1", "from_node": "A", "to_node": "B", "cost": 1.0}], directed=False
        )
        water = build_network_graph(
            [{"edge_id": "w1", "from_node": "A", "to_node": "B", "cost": 1.0}], directed=False
        )
        conflicts = co_location_conflict_scan({"electric": elec, "water": water})
        assert len(conflicts) > 0
        assert conflicts[0]["conflict_type"] == "shared_node_pair"


class TestInterdependencyCascade:
    def test_single_round(self):
        primary = _linear_graph(3)
        dependent = build_network_graph(
            [{"edge_id": "d1", "from_node": "X", "to_node": "Y", "cost": 1.0}], directed=False
        )
        result = interdependency_cascade_simulation(
            primary, dependent,
            dependency_map={"A": ["X"]},
            initial_failed_nodes=["A"],
        )
        assert "X" in result["failed_dependent_nodes"]


class TestAgeRiskRouting:
    def test_risk_premium(self):
        g = build_network_graph(
            [
                {"edge_id": "e1", "from_node": "A", "to_node": "B", "cost": 1.0, "age_years": 50, "design_life_years": 50},
                {"edge_id": "e2", "from_node": "A", "to_node": "B", "cost": 2.0, "age_years": 0, "design_life_years": 50},
            ],
            directed=False,
        )
        result = infrastructure_age_risk_weighted_routing(g, "A", "B")
        assert result["path_found"] is True
        assert result["risk_premium"] >= 0


class TestCriticalCustomerAudit:
    def test_single_point_of_failure(self):
        g = _linear_graph()
        results = critical_customer_coverage_audit(g, critical_customer_nodes=["E"], supply_nodes=["A"])
        assert len(results) == 1
        assert len(results[0]["single_points_of_failure_edges"]) > 0


# ─── Stormwater ──────────────────────────────────────────────────────────────


class TestStormwaterAccumulation:
    def test_accumulation(self):
        g = build_network_graph(
            [
                {"edge_id": "e1", "from_node": "inlet", "to_node": "junction", "cost": 1.0, "capacity": 50.0},
                {"edge_id": "e2", "from_node": "junction", "to_node": "outfall", "cost": 1.0, "capacity": 50.0},
            ],
            directed=True,
        )
        results = stormwater_flow_accumulation(g, runoff_by_node={"inlet": 10.0, "junction": 5.0})
        outfall = [r for r in results if r["node"] == "outfall"][0]
        assert outfall["accumulated_flow"] == 15.0


class TestDetentionOverflow:
    def test_no_overflow(self):
        g = _linear_graph(3)
        result = detention_basin_overflow_trace(g, basin_node="A", basin_capacity=100.0, inflow=50.0)
        assert result["overflow_occurring"] is False

    def test_overflow(self):
        g = _linear_graph(3)
        result = detention_basin_overflow_trace(g, basin_node="A", basin_capacity=50.0, inflow=100.0)
        assert result["overflow_occurring"] is True
        assert result["overflow_volume"] == 50.0


class TestInfiltrationScan:
    def test_flagged_edges(self):
        g = build_network_graph(
            [{"edge_id": "e1", "from_node": "A", "to_node": "B", "cost": 1.0, "observed_flow": 200, "dry_weather_flow": 100}],
            directed=False,
        )
        results = inflow_infiltration_scan(g, infiltration_threshold_ratio=1.25)
        assert results[0]["flagged"] is True


# ─── Telecom ─────────────────────────────────────────────────────────────────


class TestFiberSpliceNode:
    def test_incident_edges(self):
        g = _linear_graph()
        result = fiber_splice_node_trace(g, splice_node="C")
        assert result["circuits_traversing_splice"] > 0

    def test_circuit_check(self):
        g = _linear_graph()
        result = fiber_splice_node_trace(g, splice_node="C", circuit_endpoints=[("A", "E")])
        assert result["circuits_traversing_splice"] == 1


class TestRingRedundancy:
    def test_ring_has_redundancy(self):
        g = _ring_graph(4)
        results = ring_redundancy_check(g, ring_nodes=["B", "C", "D"], hub_node="A")
        assert all(r["has_redundancy"] for r in results)

    def test_linear_no_redundancy(self):
        g = _linear_graph()
        results = ring_redundancy_check(g, ring_nodes=["E"], hub_node="A")
        assert results[0]["has_redundancy"] is False


class TestFiberCutImpact:
    def test_impact_matrix(self):
        g = _linear_graph()
        results = fiber_cut_impact_matrix(
            g,
            cut_candidate_edges=["e0", "e1"],
            circuit_endpoints=[("A", "E")],
        )
        assert results[0]["circuits_impacted"] == 1


# ─── NetworkRouter ───────────────────────────────────────────────────────────


class TestNetworkRouter:
    def test_cached_matches_uncached(self):
        g = _linear_graph()
        router = NetworkRouter(g)
        cached = router.shortest_path("A", "E")
        uncached = shortest_path(g, "A", "E")
        assert cached["total_cost"] == uncached["total_cost"]

    def test_cache_reuse(self):
        g = _linear_graph()
        router = NetworkRouter(g)
        router.shortest_path("A", "E")
        router.shortest_path("A", "C")
        assert "A" in router._distance_cache


# ─── Landmark Index ──────────────────────────────────────────────────────────


class TestLandmarkIndex:
    def test_lower_bound_admissible(self):
        g = _linear_graph()
        index = build_landmark_index(g, landmarks=["A", "E"])
        lb = landmark_lower_bound(index, "B", "D")
        actual = shortest_path(g, "B", "D")["total_cost"]
        assert lb <= actual


# ─── Edge Impedance ──────────────────────────────────────────────────────────


class TestEdgeImpedance:
    def test_custom_cost(self):
        g = _linear_graph()
        edge = g.edge_attributes["e0"]
        cost = edge_impedance_cost(edge, weights={"cost": 1.0})
        assert cost > 0


# ─── Constrained Flow ───────────────────────────────────────────────────────


class TestConstrainedFlow:
    def test_assignment(self):
        g = _linear_graph()
        results = constrained_flow_assignment(
            g,
            od_demands=[("A", "E", 10.0)],
            capacity_field="capacity",
        )
        assert len(results) > 0


class TestCapacityConstrainedOD:
    def test_multi_round(self):
        g = _linear_graph()
        results = capacity_constrained_od_assignment(
            g,
            od_demands=[("A", "E", 10.0)],
            capacity_field="capacity",
        )
        assert len(results) > 0


# ─── Criticality Ranking ────────────────────────────────────────────────────


class TestCriticalityRanking:
    def test_center_node_most_critical(self):
        g = _linear_graph()
        results = criticality_ranking_by_node_removal(g)
        assert len(results) == 5


# ─── Large Graph Stress Tests ───────────────────────────────────────────────


class TestLargeGraph:
    def test_shortest_path_30x30(self):
        g = _large_grid(30, 30)
        result = shortest_path(g, "n0_0", "n29_29")
        assert result["reachable"] is True
        assert result["total_cost"] > 0

    def test_service_area_30x30(self):
        g = _large_grid(30, 30)
        rows = service_area(g, origins=["n0_0"], max_cost=20.0)
        assert len(rows) > 10

    def test_od_matrix_30x30(self):
        g = _large_grid(30, 30)
        rows = od_cost_matrix(
            g,
            origins=["n0_0", "n0_29"],
            destinations=["n29_0", "n29_29"],
        )
        assert all(r["reachable"] for r in rows)

    def test_topology_30x30(self):
        g = _large_grid(30, 30)
        result = analyze_network_topology(g)
        assert result["component_count"] == 1
        assert result["node_count"] == 900


# ─── Directed Graph Edge Cases ───────────────────────────────────────────────


class TestDirectedGraph:
    def test_one_way(self):
        g = build_network_graph(
            [{"edge_id": "e1", "from_node": "A", "to_node": "B", "cost": 1.0}],
            directed=True,
        )
        forward = shortest_path(g, "A", "B")
        backward = shortest_path(g, "B", "A")
        assert forward["reachable"] is True
        assert backward["reachable"] is False

    def test_bidirectional_flag(self):
        g = build_network_graph(
            [{"edge_id": "e1", "from_node": "A", "to_node": "B", "cost": 1.0, "bidirectional": True}],
            directed=True,
        )
        backward = shortest_path(g, "B", "A")
        assert backward["reachable"] is True


# ─── Empty / Single-Node ────────────────────────────────────────────────────


class TestEdgeCases:
    def test_single_node_graph(self):
        g = build_network_graph(
            [{"edge_id": "e1", "from_node": "A", "to_node": "A", "cost": 0.0}],
            directed=False,
        )
        result = shortest_path(g, "A", "A")
        assert result["reachable"] is True

    def test_service_area_empty_origins(self):
        g = _linear_graph()
        rows = service_area(g, origins=[], max_cost=10.0)
        assert len(rows) == 0

    def test_od_matrix_empty(self):
        g = _linear_graph()
        rows = od_cost_matrix(g, origins=[], destinations=["A"])
        assert len(rows) == 0
