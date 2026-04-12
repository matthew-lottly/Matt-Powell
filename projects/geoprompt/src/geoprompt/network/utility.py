"""Utility-domain network workflows built on core routing primitives."""

from __future__ import annotations

import math
from collections import deque
from itertools import combinations
from typing import Any, cast

from ..equations import utility_headloss_hazen_williams, utility_service_deficit
from .core import NetworkEdge, NetworkGraph
from .demand import utility_bottlenecks
from .routing import build_network_graph, multi_criteria_shortest_path, service_area, shortest_path


def _edge_blocked(edge: NetworkEdge, failed_edges: set[str], respect_open_devices: bool = False) -> bool:
    edge_id = str(edge.get("edge_id", ""))
    if edge_id in failed_edges:
        return True
    if not respect_open_devices:
        return False
    state = str(edge.get("state", "")).lower()
    return state in {"open", "normally_open"}


def _reachable_nodes(
    graph: NetworkGraph,
    source_nodes: list[str],
    failed_edges: list[str] | None = None,
    respect_open_devices: bool = False,
) -> set[str]:
    failed = set(failed_edges or [])
    if respect_open_devices:
        for edge in graph.edge_attributes.values():
            if _edge_blocked(edge, set(), respect_open_devices=True):
                failed.add(str(edge.get("edge_id", "")))

    rows = service_area(
        graph,
        origins=source_nodes,
        max_cost=math.inf,
        blocked_edges=sorted(failed),
    )
    return {str(row["node"]) for row in rows}


def _edge_list(graph: NetworkGraph) -> list[NetworkEdge]:
    return [cast(NetworkEdge, dict(edge)) for edge in graph.edge_attributes.values()]


def _graph_with_added_edges(graph: NetworkGraph, add_edges: list[dict[str, object]]) -> NetworkGraph:
    merged = _edge_list(graph)
    for idx, edge in enumerate(add_edges):
        normalized = dict(edge)
        normalized.setdefault("edge_id", f"project-edge-{idx}")
        merged.append(cast(NetworkEdge, normalized))
    return build_network_graph(merged, directed=graph.directed)


def trace_electric_feeder(graph: NetworkGraph, source_nodes: list[str]) -> list[dict[str, Any]]:
    energized = _reachable_nodes(graph, source_nodes, respect_open_devices=True)
    rows: list[dict[str, Any]] = []
    for node in sorted(graph.adjacency.keys()):
        rows.append({"node": node, "energized": node in energized})
    return rows


def utility_outage_isolation(
    graph: NetworkGraph,
    source_nodes: list[str],
    failed_edges: list[str],
) -> dict[str, Any]:
    energized = _reachable_nodes(graph, source_nodes, failed_edges=failed_edges, respect_open_devices=True)
    all_nodes = set(graph.adjacency.keys())
    deenergized = sorted(all_nodes - energized)
    return {
        "energized_nodes": sorted(energized),
        "deenergized_nodes": deenergized,
        "deenergized_count": len(deenergized),
        "failed_edge_count": len(failed_edges),
    }


def run_utility_scenarios(
    graph: NetworkGraph,
    source_nodes: list[str],
    outage_edges: list[str] | None = None,
    restoration_edges: list[str] | None = None,
) -> dict[str, Any]:
    outage_edges = outage_edges or []
    restoration_edges = restoration_edges or []
    baseline = utility_outage_isolation(graph, source_nodes, failed_edges=[])
    outage = utility_outage_isolation(graph, source_nodes, failed_edges=outage_edges)
    restored_failures = sorted(set(outage_edges) - set(restoration_edges))
    restoration = utility_outage_isolation(graph, source_nodes, failed_edges=restored_failures)
    return {"baseline": baseline, "outage": outage, "restoration": restoration}


