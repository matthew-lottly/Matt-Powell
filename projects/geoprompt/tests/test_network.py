from __future__ import annotations

import math

from geoprompt import GeoPromptFrame
from geoprompt.equations import (
    utility_capacity_stress_index,
    utility_headloss_hazen_williams,
    utility_reliability_score,
    utility_service_deficit,
)
from geoprompt.network import (
    NetworkRouter,
    NetworkEdge,
    analyze_network_topology,
    allocate_demand_to_supply,
    build_landmark_index,
    build_network_graph,
    capacity_constrained_od_assignment,
    constrained_flow_assignment,
    gas_shutdown_impact,
    landmark_lower_bound,
    multi_criteria_shortest_path,
    od_cost_matrix,
    run_utility_scenarios,
    service_area,
    shortest_path,
    trace_electric_feeder,
    trace_water_pressure_zones,
    utility_bottlenecks,
    utility_outage_isolation,
)


def _sample_edges() -> list[NetworkEdge]:
    return [
        {"edge_id": "ab", "from_node": "A", "to_node": "B", "cost": 1.0, "capacity": 10.0},
        {"edge_id": "bc", "from_node": "B", "to_node": "C", "cost": 1.0, "capacity": 3.0},
        {"edge_id": "ad", "from_node": "A", "to_node": "D", "cost": 2.0, "capacity": 4.0},
        {"edge_id": "dc", "from_node": "D", "to_node": "C", "cost": 1.0, "capacity": 2.0},
    ]


def test_shortest_path_and_service_area() -> None:
    graph = build_network_graph(_sample_edges(), directed=False)

    path = shortest_path(graph, origin="A", destination="C")
    assert path["reachable"] is True
    assert path["path_nodes"] == ["A", "B", "C"]
    assert round(float(path["total_cost"]), 6) == 2.0

    reachable = service_area(graph, origins=["A"], max_cost=2.0)
    nodes = {row["node"] for row in reachable}
    assert nodes == {"A", "B", "D", "C"}


def test_od_matrix_and_supply_allocation() -> None:
    graph = build_network_graph(_sample_edges(), directed=False)

    rows = od_cost_matrix(graph, origins=["A", "D"], destinations=["B", "C"])
    assert len(rows) == 4
    assert any(row["origin"] == "A" and row["destination"] == "C" and row["least_cost"] == 2.0 for row in rows)

    allocation = allocate_demand_to_supply(
        graph,
        supply_by_node={"A": 12.0},
        demand_by_node={"B": 3.0, "C": 5.0, "D": 2.0},
    )
    assert len(allocation) == 3
    assert all(row["assigned_supply_node"] == "A" for row in allocation)
    assert sum(float(row["service_deficit"]) for row in allocation) == 0.0


def test_utility_bottleneck_ranks_edges() -> None:
    graph = build_network_graph(_sample_edges(), directed=False)
    rows = utility_bottlenecks(
        graph,
        od_demands=[("A", "C", 4.0), ("D", "B", 2.0)],
    )
    assert len(rows) == 4
    assert float(rows[0]["capacity_stress"]) >= float(rows[-1]["capacity_stress"])


def test_topology_and_multicriteria_routing() -> None:
    graph = build_network_graph(_sample_edges(), directed=False)
    topology = analyze_network_topology(graph)
    assert topology["component_count"] == 1
    assert topology["node_count"] == 4

    weighted_path = multi_criteria_shortest_path(
        graph,
        origin="A",
        destination="C",
        weights={"base": 1.0, "congestion": 3.0},
    )
    assert weighted_path["reachable"] is True
    assert weighted_path["cost_mode"] == "multi_criteria"


