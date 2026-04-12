"""Network allocation: constrained flow assignment and capacity-aware routing."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

from .core import NetworkGraph, _as_non_negative
from .routing import _dijkstra, shortest_path
from ..equations import utility_capacity_stress_index, utility_service_deficit

if TYPE_CHECKING:
    from collections.abc import Sequence


def constrained_flow_assignment(
    graph: NetworkGraph,
    od_demands: list[tuple[str, str, float]],
    capacity_field: str = "capacity",
    max_iterations: int = 8,
    overflow_penalty: float = 3.0,
    convergence_tolerance: float = 1e-6,
) -> dict[str, Any]:
    """Iterative assignment with congestion penalties to emulate capacity-aware rerouting."""
    if max_iterations <= 0:
        raise ValueError("max_iterations must be greater than zero")
    if overflow_penalty < 0:
        raise ValueError("overflow_penalty must be zero or greater")

    base_costs = {
        edge_id: _as_non_negative(edge.get("cost", edge.get("length", 1.0)), "cost")
        for edge_id, edge in graph.edge_attributes.items()
    }
    edge_costs = dict(base_costs)
    edge_loads: dict[str, float] = {edge_id: 0.0 for edge_id in graph.edge_attributes}
    unmet_demand = 0.0

    converged = False
    iterations_run = 0
    for iteration in range(1, max_iterations + 1):
        iterations_run = iteration
        edge_loads = {edge_id: 0.0 for edge_id in graph.edge_attributes}
        unmet_demand = 0.0

        for origin, destination, demand in od_demands:
            demand_value = max(0.0, float(demand))
            if demand_value == 0:
                continue
            try:
                path = shortest_path(
                    graph,
                    origin=origin,
                    destination=destination,
                    edge_cost_overrides=edge_costs,
                )
            except KeyError:
                unmet_demand += demand_value
                continue

            if not bool(path["reachable"]):
                unmet_demand += demand_value
                continue

            for edge_id in list(path.get("path_edges", [])):
                edge_loads[edge_id] += demand_value

        max_overflow = 0.0
        next_costs: dict[str, float] = {}
        for edge_id, edge in graph.edge_attributes.items():
            capacity = _as_non_negative(edge.get(capacity_field, math.inf), capacity_field)
            load = edge_loads[edge_id]
            base = base_costs[edge_id]
            if not math.isfinite(capacity) or capacity == 0:
                next_costs[edge_id] = base
                continue
            stress_ratio = utility_capacity_stress_index(load, capacity, stress_power=1.0)
            overflow = max(0.0, stress_ratio - 1.0)
            max_overflow = max(max_overflow, overflow)
            next_costs[edge_id] = base * (1.0 + overflow_penalty * overflow)

        edge_costs = next_costs
        if max_overflow <= convergence_tolerance:
            converged = True
            break

    edge_rows: list[dict[str, Any]] = []
    for edge_id, edge in graph.edge_attributes.items():
        capacity = _as_non_negative(edge.get(capacity_field, math.inf), capacity_field)
        load = edge_loads[edge_id]
        stress = 0.0 if not math.isfinite(capacity) else utility_capacity_stress_index(load, capacity, stress_power=1.0)
        edge_rows.append(
            {
                "edge_id": edge_id,
                "from_node": edge["from_node"],
                "to_node": edge["to_node"],
                "capacity": capacity,
                "flow_load": load,
                "stress_ratio": stress,
                "assigned_cost": edge_costs[edge_id],
            }
        )
    edge_rows.sort(key=lambda item: (-float(item["stress_ratio"]), str(item["edge_id"])))

    return {
        "iterations": iterations_run,
        "converged": converged,
        "unmet_demand": unmet_demand,
        "edge_results": edge_rows,
    }


def capacity_constrained_od_assignment(
    graph: NetworkGraph,
    od_demands: list[tuple[str, str, float]],
    capacity_field: str = "capacity",
    max_rounds: int = 6,
    blocked_edges: Sequence[str] | None = None,
    edge_cost_overrides: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Assign OD demand with capacity spillover using residual edge capacities.

    Demands are routed in rounds and can be partially served based on bottleneck
    residual capacity along each selected path.
    """
    if max_rounds <= 0:
        raise ValueError("max_rounds must be greater than zero")

    blocked = set(blocked_edges or [])
    residual_capacity: dict[str, float] = {}
    for edge_id, edge in graph.edge_attributes.items():
        capacity = _as_non_negative(edge.get(capacity_field, math.inf), capacity_field)
        residual_capacity[edge_id] = capacity

    requests: list[dict[str, Any]] = []
    for origin, destination, demand in od_demands:
        demand_value = max(0.0, float(demand))
        requests.append(
            {
                "origin": origin,
                "destination": destination,
                "requested": demand_value,
                "remaining": demand_value,
                "delivered": 0.0,
                "segments": [],
            }
        )

    for round_index in range(1, max_rounds + 1):
        delivered_this_round = 0.0
        for request in requests:
            remaining = float(request["remaining"])
            if remaining <= 0:
                continue

            dynamic_blocked = set(blocked)
            dynamic_blocked.update(
                edge_id for edge_id, cap in residual_capacity.items() if cap <= 1e-12
            )

            try:
                path = shortest_path(
                    graph,
                    origin=str(request["origin"]),
                    destination=str(request["destination"]),
                    blocked_edges=list(dynamic_blocked),
                    edge_cost_overrides=edge_cost_overrides,
                )
            except KeyError:
                continue

            if not bool(path["reachable"]):
                continue

            path_edges = [str(edge_id) for edge_id in list(path.get("path_edges", []))]
            if not path_edges:
                continue

            bottleneck = min(residual_capacity.get(edge_id, 0.0) for edge_id in path_edges)
            deliverable = min(remaining, max(0.0, bottleneck))
            if deliverable <= 0:
                continue

            for edge_id in path_edges:
                if math.isfinite(residual_capacity[edge_id]):
                    residual_capacity[edge_id] = max(0.0, residual_capacity[edge_id] - deliverable)

            request["remaining"] = remaining - deliverable
            request["delivered"] = float(request["delivered"]) + deliverable
            request["segments"].append(
                {
                    "round": round_index,
                    "delivered": deliverable,
                    "path_edges": path_edges,
                    "path_nodes": list(path.get("path_nodes", [])),
                    "total_cost": float(path["total_cost"]),
                }
            )
            delivered_this_round += deliverable

        if delivered_this_round <= 1e-12:
            break

    od_results: list[dict[str, Any]] = []
    for request in requests:
        requested = float(request["requested"])
        delivered = float(request["delivered"])
        unmet = max(0.0, requested - delivered)
        od_results.append(
            {
                "origin": request["origin"],
                "destination": request["destination"],
                "requested": requested,
                "delivered": delivered,
                "unmet": unmet,
                "service_deficit": utility_service_deficit(requested, delivered),
                "segments": list(request["segments"]),
            }
        )

    edge_results: list[dict[str, Any]] = []
    for edge_id, edge in graph.edge_attributes.items():
        capacity = _as_non_negative(edge.get(capacity_field, math.inf), capacity_field)
        residual = residual_capacity[edge_id]
        used = 0.0 if not math.isfinite(capacity) else max(0.0, capacity - residual)
        stress = 0.0 if not math.isfinite(capacity) else utility_capacity_stress_index(used, capacity, stress_power=1.0)
        edge_results.append(
            {
                "edge_id": edge_id,
                "from_node": edge["from_node"],
                "to_node": edge["to_node"],
                "capacity": capacity,
                "used_capacity": used,
                "residual_capacity": residual,
                "stress_ratio": stress,
            }
        )
    edge_results.sort(key=lambda item: (-float(item["stress_ratio"]), str(item["edge_id"])))

    total_requested = sum(float(item["requested"]) for item in od_results)
    total_delivered = sum(float(item["delivered"]) for item in od_results)
    return {
        "od_results": od_results,
        "edge_results": edge_results,
        "total_requested": total_requested,
        "total_delivered": total_delivered,
        "total_unmet": max(0.0, total_requested - total_delivered),
    }