def load_transfer_feasibility(
    graph: NetworkGraph,
    feeder_a_source: str,
    feeder_b_source: str,
    tie_edge: NetworkEdge,
) -> dict[str, Any]:
    tie_capacity = float(tie_edge.get("capacity", math.inf))
    tie_load = float(tie_edge.get("load", 0.0))
    spare = tie_capacity - tie_load if math.isfinite(tie_capacity) else math.inf
    path = shortest_path(graph, feeder_a_source, feeder_b_source)
    return {
        "feasible": bool(path["reachable"]) and spare > 0,
        "available_transfer_capacity": max(0.0, spare) if math.isfinite(spare) else math.inf,
        "path_cost": float(path["total_cost"]),
    }


def n_minus_one_edge_contingency_screen(
    graph: NetworkGraph,
    source_nodes: list[str],
    demand_by_node: dict[str, float] | None = None,
    critical_nodes: list[str] | None = None,
    candidate_edge_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    if not source_nodes:
        raise ValueError("source_nodes must not be empty")
    demand_by_node = demand_by_node or {}
    critical_nodes = critical_nodes or []
    baseline = _reachable_nodes(graph, source_nodes)
    candidates = candidate_edge_ids or sorted(graph.edge_attributes.keys())

    rows: list[dict[str, Any]] = []
    for edge_id in candidates:
        energized = _reachable_nodes(graph, source_nodes, failed_edges=[edge_id])
        lost_nodes = sorted(baseline - energized)
        lost_demand = sum(float(demand_by_node.get(node, 0.0)) for node in lost_nodes)
        lost_critical = [node for node in critical_nodes if node in lost_nodes]
        rows.append(
            {
                "cut_edge_id": edge_id,
                "lost_node_count": len(lost_nodes),
                "lost_demand": lost_demand,
                "lost_critical_count": len(lost_critical),
                "lost_nodes": lost_nodes,
            }
        )

    rows.sort(key=lambda item: (-float(item["lost_demand"]), -int(item["lost_critical_count"]), str(item["cut_edge_id"])))
    return rows


def outage_restoration_tie_options(
    graph: NetworkGraph,
    source_nodes: list[str],
    affected_nodes: list[str],
    tie_edge_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    if not source_nodes:
        raise ValueError("source_nodes must not be empty")

    if tie_edge_ids is None:
        detected: list[str] = []
        for edge_id, edge in graph.edge_attributes.items():
            state = str(edge.get("state", "")).lower()
            device_type = str(edge.get("device_type", "")).lower()
            if state in {"open", "normally_open"} or device_type in {"tie", "switch"}:
                detected.append(edge_id)
        tie_edge_ids = sorted(detected)

    rows: list[dict[str, Any]] = []
    for tie_edge_id in tie_edge_ids:
        failed = [eid for eid, edge in graph.edge_attributes.items() if _edge_blocked(edge, set(), True)]
        failed = [eid for eid in failed if eid != tie_edge_id]
        energized = _reachable_nodes(graph, source_nodes, failed_edges=failed)
        restored = [node for node in affected_nodes if node in energized]
        rows.append(
            {
                "tie_edge_id": tie_edge_id,
                "restored_target_count": len(restored),
                "restored_nodes": sorted(restored),
            }
        )

    rows.sort(key=lambda item: (-int(item["restored_target_count"]), str(item["tie_edge_id"])))
    return rows


def n_minus_k_edge_contingency_screen(
    graph: NetworkGraph,
    source_nodes: list[str],
    k: int,
    candidate_edge_ids: list[str] | None = None,
    max_combinations: int | None = None,
    prefilter_with_n_minus_one: bool = False,
) -> list[dict[str, Any]]:
    if k <= 0:
        raise ValueError("k must be >= 1")
    candidates = candidate_edge_ids or sorted(graph.edge_attributes.keys())
    if prefilter_with_n_minus_one:
        ranked = n_minus_one_edge_contingency_screen(graph, source_nodes, candidate_edge_ids=candidates)
        candidates = [str(row["cut_edge_id"]) for row in ranked]

    baseline = _reachable_nodes(graph, source_nodes)
    rows: list[dict[str, Any]] = []
    for idx, combo in enumerate(combinations(candidates, k)):
        if max_combinations is not None and idx >= max_combinations:
            break
        energized = _reachable_nodes(graph, source_nodes, failed_edges=list(combo))
        rows.append(
            {
                "k": k,
                "cut_edge_ids": list(combo),
                "lost_node_count": len(baseline - energized),
            }
        )

    rows.sort(key=lambda item: (-int(item["lost_node_count"]), str(item["cut_edge_ids"])))
    return rows


def crew_dispatch_optimizer(
    graph: NetworkGraph,
    source_nodes: list[str],
    failed_edges: list[str],
    repair_time_by_edge: dict[str, float] | None = None,
    demand_by_node: dict[str, float] | None = None,
    critical_nodes: list[str] | None = None,
) -> dict[str, Any]:
    if not failed_edges:
        return {"total_repairs_planned": 0, "repair_plan": []}

    repair_time_by_edge = repair_time_by_edge or {}
    demand_by_node = demand_by_node or {}
    critical_nodes = critical_nodes or []

    unresolved = set(failed_edges)
    plan: list[dict[str, Any]] = []
    while unresolved:
        best_edge = None
        best_score = -math.inf
        for edge_id in sorted(unresolved):
            after_repair_failed = sorted(unresolved - {edge_id})
            outage = utility_outage_isolation(graph, source_nodes, failed_edges=after_repair_failed)
            lost_nodes = set(outage["deenergized_nodes"])
            served_demand = sum(float(demand_by_node.get(node, 0.0)) for node in graph.adjacency if node not in lost_nodes)
            protected_critical = sum(1 for node in critical_nodes if node not in lost_nodes)
            repair_time = max(0.1, float(repair_time_by_edge.get(edge_id, 1.0)))
            score = (served_demand + 1000.0 * protected_critical) / repair_time
            if score > best_score:
                best_score = score
                best_edge = edge_id

        assert best_edge is not None
        unresolved.remove(best_edge)
        plan.append({"repair_edge_id": best_edge, "priority_score": best_score})

    return {"total_repairs_planned": len(plan), "repair_plan": plan}


def pressure_zone_reconfiguration_planner(
    graph: NetworkGraph,
    source_nodes: list[str],
    max_headloss: float = 10.0,
) -> list[dict[str, Any]]:
    baseline = trace_water_pressure_zones(graph, source_nodes, max_headloss=max_headloss)
    baseline_count = sum(1 for row in baseline if bool(row["within_pressure_zone"]))

    candidate_edges = [
        edge_id
        for edge_id, edge in graph.edge_attributes.items()
        if str(edge.get("device_type", "")).lower() in {"valve", "switch", "tie"}
    ]

    rows: list[dict[str, Any]] = []
    for edge_id in candidate_edges:
        edge = graph.edge_attributes[edge_id]
        state = str(edge.get("state", "open")).lower()
        currently_open = state in {"open", "normally_open", "closed_for_maintenance"}
        simulated_failed = [] if currently_open else [edge_id]
        simulated = _reachable_nodes(graph, source_nodes, failed_edges=simulated_failed)
        delta = len(simulated) - baseline_count
        rows.append(
            {
                "action_edge_id": edge_id,
                "proposed_action": "close" if currently_open else "open",
                "delta_within_pressure_band": delta,
            }
        )

    rows.sort(key=lambda item: (-int(item["delta_within_pressure_band"]), str(item["action_edge_id"])))
    return rows


def pump_station_failure_cascade(
    graph: NetworkGraph,
    pump_nodes: list[str],
    initial_failed_pumps: list[str],
    dependency_map: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    del graph  # graph reserved for future hydraulic coupling
    dependency_map = dependency_map or {}
    failed: set[str] = set(initial_failed_pumps)
    queue: deque[str] = deque(initial_failed_pumps)

    while queue:
        pump = queue.popleft()
        for dependent in dependency_map.get(pump, []):
            if dependent in pump_nodes and dependent not in failed:
                failed.add(dependent)
                queue.append(dependent)

    return {
        "final_failed_count": len(failed),
        "final_failed_pumps": sorted(failed),
    }


def feeder_reconfiguration_optimizer(
    graph: NetworkGraph,
    source_nodes: list[str],
    tie_edge_ids: list[str],
    demand_by_node: dict[str, float] | None = None,
    max_switch_actions: int = 1,
) -> dict[str, Any]:
    demand_by_node = demand_by_node or {}
    if not tie_edge_ids:
        return {"switch_actions": []}

    candidates = outage_restoration_tie_options(
        graph,
        source_nodes=source_nodes,
        affected_nodes=list(graph.adjacency.keys()),
        tie_edge_ids=tie_edge_ids,
    )

    actions: list[dict[str, Any]] = []
    for row in candidates[: max(0, max_switch_actions)]:
        restored_nodes = list(row["restored_nodes"])
        restored_demand = sum(float(demand_by_node.get(node, 0.0)) for node in restored_nodes)
        actions.append(
            {
                "tie_edge_id": row["tie_edge_id"],
                "restored_target_count": row["restored_target_count"],
                "restored_demand": restored_demand,
            }
        )

    actions.sort(key=lambda item: (-float(item["restored_demand"]), str(item["tie_edge_id"])))
    return {"switch_actions": actions}


def resilience_capex_prioritization(
    graph: NetworkGraph,
    source_nodes: list[str],
    demand_by_node: dict[str, float],
    project_candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    baseline_rows = n_minus_one_edge_contingency_screen(graph, source_nodes, demand_by_node=demand_by_node)
    baseline_risk = sum(float(row["lost_demand"]) for row in baseline_rows)

    rows: list[dict[str, Any]] = []
    for candidate in project_candidates:
        project_graph = _graph_with_added_edges(graph, list(candidate.get("add_edges", [])))
        upgraded_rows = n_minus_one_edge_contingency_screen(project_graph, source_nodes, demand_by_node=demand_by_node)
        upgraded_risk = sum(float(row["lost_demand"]) for row in upgraded_rows)
        avoided = max(0.0, baseline_risk - upgraded_risk)
        capex = max(1.0, float(candidate.get("capex_cost", 1.0)))
        rows.append(
            {
                "project_id": str(candidate.get("project_id", "unknown")),
                "capex_cost": capex,
                "risk_avoided": avoided,
                "benefit_cost_ratio": avoided / capex,
            }
        )

    rows.sort(key=lambda item: (-float(item["benefit_cost_ratio"]), -float(item["risk_avoided"]), str(item["project_id"])))
    return rows


def trace_water_pressure_zones(
    graph: NetworkGraph,
    source_nodes: list[str],
    max_headloss: float,
) -> list[dict[str, Any]]:
    if max_headloss < 0:
        raise ValueError("max_headloss must be zero or greater")
    rows = service_area(graph, source_nodes, max_cost=math.inf)
    results: list[dict[str, Any]] = []
    for row in rows:
        headloss = float(row["cost"])
        results.append(
            {
                "node": row["node"],
                "headloss": headloss,
                "within_pressure_zone": headloss <= max_headloss,
            }
        )
    return results


def pipe_break_isolation_zones(graph: NetworkGraph, break_edge_id: str) -> dict[str, Any]:
    edge = graph.edge_attributes.get(break_edge_id, {})
    from_node = str(edge.get("from_node", ""))
    to_node = str(edge.get("to_node", ""))
    reachable_from_upstream = _reachable_nodes(graph, [from_node], failed_edges=[break_edge_id]) if from_node else set()
    reachable_from_downstream = _reachable_nodes(graph, [to_node], failed_edges=[break_edge_id]) if to_node else set()
    affected = sorted(set(graph.adjacency) - reachable_from_upstream.intersection(reachable_from_downstream))
    return {
        "break_edge_id": break_edge_id,
        "affected_nodes": affected,
        "isolation_boundary_nodes": sorted({from_node, to_node} - {""}),
    }


def fire_flow_demand_check(
    graph: NetworkGraph,
    hydrant_nodes: list[str],
    demand_gpm: float,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for hydrant in hydrant_nodes:
        available = 0.0
        for edge in graph.edge_attributes.values():
            if hydrant in {str(edge.get("from_node", "")), str(edge.get("to_node", ""))}:
                capacity = float(edge.get("capacity", 0.0))
                flow = float(edge.get("flow", 0.0))
                available += max(0.0, capacity - flow)
        deficit = max(0.0, float(demand_gpm) - available)
        rows.append(
            {
                "hydrant_node": hydrant,
                "available_gpm": available,
                "demand_gpm": float(demand_gpm),
                "deficit_gpm": deficit,
                "adequate_for_fire_flow": deficit <= 0.0,
            }
        )
    return rows


def gas_pressure_drop_trace(
    graph: NetworkGraph,
    source_node: str,
    inlet_pressure: float,
    drop_per_cost: float = 1.0,
) -> dict[str, Any]:
    rows = service_area(graph, [source_node], max_cost=math.inf)
    profile: list[dict[str, Any]] = []
    for row in rows:
        cost = float(row["cost"])
        pressure = max(0.0, float(inlet_pressure) - cost * drop_per_cost)
        profile.append({"node": row["node"], "pressure": pressure})
    return {"source_node": source_node, "zone_node_count": len(profile), "pressure_profile": profile}


def gas_shutdown_impact(
    graph: NetworkGraph,
    source_nodes: list[str],
    shutdown_edges: list[str],
) -> dict[str, Any]:
    outage = utility_outage_isolation(graph, source_nodes, failed_edges=shutdown_edges)
    return {
        "impacted_count": int(outage["deenergized_count"]),
        "impacted_nodes": list(outage["deenergized_nodes"]),
    }


def gas_odorization_zone_trace(graph: NetworkGraph, odorizer_nodes: list[str]) -> list[dict[str, Any]]:
    zone_map: dict[str, set[str]] = {}
    for odorizer in odorizer_nodes:
        zone_map[odorizer] = _reachable_nodes(graph, [odorizer])

    rows: list[dict[str, Any]] = []
    for odorizer in odorizer_nodes:
        current = zone_map[odorizer]
        overlap = set()
        for other, nodes in zone_map.items():
            if other == odorizer:
                continue
            overlap.update(current.intersection(nodes))
        rows.append(
            {
                "odorizer_node": odorizer,
                "zone_node_count": len(current),
                "overlap_node_count": len(overlap),
            }
        )
    return rows


def gas_regulator_station_isolation(graph: NetworkGraph, regulator_node: str) -> dict[str, Any]:
    neighbors = sorted({step.to_node for step in graph.adjacency.get(regulator_node, [])})
    alternate_available = False
    for left, right in combinations(neighbors, 2):
        blocked = [
            edge_id
            for edge_id, edge in graph.edge_attributes.items()
            if regulator_node in {str(edge.get("from_node", "")), str(edge.get("to_node", ""))}
        ]
        try:
            path = shortest_path(graph, left, right, blocked_edges=blocked)
            if bool(path["reachable"]):
                alternate_available = True
                break
        except KeyError:
            continue

    return {
        "regulator_node": regulator_node,
        "neighbor_count": len(neighbors),
        "alternate_path_available": alternate_available,
    }


def interdependency_cascade_simulation(
    primary_graph: NetworkGraph,
    dependent_graph: NetworkGraph,
    dependency_map: dict[str, list[str]],
    initial_failed_nodes: list[str],
) -> dict[str, Any]:
    del primary_graph
    failed_primary = set(initial_failed_nodes)
    failed_dependent: set[str] = set()

    frontier = deque(initial_failed_nodes)
    while frontier:
        primary_node = frontier.popleft()
        for dependent_node in dependency_map.get(primary_node, []):
            if dependent_node not in failed_dependent and dependent_node in dependent_graph.adjacency:
                failed_dependent.add(dependent_node)

    return {
        "failed_primary_nodes": sorted(failed_primary),
        "failed_dependent_nodes": sorted(failed_dependent),
    }


def infrastructure_age_risk_weighted_routing(graph: NetworkGraph, origin: str, destination: str) -> dict[str, Any]:
    weights = {
        "base": 1.0,
        "failure_risk": 1.5,
        "condition_penalty": 1.0,
    }

    adjusted_edges: dict[str, float] = {}
    for edge_id, edge in graph.edge_attributes.items():
        base_cost = float(edge.get("cost", edge.get("length", 1.0)))
        age = float(edge.get("age_years", edge.get("age", 0.0)))
        design_life = max(1.0, float(edge.get("design_life_years", edge.get("design_life", 50.0))))
        risk_ratio = min(3.0, age / design_life)
        adjusted_edges[edge_id] = base_cost * (1.0 + 0.5 * risk_ratio)

    base_path = shortest_path(graph, origin, destination)
    risk_path = shortest_path(graph, origin, destination, edge_cost_overrides=adjusted_edges)
    if not bool(risk_path["reachable"]):
        return {"path_found": False, "risk_premium": math.inf, "result": risk_path}

    base_cost = float(base_path["total_cost"]) if bool(base_path["reachable"]) else 0.0
    premium = max(0.0, float(risk_path["total_cost"]) - base_cost)
    return {
        "path_found": True,
        "risk_premium": premium,
        "weights": weights,
        "result": risk_path,
    }


def critical_customer_coverage_audit(
    graph: NetworkGraph,
    critical_customer_nodes: list[str],
    supply_nodes: list[str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for customer in critical_customer_nodes:
        single_points: list[str] = []
        for edge_id in graph.edge_attributes:
            outage = utility_outage_isolation(graph, supply_nodes, failed_edges=[edge_id])
            if customer in outage["deenergized_nodes"]:
                single_points.append(edge_id)
        rows.append(
            {
                "critical_customer_node": customer,
                "single_points_of_failure_edges": sorted(single_points),
            }
        )
    return rows


def stormwater_flow_accumulation(graph: NetworkGraph, runoff_by_node: dict[str, float]) -> list[dict[str, Any]]:
    accumulation: dict[str, float] = {node: float(runoff_by_node.get(node, 0.0)) for node in graph.adjacency}
    indegree: dict[str, int] = {node: 0 for node in graph.adjacency}
    for node, steps in graph.adjacency.items():
        for step in steps:
            indegree[step.to_node] = indegree.get(step.to_node, 0) + 1

    queue = deque([node for node, deg in indegree.items() if deg == 0])
    processed = 0
    while queue:
        node = queue.popleft()
        processed += 1
        for step in graph.adjacency.get(node, []):
            accumulation[step.to_node] = accumulation.get(step.to_node, 0.0) + accumulation.get(node, 0.0)
            indegree[step.to_node] = indegree.get(step.to_node, 0) - 1
            if indegree[step.to_node] == 0:
                queue.append(step.to_node)

    if processed < len(graph.adjacency):
        # Cycle-safe fallback for non-DAG networks.
        for _ in range(2):
            for node, steps in graph.adjacency.items():
                for step in steps:
                    accumulation[step.to_node] = max(accumulation.get(step.to_node, 0.0), accumulation.get(node, 0.0))

    rows = [{"node": node, "accumulated_flow": flow} for node, flow in accumulation.items()]
    rows.sort(key=lambda item: str(item["node"]))
    return rows


def detention_basin_overflow_trace(
    graph: NetworkGraph,
    basin_node: str,
    basin_capacity: float,
    inflow: float,
) -> dict[str, Any]:
    del graph
    overflow = max(0.0, float(inflow) - float(basin_capacity))
    return {
        "basin_node": basin_node,
        "overflow_occurring": overflow > 0,
        "overflow_volume": overflow,
    }


def inflow_infiltration_scan(graph: NetworkGraph, infiltration_threshold_ratio: float = 1.25) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for edge_id, edge in graph.edge_attributes.items():
        observed = float(edge.get("observed_flow", edge.get("flow", 0.0)))
        dry = max(1e-9, float(edge.get("dry_weather_flow", observed if observed > 0 else 1.0)))
        ratio = observed / dry
        rows.append(
            {
                "edge_id": edge_id,
                "observed_flow": observed,
                "dry_weather_flow": dry,
                "infiltration_ratio": ratio,
                "flagged": ratio >= infiltration_threshold_ratio,
            }
        )
    return rows


def fiber_splice_node_trace(
    graph: NetworkGraph,
    splice_node: str,
    circuit_endpoints: list[tuple[str, str]] | None = None,
) -> dict[str, Any]:
    if circuit_endpoints:
        traversing = 0
        for origin, destination in circuit_endpoints:
            result = shortest_path(graph, origin, destination)
            if splice_node in result.get("path_nodes", []):
                traversing += 1
    else:
        traversing = len(graph.adjacency.get(splice_node, []))

    return {"splice_node": splice_node, "circuits_traversing_splice": traversing}


def ring_redundancy_check(graph: NetworkGraph, ring_nodes: list[str], hub_node: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for node in ring_nodes:
        if node not in graph.adjacency:
            rows.append({"ring_node": node, "has_redundancy": False})
            continue

        incoming = graph.adjacency.get(node, [])
        successful_paths = 0
        checked_edges: set[str] = set()
        for step in incoming:
            if step.edge_id in checked_edges:
                continue
            checked_edges.add(step.edge_id)
            result = shortest_path(graph, node, hub_node, blocked_edges=[step.edge_id])
            if bool(result["reachable"]):
                successful_paths += 1

        rows.append({"ring_node": node, "has_redundancy": successful_paths >= 1 and len(checked_edges) >= 2})

    return rows


def fiber_cut_impact_matrix(
    graph: NetworkGraph,
    cut_candidate_edges: list[str],
    circuit_endpoints: list[tuple[str, str]],
) -> list[dict[str, Any]]:
    baseline: dict[tuple[str, str], bool] = {}
    for origin, destination in circuit_endpoints:
        baseline[(origin, destination)] = bool(shortest_path(graph, origin, destination)["reachable"])

    rows: list[dict[str, Any]] = []
    for cut_edge in cut_candidate_edges:
        impacted = 0
        for origin, destination in circuit_endpoints:
            result = shortest_path(graph, origin, destination, blocked_edges=[cut_edge])
            reachable = bool(result["reachable"])
            if baseline[(origin, destination)] and not reachable:
                impacted += 1
        rows.append({"cut_edge_id": cut_edge, "circuits_impacted": impacted})

    rows.sort(key=lambda item: (-int(item["circuits_impacted"]), str(item["cut_edge_id"])))
    return rows


def criticality_ranking_by_node_removal(
    graph: NetworkGraph,
    source_nodes: list[str] | None = None,
    demand_by_node: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    if source_nodes is None:
        source_nodes = [sorted(graph.adjacency.keys())[0]] if graph.adjacency else []
    demand_by_node = demand_by_node or {node: 1.0 for node in graph.adjacency}

    rows: list[dict[str, Any]] = []
    for node in graph.adjacency:
        failed_edges = [
            edge_id
            for edge_id, edge in graph.edge_attributes.items()
            if node in {str(edge.get("from_node", "")), str(edge.get("to_node", ""))}
        ]
        outage = utility_outage_isolation(graph, source_nodes, failed_edges=failed_edges)
        lost_demand = sum(float(demand_by_node.get(n, 0.0)) for n in outage["deenergized_nodes"])
        rows.append({"node": node, "lost_demand": lost_demand})

    rows.sort(key=lambda item: (-float(item["lost_demand"]), str(item["node"])))
    return rows