def test_constrained_assignment_and_domain_traces() -> None:
    graph = build_network_graph(_sample_edges(), directed=False)

    assignment = constrained_flow_assignment(
        graph,
        od_demands=[("A", "C", 5.0), ("D", "B", 3.0)],
        max_iterations=5,
    )
    assert assignment["iterations"] >= 1
    assert len(assignment["edge_results"]) == 4

    feeder = trace_electric_feeder(graph, source_nodes=["A"], open_switch_edges=["ab", "ad"])
    assert any(row["node"] == "C" and row["energized"] is False for row in feeder)

    outage = utility_outage_isolation(graph, source_nodes=["A"], failed_edges=["ab", "ad"], critical_nodes=["B", "C"])
    assert outage["critical_impacted_count"] >= 1
    assert "supplied_nodes" in outage
    assert "supplied_count" in outage
    assert isinstance(outage["supplied_nodes"], list)
    assert outage["supplied_count"] + outage["deenergized_count"] == len(graph.nodes)

    pressure = trace_water_pressure_zones(graph, source_nodes=["A"], max_headloss=200.0)
    assert len(pressure) > 0

    gas = gas_shutdown_impact(graph, source_nodes=["A"], shutdown_edges=["ab", "ad"])
    assert gas["impacted_count"] >= 1


def test_router_cache_and_landmarks() -> None:
    graph = build_network_graph(_sample_edges(), directed=False)
    router = NetworkRouter(graph)

    path = router.shortest_path("A", "C")
    assert path["reachable"] is True
    matrix = router.od_cost_matrix(origins=["A"], destinations=["B", "C"])
    assert len(matrix) == 2

    landmarks = build_landmark_index(graph, landmarks=["A", "D"])
    lower_bound = landmark_lower_bound(landmarks, origin="A", destination="C")
    assert lower_bound >= 0.0


def test_device_state_propagation_spill_and_scenarios() -> None:
    graph = build_network_graph(
        [
            {"edge_id": "ab", "from_node": "A", "to_node": "B", "cost": 1.0, "capacity": 3.0, "device_type": "switch", "state": "closed"},
            {"edge_id": "bc", "from_node": "B", "to_node": "C", "cost": 1.0, "capacity": 1.0, "device_type": "switch", "state": "open"},
            {"edge_id": "ad", "from_node": "A", "to_node": "D", "cost": 1.0, "capacity": 1.0, "device_type": "valve", "state": "open"},
            {"edge_id": "dc", "from_node": "D", "to_node": "C", "cost": 1.0, "capacity": 1.0, "device_type": "valve", "state": "closed"},
        ],
        directed=False,
    )

    feeder = trace_electric_feeder(graph, source_nodes=["A"])
    assert any(row["node"] == "C" and row["energized"] is False for row in feeder)

    spill = capacity_constrained_od_assignment(
        graph,
        od_demands=[("A", "C", 3.0)],
        capacity_field="capacity",
        max_rounds=4,
    )
    assert spill["total_requested"] == 3.0
    assert spill["total_delivered"] < 3.0
    assert spill["total_unmet"] > 0.0

    scenario = run_utility_scenarios(
        graph,
        source_nodes=["A"],
        critical_nodes=["C"],
        outage_edges=["ab"],
        restoration_edges=[],
    )
    assert "delta_outage_vs_baseline" in scenario
    assert "supplied_count" in scenario["delta_outage_vs_baseline"]
    assert "supplied_count" in scenario["delta_restoration_vs_outage"]
    assert len(scenario["critical_edge_rankings"]) == len(graph.edge_attributes)
    assert "supplied_count" in scenario["critical_edge_rankings"][0]
    assert "supplied_count" in scenario["critical_node_rankings"][0]

    # Device state params thread through scenario runner without error
    scenario_with_state = run_utility_scenarios(
        graph,
        source_nodes=["A"],
        critical_nodes=["C"],
        outage_edges=["ab"],
        restoration_edges=[],
        device_type_field="device_type",
        state_field="state",
        unknown_state_policy="passable",
    )
    assert scenario_with_state["baseline"]["supplied_count"] == scenario["baseline"]["supplied_count"]

    # static_blocked_edges permanently remove an edge from all snapshots
    scenario_static = run_utility_scenarios(
        graph,
        source_nodes=["A"],
        critical_nodes=["C"],
        static_blocked_edges=["dc"],
    )
    # dc blocked in baseline → fewer reachable nodes than unrestricted
    assert scenario_static["baseline"]["supplied_count"] <= len(graph.nodes)


def test_utility_equations() -> None:
    assert utility_capacity_stress_index(8.0, 10.0) < 1.0
    assert utility_capacity_stress_index(15.0, 10.0) > 1.0

    headloss = utility_headloss_hazen_williams(length=500.0, flow=0.2, diameter=0.3, roughness_coefficient=130.0)
    assert math.isfinite(headloss)
    assert headloss > 0

    reliability = utility_reliability_score(base_reliability=0.95, redundancy_factor=2.0, stress_index=0.1)
    assert 0.0 <= reliability <= 1.0

    assert utility_service_deficit(demand=100.0, delivered=75.0) == 0.25


def test_frame_network_analysis_methods() -> None:
    frame = GeoPromptFrame.from_records(
        [
            {
                "edge_id": "ab",
                "from_node": "A",
                "to_node": "B",
                "node": "A",
                "supply": 10.0,
                "demand": 0.0,
                "cost": 1.0,
                "capacity": 10.0,
                "device_type": "switch",
                "state": "closed",
                "geometry": {"type": "Point", "coordinates": [0.0, 0.0]},
            },
            {
                "edge_id": "bc",
                "from_node": "B",
                "to_node": "C",
                "node": "B",
                "supply": 0.0,
                "demand": 2.0,
                "cost": 1.0,
                "capacity": 3.0,
                "device_type": "switch",
                "state": "open",
                "geometry": {"type": "Point", "coordinates": [1.0, 0.0]},
            },
            {
                "edge_id": "ad",
                "from_node": "A",
                "to_node": "D",
                "node": "D",
                "supply": 0.0,
                "demand": 1.0,
                "cost": 2.0,
                "capacity": 4.0,
                "device_type": "switch",
                "state": "open",
                "geometry": {"type": "Point", "coordinates": [0.0, 1.0]},
            },
            {
                "edge_id": "dc",
                "from_node": "D",
                "to_node": "C",
                "node": "C",
                "supply": 0.0,
                "demand": 5.0,
                "cost": 1.0,
                "capacity": 2.0,
                "device_type": "switch",
                "state": "closed",
                "geometry": {"type": "Point", "coordinates": [1.0, 1.0]},
            },
        ]
    )

    shortest = frame.analysis.network_shortest_path(
        from_node_column="from_node",
        to_node_column="to_node",
        origin_node="A",
        destination_node="C",
        edge_id_column="edge_id",
        cost_column="cost",
    )
    assert shortest["reachable"] is True
    assert shortest["path_nodes"] == ["A", "B", "C"]

    area = frame.network_service_area_analysis(
        from_node_column="from_node",
        to_node_column="to_node",
        origin_nodes=["A"],
        max_cost=2.0,
        edge_id_column="edge_id",
        cost_column="cost",
    )
    assert any(row["node"] == "C" and row["within_service_area"] for row in area)

    matrix = frame.network_od_matrix_analysis(
        from_node_column="from_node",
        to_node_column="to_node",
        origin_nodes=["A"],
        destination_nodes=["B", "C"],
        edge_id_column="edge_id",
        cost_column="cost",
    )
    assert len(matrix) == 2

    allocation = frame.utility_supply_allocation_analysis(
        from_node_column="from_node",
        to_node_column="to_node",
        node_column="node",
        supply_column="supply",
        demand_column="demand",
        edge_id_column="edge_id",
        cost_column="cost",
    )
    assert len(allocation) == 3
    assert all(row["reachable"] is True for row in allocation)

    bottlenecks = frame.utility_bottleneck_scan_analysis(
        from_node_column="from_node",
        to_node_column="to_node",
        edge_id_column="edge_id",
        cost_column="cost",
        capacity_column="capacity",
        od_demands=[("A", "C", 6.0), ("D", "B", 2.0)],
    )
    assert float(bottlenecks[0]["capacity_stress"]) >= float(bottlenecks[-1]["capacity_stress"])

    topology = frame.network_topology_audit_analysis(
        from_node_column="from_node",
        to_node_column="to_node",
        edge_id_column="edge_id",
        cost_column="cost",
    )
    assert topology["component_count"] == 1

    multicriteria = frame.network_multicriteria_path_analysis(
        from_node_column="from_node",
        to_node_column="to_node",
        origin_node="A",
        destination_node="C",
        edge_id_column="edge_id",
        cost_column="cost",
        congestion_column="demand",
        condition_column="supply",
        weights={"base": 1.0, "congestion": 2.0, "condition_penalty": 1.0},
    )
    assert multicriteria["reachable"] is True

    capacity_assignment = frame.network_capacity_assignment_analysis(
        from_node_column="from_node",
        to_node_column="to_node",
        edge_id_column="edge_id",
        cost_column="cost",
        capacity_column="capacity",
        od_demands=[("A", "C", 6.0), ("D", "B", 2.0)],
        max_iterations=4,
    )
    assert capacity_assignment["iterations"] >= 1

    feeder_trace = frame.electric_feeder_trace_analysis(
        from_node_column="from_node",
        to_node_column="to_node",
        source_nodes=["A"],
        open_switch_edges=["ab", "ad"],
        edge_id_column="edge_id",
        cost_column="cost",
    )
    assert any(row["node"] == "C" and row["energized"] is False for row in feeder_trace)

    outage_scan = frame.utility_outage_isolation_analysis(
        from_node_column="from_node",
        to_node_column="to_node",
        source_nodes=["A"],
        failed_edges=["ab", "ad"],
        critical_nodes=["B", "C"],
        edge_id_column="edge_id",
        cost_column="cost",
    )
    assert outage_scan["critical_impacted_count"] >= 1

    pressure_zones = frame.water_pressure_zones_analysis(
        from_node_column="from_node",
        to_node_column="to_node",
        source_nodes=["A"],
        max_headloss=200.0,
        edge_id_column="edge_id",
        cost_column="cost",
    )
    assert len(pressure_zones) > 0

    spill_assignment = frame.network_capacity_spill_assignment_analysis(
        from_node_column="from_node",
        to_node_column="to_node",
        edge_id_column="edge_id",
        cost_column="cost",
        capacity_column="capacity",
        od_demands=[("A", "C", 12.0)],
        max_rounds=4,
    )
    assert spill_assignment["total_delivered"] < spill_assignment["total_requested"]

    feeder_by_state = frame.electric_feeder_trace_analysis(
        from_node_column="from_node",
        to_node_column="to_node",
        source_nodes=["A"],
        edge_id_column="edge_id",
        cost_column="cost",
        device_type_column="device_type",
        state_column="state",
        unknown_state_policy="passable",
    )
    assert any(row["node"] == "C" and row["energized"] is False for row in feeder_by_state)

    scenario = frame.utility_scenario_runner_analysis(
        from_node_column="from_node",
        to_node_column="to_node",
        source_nodes=["A"],
        outage_edges=["ab", "ad"],
        restoration_edges=["ab"],
        critical_nodes=["B", "C"],
        edge_id_column="edge_id",
        cost_column="cost",
    )
    assert "delta_restoration_vs_outage" in scenario

    gas_impact = frame.gas_shutdown_impact_analysis(
        from_node_column="from_node",
        to_node_column="to_node",
        source_nodes=["A"],
        shutdown_edges=["ab", "ad"],
        edge_id_column="edge_id",
        cost_column="cost",
    )
    assert gas_impact["impacted_count"] >= 1
