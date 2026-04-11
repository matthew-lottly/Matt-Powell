from __future__ import annotations

import math
from dataclasses import dataclass
from heapq import heappop, heappush
from itertools import combinations
from typing import TYPE_CHECKING, Any, TypedDict

from .equations import utility_capacity_stress_index, utility_headloss_hazen_williams, utility_service_deficit

if TYPE_CHECKING:
    from collections.abc import Sequence


class NetworkEdge(TypedDict, total=False):
    """Extensible typed dictionary for network edge attributes.

    Common fields are defined below; additional domain-specific fields
    can be added as needed by analysis functions. All fields are optional
    and allow custom attributes to flow through the system.
    """
    edge_id: str
    from_node: str
    to_node: str
    cost: float
    length: float
    capacity: float
    flow: float
    load: float
    device_type: str
    state: str
    bidirectional: bool
    congestion: float
    slope: float
    failure_risk: float
    condition: float
    # Domain-specific utility fields
    diameter: float
    age: float
    design_life: float
    pressure: float
    headloss: float
    customers: int
    # Reserved for additional field names passed at runtime
    # (users may add any other field name with Any value)


@dataclass(frozen=True)
class Traversal:
    edge_id: str
    from_node: str
    to_node: str
    cost: float


@dataclass
class NetworkGraph:
    directed: bool
    adjacency: dict[str, list[Traversal]]
    edge_attributes: dict[str, NetworkEdge]

    @property
    def nodes(self) -> set[str]:
        return set(self.adjacency.keys())


def _as_node(value: object, field: str) -> str:
    node = str(value)
    if not node:
        raise ValueError(f"{field} must be a non-empty string")
    return node


def _as_non_negative(value: Any, field: str) -> float:
    resolved = float(value)
    if resolved < 0:
        raise ValueError(f"{field} must be zero or greater")
    return resolved


def build_network_graph(
    edges: list[NetworkEdge],
    directed: bool = False,
    cost_field: str = "cost",
    capacity_field: str = "capacity",
) -> NetworkGraph:
    """Build an adjacency graph from edge records.

    For undirected networks, each edge is inserted in both directions.
    For directed networks, reverse traversal can be forced per-edge by setting
    ``bidirectional=True``.
    """
    adjacency: dict[str, list[Traversal]] = {}
    edge_attributes: dict[str, NetworkEdge] = {}

    for index, edge in enumerate(edges):
        from_node = _as_node(edge.get("from_node"), "from_node")
        to_node = _as_node(edge.get("to_node"), "to_node")

        if cost_field in edge:
            cost = _as_non_negative(edge[cost_field], cost_field)
        elif "length" in edge:
            cost = _as_non_negative(edge["length"], "length")
        else:
            cost = 1.0

        capacity = _as_non_negative(edge.get(capacity_field, math.inf), capacity_field)
        edge_id = str(edge.get("edge_id", f"edge-{index}"))
        resolved_edge: NetworkEdge = dict(edge)
        resolved_edge["edge_id"] = edge_id
        resolved_edge["from_node"] = from_node
        resolved_edge["to_node"] = to_node
        resolved_edge[cost_field] = cost
        resolved_edge[capacity_field] = capacity
        resolved_edge["bidirectional"] = bool(edge.get("bidirectional", not directed))
        if "length" in edge:
            resolved_edge["length"] = _as_non_negative(edge["length"], "length")
        edge_attributes[edge_id] = resolved_edge

        adjacency.setdefault(from_node, []).append(
            Traversal(edge_id=edge_id, from_node=from_node, to_node=to_node, cost=cost)
        )
        adjacency.setdefault(to_node, [])

        reverse_allowed = (not directed) or bool(edge.get("bidirectional", False))
        if reverse_allowed:
            adjacency[to_node].append(
                Traversal(edge_id=edge_id, from_node=to_node, to_node=from_node, cost=cost)
            )

    return NetworkGraph(directed=directed, adjacency=adjacency, edge_attributes=edge_attributes)


def _dijkstra(
    graph: NetworkGraph,
    origins: list[str],
    max_cost: float | None = None,
    blocked_edges: set[str] | None = None,
    edge_cost_overrides: dict[str, float] | None = None,
) -> tuple[dict[str, float], dict[str, str], dict[str, str], dict[str, str]]:
    distances: dict[str, float] = {}
    previous_node: dict[str, str] = {}
    previous_edge: dict[str, str] = {}
    source_for_node: dict[str, str] = {}
    queue: list[tuple[float, str]] = []

    for origin in origins:
        if origin not in graph.adjacency:
            continue
        distances[origin] = 0.0
        source_for_node[origin] = origin
        heappush(queue, (0.0, origin))

    while queue:
        current_cost, current_node = heappop(queue)
        if current_cost > distances.get(current_node, math.inf):
            continue
        if max_cost is not None and current_cost > max_cost:
            continue

        for step in graph.adjacency.get(current_node, []):
            if blocked_edges is not None and step.edge_id in blocked_edges:
                continue
            step_cost = step.cost if edge_cost_overrides is None else edge_cost_overrides.get(step.edge_id, step.cost)
            next_cost = current_cost + step_cost
            if max_cost is not None and next_cost > max_cost:
                continue
            if next_cost >= distances.get(step.to_node, math.inf):
                continue
            distances[step.to_node] = next_cost
            previous_node[step.to_node] = current_node
            previous_edge[step.to_node] = step.edge_id
            source_for_node[step.to_node] = source_for_node[current_node]
            heappush(queue, (next_cost, step.to_node))

    return distances, previous_node, previous_edge, source_for_node


def shortest_path(
    graph: NetworkGraph,
    origin: str,
    destination: str,
    max_cost: float | None = None,
    blocked_edges: Sequence[str] | None = None,
    edge_cost_overrides: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Compute shortest path between two nodes with Dijkstra."""
    if origin not in graph.adjacency:
        raise KeyError(f"origin node '{origin}' is not present in the network")
    if destination not in graph.adjacency:
        raise KeyError(f"destination node '{destination}' is not present in the network")

    blocked = set(blocked_edges or [])
    distances, previous_node, previous_edge, _ = _dijkstra(
        graph,
        origins=[origin],
        max_cost=max_cost,
        blocked_edges=blocked,
        edge_cost_overrides=edge_cost_overrides,
    )
    if destination not in distances:
        return {
            "origin": origin,
            "destination": destination,
            "reachable": False,
            "total_cost": math.inf,
            "path_nodes": [],
            "path_edges": [],
            "hop_count": 0,
        }

    nodes = [destination]
    edges: list[str] = []
    current = destination
    while current != origin:
        edges.append(previous_edge[current])
        current = previous_node[current]
        nodes.append(current)

    nodes.reverse()
    edges.reverse()
    return {
        "origin": origin,
        "destination": destination,
        "reachable": True,
        "total_cost": distances[destination],
        "path_nodes": nodes,
        "path_edges": edges,
        "hop_count": len(edges),
    }


def service_area(
    graph: NetworkGraph,
    origins: list[str],
    max_cost: float,
    blocked_edges: Sequence[str] | None = None,
    edge_cost_overrides: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    """Return all nodes reachable from one or more origins within max_cost."""
    if max_cost < 0:
        raise ValueError("max_cost must be zero or greater")

    blocked = set(blocked_edges or [])
    distances, _, _, source_for_node = _dijkstra(
        graph,
        origins=origins,
        max_cost=max_cost,
        blocked_edges=blocked,
        edge_cost_overrides=edge_cost_overrides,
    )
    records = [
        {
            "node": node,
            "assigned_origin": source_for_node[node],
            "cost": cost,
            "within_service_area": cost <= max_cost,
        }
        for node, cost in distances.items()
    ]
    records.sort(key=lambda item: (float(item["cost"]), str(item["node"])))
    return records


def od_cost_matrix(
    graph: NetworkGraph,
    origins: list[str],
    destinations: list[str],
    max_cost: float | None = None,
    blocked_edges: Sequence[str] | None = None,
    edge_cost_overrides: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    """Compute an origin-destination least-cost matrix."""
    rows: list[dict[str, Any]] = []
    blocked = set(blocked_edges or [])
    for origin in origins:
        if origin not in graph.adjacency:
            continue
        distances, _, _, _ = _dijkstra(
            graph,
            origins=[origin],
            max_cost=max_cost,
            blocked_edges=blocked,
            edge_cost_overrides=edge_cost_overrides,
        )
        for destination in destinations:
            total_cost = distances.get(destination, math.inf)
            rows.append(
                {
                    "origin": origin,
                    "destination": destination,
                    "reachable": math.isfinite(total_cost),
                    "least_cost": total_cost,
                }
            )
    rows.sort(key=lambda item: (str(item["origin"]), str(item["destination"])))
    return rows


def allocate_demand_to_supply(
    graph: NetworkGraph,
    supply_by_node: dict[str, float],
    demand_by_node: dict[str, float],
    max_cost: float | None = None,
    blocked_edges: Sequence[str] | None = None,
    edge_cost_overrides: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    """Assign each demand node to the closest reachable supply node."""
    supply_nodes = [node for node, supply in supply_by_node.items() if supply > 0]
    if not supply_nodes:
        raise ValueError("supply_by_node must contain at least one positive supply")

    blocked = set(blocked_edges or [])
    distances, _, _, source_for_node = _dijkstra(
        graph,
        origins=supply_nodes,
        max_cost=max_cost,
        blocked_edges=blocked,
        edge_cost_overrides=edge_cost_overrides,
    )
    rows: list[dict[str, Any]] = []
    for demand_node, demand in demand_by_node.items():
        demand_value = max(0.0, float(demand))
        if demand_value == 0:
            continue

        distance_value = distances.get(demand_node, math.inf)
        assigned_supply = source_for_node.get(demand_node)
        served = math.isfinite(distance_value) and assigned_supply is not None
        delivered = demand_value if served else 0.0
        rows.append(
            {
                "demand_node": demand_node,
                "assigned_supply_node": assigned_supply,
                "least_cost": distance_value,
                "demand": demand_value,
                "delivered": delivered,
                "service_deficit": utility_service_deficit(demand_value, delivered),
                "reachable": served,
            }
        )

    rows.sort(key=lambda item: str(item["demand_node"]))
    return rows


def utility_bottlenecks(
    graph: NetworkGraph,
    od_demands: list[tuple[str, str, float]],
    capacity_field: str = "capacity",
    blocked_edges: Sequence[str] | None = None,
    edge_cost_overrides: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    """Estimate edge stress by loading shortest paths for OD demand pairs.

    OD pairs are grouped by origin so that a single Dijkstra tree is reused for
    all destinations sharing the same origin, avoiding redundant graph traversals.
    """
    edge_loads: dict[str, float] = {edge_id: 0.0 for edge_id in graph.edge_attributes}

    blocked = set(blocked_edges or [])

    # Group demands by origin to batch Dijkstra calls.
    origin_groups: dict[str, list[tuple[str, float]]] = {}
    for origin, destination, demand in od_demands:
        demand_value = max(0.0, float(demand))
        if demand_value == 0:
            continue
        origin_groups.setdefault(origin, []).append((destination, demand_value))

    for origin, dest_demands in origin_groups.items():
        if origin not in graph.adjacency:
            continue
        distances, prev_node, prev_edge, _ = _dijkstra(
            graph,
            origins=[origin],
            max_cost=None,
            blocked_edges=blocked,
            edge_cost_overrides=edge_cost_overrides,
        )
        for destination, demand_value in dest_demands:
            if destination not in distances:
                continue
            # Reconstruct path edges and load demand onto them.
            current = destination
            while current != origin:
                edge_id = prev_edge.get(current)
                if edge_id is None:
                    break
                edge_loads[edge_id] += demand_value
                current = prev_node[current]

    rows: list[dict[str, Any]] = []
    for edge_id, edge in graph.edge_attributes.items():
        capacity = _as_non_negative(edge.get(capacity_field, math.inf), capacity_field)
        load = edge_loads[edge_id]
        stress = 0.0 if not math.isfinite(capacity) else utility_capacity_stress_index(load, capacity)
        rows.append(
            {
                "edge_id": edge_id,
                "from_node": edge["from_node"],
                "to_node": edge["to_node"],
                "flow_load": load,
                "capacity": capacity,
                "capacity_stress": stress,
            }
        )

    rows.sort(key=lambda item: (-float(item["capacity_stress"]), str(item["edge_id"])))
    return rows


def analyze_network_topology(graph: NetworkGraph) -> dict[str, Any]:
    """Audit network topology for connectivity and data-quality issues."""
    node_set = set(graph.adjacency)
    in_degree: dict[str, int] = {node: 0 for node in node_set}
    out_degree: dict[str, int] = {node: 0 for node in node_set}
    self_loops: list[str] = []
    pair_counts: dict[tuple[str, str], int] = {}

    undirected_neighbors: dict[str, set[str]] = {node: set() for node in node_set}
    for edge_id, edge in graph.edge_attributes.items():
        from_node = str(edge["from_node"])
        to_node = str(edge["to_node"])
        out_degree[from_node] = out_degree.get(from_node, 0) + 1
        in_degree[to_node] = in_degree.get(to_node, 0) + 1
        undirected_neighbors.setdefault(from_node, set()).add(to_node)
        undirected_neighbors.setdefault(to_node, set()).add(from_node)

        if graph.directed:
            key = (from_node, to_node)
        else:
            ordered_left, ordered_right = sorted((from_node, to_node))
            key = (ordered_left, ordered_right)
        pair_counts[key] = pair_counts.get(key, 0) + 1
        if from_node == to_node:
            self_loops.append(edge_id)

    duplicate_edge_pairs = [pair for pair, count in pair_counts.items() if count > 1]
    isolated_nodes = sorted(node for node in node_set if not undirected_neighbors.get(node))
    dangling_nodes = sorted(
        node
        for node in node_set
        if len(undirected_neighbors.get(node, set())) == 1
    )

    remaining = set(node_set)
    components: list[list[str]] = []
    while remaining:
        seed = next(iter(remaining))
        stack = [seed]
        component: list[str] = []
        while stack:
            node = stack.pop()
            if node not in remaining:
                continue
            remaining.remove(node)
            component.append(node)
            stack.extend(neighbor for neighbor in undirected_neighbors.get(node, set()) if neighbor in remaining)
        components.append(sorted(component))

    components.sort(key=lambda comp: (-len(comp), comp[0] if comp else ""))
    return {
        "node_count": len(node_set),
        "edge_count": len(graph.edge_attributes),
        "isolated_nodes": isolated_nodes,
        "dangling_nodes": dangling_nodes,
        "self_loop_edge_ids": sorted(self_loops),
        "duplicate_edge_pairs": duplicate_edge_pairs,
        "connected_components": components,
        "component_count": len(components),
        "largest_component_size": len(components[0]) if components else 0,
        "in_degree": in_degree,
        "out_degree": out_degree,
    }


def edge_impedance_cost(
    edge: NetworkEdge,
    weights: dict[str, float] | None = None,
    base_cost_field: str = "cost",
) -> float:
    """Build configurable impedance from edge attributes for multi-criteria routing."""
    default_weights = {
        "base": 1.0,
        "length": 0.0,
        "congestion": 0.0,
        "slope": 0.0,
        "failure_risk": 0.0,
        "condition_penalty": 0.0,
    }
    resolved_weights = {**default_weights, **(weights or {})}
    base_cost = _as_non_negative(edge.get(base_cost_field, edge.get("length", 1.0)), base_cost_field)
    length = _as_non_negative(edge.get("length", base_cost), "length")
    congestion = _as_non_negative(edge.get("congestion", 0.0), "congestion")
    slope = _as_non_negative(edge.get("slope", 0.0), "slope")
    failure_risk = _as_non_negative(edge.get("failure_risk", 0.0), "failure_risk")
    condition = min(1.0, max(0.0, _as_non_negative(edge.get("condition", 1.0), "condition")))

    return (
        resolved_weights["base"] * base_cost
        + resolved_weights["length"] * length
        + resolved_weights["congestion"] * base_cost * congestion
        + resolved_weights["slope"] * base_cost * slope
        + resolved_weights["failure_risk"] * base_cost * failure_risk
        + resolved_weights["condition_penalty"] * base_cost * (1.0 - condition)
    )


def multi_criteria_shortest_path(
    graph: NetworkGraph,
    origin: str,
    destination: str,
    weights: dict[str, float] | None = None,
    max_cost: float | None = None,
    blocked_edges: Sequence[str] | None = None,
    base_cost_field: str = "cost",
) -> dict[str, Any]:
    """Shortest path where impedance is computed from multiple edge factors."""
    overrides = {
        edge_id: edge_impedance_cost(edge, weights=weights, base_cost_field=base_cost_field)
        for edge_id, edge in graph.edge_attributes.items()
    }
    result = shortest_path(
        graph,
        origin=origin,
        destination=destination,
        max_cost=max_cost,
        blocked_edges=blocked_edges,
        edge_cost_overrides=overrides,
    )
    result["impedance_weights"] = dict(weights or {})
    result["cost_mode"] = "multi_criteria"
    return result


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


def _device_state_blocked_edges(
    graph: NetworkGraph,
    device_rules: dict[str, dict[str, bool]] | None = None,
    device_type_field: str = "device_type",
    state_field: str = "state",
    unknown_state_policy: str = "passable",
) -> set[str]:
    if unknown_state_policy not in {"passable", "blocked"}:
        raise ValueError("unknown_state_policy must be 'passable' or 'blocked'")

    default_rules: dict[str, dict[str, bool]] = {
        "switch": {"open": True, "closed": False, "unknown": unknown_state_policy == "blocked"},
        "breaker": {"open": True, "closed": False, "unknown": unknown_state_policy == "blocked"},
        "valve": {"closed": True, "open": False, "unknown": unknown_state_policy == "blocked"},
    }
    rules = {**default_rules, **(device_rules or {})}

    blocked: set[str] = set()
    for edge_id, edge in graph.edge_attributes.items():
        raw_type = str(edge.get(device_type_field, "")).strip().lower()
        raw_state = str(edge.get(state_field, "")).strip().lower()
        if not raw_type or not raw_state:
            continue
        state_map = rules.get(raw_type)
        if state_map is None:
            continue
        blocked_flag = state_map.get(raw_state)
        if blocked_flag is None:
            blocked_flag = unknown_state_policy == "blocked"
        if blocked_flag:
            blocked.add(edge_id)
    return blocked


def trace_electric_feeder(
    graph: NetworkGraph,
    source_nodes: Sequence[str],
    open_switch_edges: Sequence[str] | None = None,
    device_rules: dict[str, dict[str, bool]] | None = None,
    device_type_field: str = "device_type",
    state_field: str = "state",
    unknown_state_policy: str = "passable",
    _precomputed_device_blocked: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Return energized/deenergized nodes after applying switch states."""
    blocked = set(open_switch_edges or [])
    if _precomputed_device_blocked is not None:
        blocked.update(_precomputed_device_blocked)
    else:
        blocked.update(
            _device_state_blocked_edges(
                graph,
                device_rules=device_rules,
                device_type_field=device_type_field,
                state_field=state_field,
                unknown_state_policy=unknown_state_policy,
            )
        )
    distances, _, _, source_for_node = _dijkstra(graph, origins=list(source_nodes), blocked_edges=blocked)
    rows: list[dict[str, Any]] = []
    for node in sorted(graph.nodes):
        energized = node in distances
        rows.append(
            {
                "node": node,
                "energized": energized,
                "source_node": source_for_node.get(node),
                "electrical_distance": distances.get(node, math.inf),
            }
        )
    return rows


def utility_outage_isolation(
    graph: NetworkGraph,
    source_nodes: Sequence[str],
    failed_edges: Sequence[str],
    critical_nodes: Sequence[str] | None = None,
    device_rules: dict[str, dict[str, bool]] | None = None,
    device_type_field: str = "device_type",
    state_field: str = "state",
    unknown_state_policy: str = "passable",
    _precomputed_device_blocked: set[str] | None = None,
) -> dict[str, Any]:
    """Compute outage impact from failed segments."""
    blocked = set(failed_edges)
    traces = trace_electric_feeder(
        graph,
        source_nodes=source_nodes,
        open_switch_edges=list(blocked),
        device_rules=device_rules,
        device_type_field=device_type_field,
        state_field=state_field,
        unknown_state_policy=unknown_state_policy,
        _precomputed_device_blocked=_precomputed_device_blocked,
    )
    deenergized = [row["node"] for row in traces if not bool(row["energized"])]
    supplied = [row["node"] for row in traces if bool(row["energized"])]
    critical = list(critical_nodes or [])
    critical_impacted = sorted(node for node in critical if node in deenergized)
    return {
        "failed_edges": sorted(blocked),
        "supplied_nodes": sorted(supplied),
        "supplied_count": len(supplied),
        "deenergized_nodes": sorted(deenergized),
        "deenergized_count": len(deenergized),
        "critical_impacted_nodes": critical_impacted,
        "critical_impacted_count": len(critical_impacted),
    }


def trace_water_pressure_zones(
    graph: NetworkGraph,
    source_nodes: Sequence[str],
    max_headloss: float,
    flow_by_edge: dict[str, float] | None = None,
    diameter_by_edge: dict[str, float] | None = None,
    roughness_coefficient: float = 130.0,
) -> list[dict[str, Any]]:
    """Trace water service zones using cumulative headloss as impedance."""
    if max_headloss < 0:
        raise ValueError("max_headloss must be zero or greater")

    flow_lookup = flow_by_edge or {}
    diameter_lookup = diameter_by_edge or {}
    overrides: dict[str, float] = {}
    for edge_id, edge in graph.edge_attributes.items():
        length = _as_non_negative(edge.get("length", edge.get("cost", 1.0)), "length")
        flow = _as_non_negative(flow_lookup.get(edge_id, 1.0), "flow")
        diameter = _as_non_negative(diameter_lookup.get(edge_id, 0.5), "diameter")
        if diameter == 0:
            diameter = 0.5
        overrides[edge_id] = utility_headloss_hazen_williams(
            length=length,
            flow=flow,
            diameter=diameter,
            roughness_coefficient=roughness_coefficient,
        )

    distances, _, _, source_for_node = _dijkstra(
        graph,
        origins=list(source_nodes),
        max_cost=max_headloss,
        edge_cost_overrides=overrides,
    )

    rows = [
        {
            "node": node,
            "source_node": source_for_node[node],
            "cumulative_headloss": distance,
            "within_pressure_zone": distance <= max_headloss,
        }
        for node, distance in distances.items()
    ]
    rows.sort(key=lambda item: (float(item["cumulative_headloss"]), str(item["node"])))
    return rows


def gas_shutdown_impact(
    graph: NetworkGraph,
    source_nodes: Sequence[str],
    shutdown_edges: Sequence[str],
    device_rules: dict[str, dict[str, bool]] | None = None,
    device_type_field: str = "device_type",
    state_field: str = "state",
    unknown_state_policy: str = "passable",
) -> dict[str, Any]:
    """Estimate impacted gas network nodes after planned shutdown segments."""
    blocked = set(shutdown_edges)
    blocked.update(
        _device_state_blocked_edges(
            graph,
            device_rules=device_rules,
            device_type_field=device_type_field,
            state_field=state_field,
            unknown_state_policy=unknown_state_policy,
        )
    )
    distances, _, _, _ = _dijkstra(graph, origins=list(source_nodes), blocked_edges=blocked)
    supplied_nodes = sorted(distances.keys())
    impacted_nodes = sorted(node for node in graph.nodes if node not in distances)
    return {
        "shutdown_edges": sorted(blocked),
        "supplied_nodes": supplied_nodes,
        "impacted_nodes": impacted_nodes,
        "impacted_count": len(impacted_nodes),
    }


def run_utility_scenarios(
    graph: NetworkGraph,
    source_nodes: Sequence[str],
    critical_nodes: Sequence[str] | None = None,
    outage_edges: Sequence[str] | None = None,
    restoration_edges: Sequence[str] | None = None,
    candidate_critical_edges: Sequence[str] | None = None,
    static_blocked_edges: Sequence[str] | None = None,
    device_rules: dict[str, dict[str, bool]] | None = None,
    device_type_field: str = "device_type",
    state_field: str = "state",
    unknown_state_policy: str = "passable",
) -> dict[str, Any]:
    """Run baseline, outage, and restoration snapshots with deltas and rankings.

    Parameters
    ----------
    graph:
        Pre-built network graph.
    source_nodes:
        Starting supply nodes (substations, sources, etc.).
    critical_nodes:
        Nodes whose outage impact is tracked separately (hospitals, pumping
        stations, etc.).
    outage_edges:
        Edge IDs that fail in the outage scenario.
    restoration_edges:
        Subset of outage_edges restored in the restoration scenario.
    candidate_critical_edges:
        Edges scored for criticality ranking.  Defaults to all graph edges.
    static_blocked_edges:
        Edges permanently blocked regardless of scenario (e.g. normally-open
        tie switches that are never closed in this study).
    device_rules:
        Mapping of ``{device_type: {state: blocked}}`` overriding the default
        switch/valve blocking logic for all three snapshots.
    device_type_field:
        Edge attribute key holding the device type string.
    state_field:
        Edge attribute key holding the device state string.
    unknown_state_policy:
        ``"block"`` or ``"passable"`` for edges whose state is unrecognised.
    """
    critical = list(critical_nodes or [])
    outage = set(outage_edges or [])
    restoration = set(restoration_edges or [])
    static_blocked = set(static_blocked_edges or [])
    restored_blocked = (outage - restoration) | static_blocked

    # Pre-compute device-blocked edges once instead of O(E+N) redundant scans.
    _device_blocked = _device_state_blocked_edges(
        graph,
        device_rules=device_rules,
        device_type_field=device_type_field,
        state_field=state_field,
        unknown_state_policy=unknown_state_policy,
    )

    _shared_kw: dict[str, Any] = dict(
        device_rules=device_rules,
        device_type_field=device_type_field,
        state_field=state_field,
        unknown_state_policy=unknown_state_policy,
        _precomputed_device_blocked=_device_blocked,
    )

    baseline = utility_outage_isolation(
        graph,
        source_nodes=source_nodes,
        failed_edges=sorted(static_blocked),
        critical_nodes=critical,
        **_shared_kw,
    )
    outage_snapshot = utility_outage_isolation(
        graph,
        source_nodes=source_nodes,
        failed_edges=sorted(outage | static_blocked),
        critical_nodes=critical,
        **_shared_kw,
    )
    restoration_snapshot = utility_outage_isolation(
        graph,
        source_nodes=source_nodes,
        failed_edges=sorted(restored_blocked),
        critical_nodes=critical,
        **_shared_kw,
    )

    def _delta(current: dict[str, Any], previous: dict[str, Any], key: str) -> int:
        return int(current[key]) - int(previous[key])

    tracked_edges = list(candidate_critical_edges or graph.edge_attributes.keys())
    edge_rankings: list[dict[str, Any]] = []
    for edge_id in tracked_edges:
        edge_outage = utility_outage_isolation(
            graph,
            source_nodes=source_nodes,
            failed_edges=sorted({edge_id} | static_blocked),
            critical_nodes=critical,
            **_shared_kw,
        )
        edge_rankings.append(
            {
                "edge_id": edge_id,
                "critical_impacted_count": edge_outage["critical_impacted_count"],
                "deenergized_count": edge_outage["deenergized_count"],
                "supplied_count": edge_outage["supplied_count"],
            }
        )
    edge_rankings.sort(
        key=lambda item: (-int(item["critical_impacted_count"]), -int(item["deenergized_count"]), str(item["edge_id"]))
    )

    node_rankings: list[dict[str, Any]] = []
    node_to_incident_edges: dict[str, set[str]] = {node: set() for node in graph.nodes}
    for edge_id, edge in graph.edge_attributes.items():
        node_to_incident_edges[str(edge["from_node"])].add(edge_id)
        node_to_incident_edges[str(edge["to_node"])].add(edge_id)

    for node in sorted(graph.nodes):
        simulated_failed = sorted(node_to_incident_edges.get(node, set()) | static_blocked)
        node_outage = utility_outage_isolation(
            graph,
            source_nodes=source_nodes,
            failed_edges=simulated_failed,
            critical_nodes=critical,
            **_shared_kw,
        )
        node_rankings.append(
            {
                "node": node,
                "critical_impacted_count": node_outage["critical_impacted_count"],
                "deenergized_count": node_outage["deenergized_count"],
                "supplied_count": node_outage["supplied_count"],
            }
        )
    node_rankings.sort(
        key=lambda item: (-int(item["critical_impacted_count"]), -int(item["deenergized_count"]), str(item["node"]))
    )

    return {
        "baseline": baseline,
        "outage": outage_snapshot,
        "restoration": restoration_snapshot,
        "delta_outage_vs_baseline": {
            "supplied_count": _delta(outage_snapshot, baseline, "supplied_count"),
            "deenergized_count": _delta(outage_snapshot, baseline, "deenergized_count"),
            "critical_impacted_count": _delta(outage_snapshot, baseline, "critical_impacted_count"),
        },
        "delta_restoration_vs_outage": {
            "supplied_count": _delta(restoration_snapshot, outage_snapshot, "supplied_count"),
            "deenergized_count": _delta(restoration_snapshot, outage_snapshot, "deenergized_count"),
            "critical_impacted_count": _delta(restoration_snapshot, outage_snapshot, "critical_impacted_count"),
        },
        "critical_edge_rankings": edge_rankings,
        "critical_node_rankings": node_rankings,
    }


class NetworkRouter:
    """Cached routing helper for repeated OD queries on stable networks."""

    def __init__(self, graph: NetworkGraph) -> None:
        self.graph = graph
        self._distance_cache: dict[str, tuple[dict[str, float], dict[str, str], dict[str, str]]] = {}

    def _origin_tree(self, origin: str) -> tuple[dict[str, float], dict[str, str], dict[str, str]]:
        if origin not in self._distance_cache:
            distances, previous_node, previous_edge, _ = _dijkstra(self.graph, origins=[origin])
            self._distance_cache[origin] = (distances, previous_node, previous_edge)
        return self._distance_cache[origin]

    def shortest_path(self, origin: str, destination: str) -> dict[str, Any]:
        if origin not in self.graph.adjacency:
            raise KeyError(f"origin node '{origin}' is not present in the network")
        if destination not in self.graph.adjacency:
            raise KeyError(f"destination node '{destination}' is not present in the network")

        distances, previous_node, previous_edge = self._origin_tree(origin)
        if destination not in distances:
            return {
                "origin": origin,
                "destination": destination,
                "reachable": False,
                "total_cost": math.inf,
                "path_nodes": [],
                "path_edges": [],
                "hop_count": 0,
            }

        nodes = [destination]
        edges: list[str] = []
        current = destination
        while current != origin:
            edges.append(previous_edge[current])
            current = previous_node[current]
            nodes.append(current)
        nodes.reverse()
        edges.reverse()
        return {
            "origin": origin,
            "destination": destination,
            "reachable": True,
            "total_cost": distances[destination],
            "path_nodes": nodes,
            "path_edges": edges,
            "hop_count": len(edges),
        }

    def od_cost_matrix(self, origins: Sequence[str], destinations: Sequence[str]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for origin in origins:
            if origin not in self.graph.adjacency:
                continue
            distances, _, _ = self._origin_tree(origin)
            for destination in destinations:
                least_cost = distances.get(destination, math.inf)
                rows.append(
                    {
                        "origin": origin,
                        "destination": destination,
                        "reachable": math.isfinite(least_cost),
                        "least_cost": least_cost,
                    }
                )
        rows.sort(key=lambda item: (str(item["origin"]), str(item["destination"])))
        return rows


def build_landmark_index(graph: NetworkGraph, landmarks: Sequence[str]) -> dict[str, dict[str, float]]:
    """Precompute origin-to-node costs for landmark-based lower bounds."""
    index: dict[str, dict[str, float]] = {}
    for landmark in landmarks:
        if landmark not in graph.adjacency:
            continue
        distances, _, _, _ = _dijkstra(graph, origins=[landmark])
        index[landmark] = distances
    return index


def landmark_lower_bound(
    landmark_index: dict[str, dict[str, float]],
    origin: str,
    destination: str,
) -> float:
    """Triangle-inequality lower bound for A* style pruning."""
    lower = 0.0
    for distances in landmark_index.values():
        origin_cost = distances.get(origin)
        destination_cost = distances.get(destination)
        if origin_cost is None or destination_cost is None:
            continue
        lower = max(lower, abs(destination_cost - origin_cost))
    return lower


# ─── ELECTRIC ─────────────────────────────────────────────────────────────────


def criticality_ranking_by_node_removal(
    graph: NetworkGraph,
    max_cost: float = math.inf,
) -> list[dict[str, Any]]:
    """Rank nodes by connectivity loss when each is individually removed.

    For each node, blocks all incident edges then re-runs multi-source Dijkstra
    from the remaining nodes. Returns a list sorted descending by
    ``impact_ratio`` (fraction of node-pairs that lose reachability), with an
    integer ``rank`` field starting at 1.
    """
    all_nodes = sorted(graph.nodes)

    base_dist, _, _, _ = _dijkstra(graph, all_nodes, max_cost, set(), {})
    baseline_count = sum(1 for v in base_dist.values() if v < math.inf)

    results: list[dict[str, Any]] = []
    for node in all_nodes:
        incident: set[str] = set()
        for t in graph.adjacency.get(node, []):
            incident.add(t.edge_id)
        for _, tlist in graph.adjacency.items():
            for t in tlist:
                if t.to_node == node:
                    incident.add(t.edge_id)

        origins = [n for n in all_nodes if n != node]
        if not origins:
            continue

        dist, _, _, _ = _dijkstra(graph, origins, max_cost, incident, {})
        post_count = sum(
            1 for n, v in dist.items() if v < math.inf and n != node
        )
        lost = max(0, baseline_count - 1 - post_count)
        results.append(
            {
                "node": node,
                "baseline_reachable": baseline_count,
                "post_removal_reachable": post_count,
                "lost_nodes": lost,
                "impact_ratio": round(lost / max(1, baseline_count), 4),
            }
        )

    results.sort(key=lambda r: r["lost_nodes"], reverse=True)
    for rank, row in enumerate(results, start=1):
        row["rank"] = rank
    return results


def load_transfer_feasibility(
    graph: NetworkGraph,
    feeder_a_source: str,
    feeder_b_source: str,
    tie_edge: NetworkEdge,
    load_field: str = "load",
    capacity_field: str = "capacity",
    max_cost: float = math.inf,
) -> dict[str, Any]:
    """Assess whether energising a tie switch between two feeders is feasible.

    Builds the service zone of each feeder via Dijkstra, sums the load and
    capacity across all edges in each zone, then checks whether either feeder
    can absorb the combined load without exceeding its capacity.
    """
    blocked = _device_state_blocked_edges(graph)

    dist_a, _, _, _ = _dijkstra(graph, [feeder_a_source], max_cost, blocked, {})
    dist_b, _, _, _ = _dijkstra(graph, [feeder_b_source], max_cost, blocked, {})
    zone_a = {n for n, d in dist_a.items() if d < math.inf}
    zone_b = {n for n, d in dist_b.items() if d < math.inf}

    def _zone_totals(zone: set[str]) -> tuple[float, float]:
        total_load = 0.0
        total_cap = 0.0
        seen: set[str] = set()
        for n in zone:
            for t in graph.adjacency.get(n, []):
                if t.edge_id in seen:
                    continue
                seen.add(t.edge_id)
                attrs = graph.edge_attributes.get(t.edge_id, {})
                total_load += float(attrs.get(load_field, 0) or 0)
                total_cap += float(attrs.get(capacity_field, 0) or 0)
        return total_load, total_cap

    load_a, cap_a = _zone_totals(zone_a)
    load_b, cap_b = _zone_totals(zone_b)
    combined_load = load_a + load_b
    tie_cap = float(tie_edge.get(capacity_field, 0) or 0)

    a_can = (combined_load <= cap_a) if cap_a > 0 else False
    b_can = (combined_load <= cap_b) if cap_b > 0 else False

    return {
        "feasible": a_can or b_can,
        "feeder_a_source": feeder_a_source,
        "feeder_b_source": feeder_b_source,
        "feeder_a_zone_nodes": len(zone_a),
        "feeder_b_zone_nodes": len(zone_b),
        "feeder_a_load": round(load_a, 4),
        "feeder_b_load": round(load_b, 4),
        "feeder_a_capacity": round(cap_a, 4),
        "feeder_b_capacity": round(cap_b, 4),
        "combined_load": round(combined_load, 4),
        "tie_capacity": round(tie_cap, 4),
        "a_can_absorb_b": a_can,
        "b_can_absorb_a": b_can,
        "overload_ratio_if_a_absorbs": round(combined_load / cap_a, 4) if cap_a > 0 else None,
        "overload_ratio_if_b_absorbs": round(combined_load / cap_b, 4) if cap_b > 0 else None,
    }


def feeder_load_balance_swap(
    graph: NetworkGraph,
    feeder_sources: list[str],
    load_field: str = "load",
    capacity_field: str = "capacity",
    max_cost: float = math.inf,
) -> list[dict[str, Any]]:
    """Suggest boundary-edge transfers to balance load across multiple feeders.

    Builds each feeder's service zone, computes the target (mean) load, then
    for each pair of adjacent over-/under-loaded feeders identifies the
    highest-load boundary edge whose transfer would reduce imbalance.
    """
    blocked = _device_state_blocked_edges(graph)

    feeder_zones: dict[str, set[str]] = {}
    for src in feeder_sources:
        dist, _, _, _ = _dijkstra(graph, [src], max_cost, blocked, {})
        feeder_zones[src] = {n for n, d in dist.items() if d < math.inf}

    def _feeder_load(zone: set[str]) -> float:
        total = 0.0
        seen: set[str] = set()
        for n in zone:
            for t in graph.adjacency.get(n, []):
                if t.edge_id in seen:
                    continue
                seen.add(t.edge_id)
                total += float(
                    graph.edge_attributes.get(t.edge_id, {}).get(load_field, 0) or 0
                )
        return total

    feeder_loads = {src: _feeder_load(zone) for src, zone in feeder_zones.items()}
    total_load = sum(feeder_loads.values())
    target = total_load / max(1, len(feeder_sources))

    overloaded = sorted(
        [(src, load) for src, load in feeder_loads.items() if load > target],
        key=lambda x: x[1],
        reverse=True,
    )
    underloaded = sorted(
        [(src, load) for src, load in feeder_loads.items() if load < target],
        key=lambda x: x[1],
    )

    suggestions: list[dict[str, Any]] = []
    for over_src, over_load in overloaded:
        for under_src, under_load in underloaded:
            boundary: list[dict[str, Any]] = []
            for n in feeder_zones[over_src]:
                for t in graph.adjacency.get(n, []):
                    if t.to_node in feeder_zones[under_src]:
                        attrs = graph.edge_attributes.get(t.edge_id, {})
                        el = float(attrs.get(load_field, 0) or 0)
                        if el > 0:
                            boundary.append(
                                {
                                    "edge_id": t.edge_id,
                                    "load": el,
                                    "from_node": t.from_node,
                                    "to_node": t.to_node,
                                }
                            )
            if boundary:
                best = max(boundary, key=lambda e: e["load"])
                suggestions.append(
                    {
                        "from_feeder": over_src,
                        "to_feeder": under_src,
                        "edge_id": best["edge_id"],
                        "from_node": best["from_node"],
                        "to_node": best["to_node"],
                        "transfer_load": round(best["load"], 4),
                        "overloaded_feeder_load": round(over_load, 4),
                        "underloaded_feeder_load": round(under_load, 4),
                        "target_load": round(target, 4),
                        "deficit": round(over_load - target, 4),
                    }
                )
    return suggestions


# ─── WATER / HYDRAULICS ───────────────────────────────────────────────────────


def pipe_break_isolation_zones(
    graph: NetworkGraph,
    break_edge_id: str,
    isolation_valve_device_types: set[str] | None = None,
    customer_field: str = "customers",
) -> dict[str, Any]:
    """Identify isolation zones and impacted customers for a pipe break.

    Localises the break edge, then traces outward from each endpoint using a
    BFS that stops at isolation-valve edges. Returns impacted nodes, edges,
    boundary valve edge IDs, and estimated customer count.
    """
    valve_types = isolation_valve_device_types or {
        "gate_valve",
        "butterfly_valve",
        "ball_valve",
        "isolation_valve",
    }

    break_attrs = graph.edge_attributes.get(break_edge_id)
    if break_attrs is None:
        raise ValueError(f"edge '{break_edge_id}' not found in graph")

    from_node = str(break_attrs.get("from_node", ""))
    to_node = str(break_attrs.get("to_node", ""))

    valve_edges: set[str] = {
        eid
        for eid, attrs in graph.edge_attributes.items()
        if str(attrs.get("device_type", "")) in valve_types
    }
    base_blocked: set[str] = {break_edge_id}

    def _bfs_zone(origin: str) -> tuple[set[str], set[str], int]:
        visited_nodes: set[str] = {origin}
        visited_edges: set[str] = set()
        total_customers = 0
        queue = [origin]
        while queue:
            node = queue.pop()
            for t in graph.adjacency.get(node, []):
                if t.edge_id in base_blocked or t.edge_id in valve_edges:
                    continue
                if t.edge_id in visited_edges:
                    continue
                visited_edges.add(t.edge_id)
                ea = graph.edge_attributes.get(t.edge_id, {})
                total_customers += int(float(ea.get(customer_field, 0) or 0))
                if t.to_node not in visited_nodes:
                    visited_nodes.add(t.to_node)
                    queue.append(t.to_node)
        return visited_nodes, visited_edges, total_customers

    zone_a_nodes, zone_a_edges, customers_a = _bfs_zone(from_node)
    zone_b_nodes, zone_b_edges, customers_b = _bfs_zone(to_node)

    all_affected_nodes = zone_a_nodes | zone_b_nodes
    boundary_valves: list[str] = sorted(
        {
            t.edge_id
            for n in all_affected_nodes
            for t in graph.adjacency.get(n, [])
            if t.edge_id in valve_edges
        }
    )

    return {
        "break_edge_id": break_edge_id,
        "from_node": from_node,
        "to_node": to_node,
        "affected_nodes": sorted(all_affected_nodes),
        "affected_edge_count": len(zone_a_edges | zone_b_edges),
        "boundary_valves": boundary_valves,
        "estimated_customers_impacted": customers_a + customers_b,
        "zone_a_node_count": len(zone_a_nodes),
        "zone_b_node_count": len(zone_b_nodes),
    }


def pressure_reducing_valve_trace(
    graph: NetworkGraph,
    prv_node: str,
    downstream_head_limit: float,
    min_residual_pressure: float = 0.0,
    max_cost: float = math.inf,
) -> dict[str, Any]:
    """Trace the pressure zone downstream of a PRV node.

    Runs Dijkstra from ``prv_node`` using edge costs as headloss proxies.
    The residual pressure at each node is ``downstream_head_limit - cumulative_headloss``.
    Nodes below ``min_residual_pressure`` are flagged.
    """
    blocked = _device_state_blocked_edges(graph)
    dist, _, _, _ = _dijkstra(graph, [prv_node], max_cost, blocked, {})

    zone_nodes: list[dict[str, Any]] = []
    low_pressure_nodes: list[str] = []

    for node, headloss in dist.items():
        if headloss >= math.inf:
            continue
        residual = downstream_head_limit - headloss
        is_low = residual < min_residual_pressure
        zone_nodes.append(
            {
                "node": node,
                "cumulative_headloss": round(headloss, 4),
                "residual_pressure": round(residual, 4),
                "low_pressure": is_low,
            }
        )
        if is_low:
            low_pressure_nodes.append(node)

    zone_nodes.sort(key=lambda r: r["cumulative_headloss"])

    return {
        "prv_node": prv_node,
        "downstream_head_limit": downstream_head_limit,
        "min_residual_pressure": min_residual_pressure,
        "zone_node_count": len(zone_nodes),
        "low_pressure_node_count": len(low_pressure_nodes),
        "low_pressure_nodes": low_pressure_nodes,
        "zone_pressure_profile": zone_nodes,
    }


def fire_flow_demand_check(
    graph: NetworkGraph,
    hydrant_nodes: list[str],
    demand_gpm: float,
    capacity_field: str = "capacity",
    flow_field: str = "flow",
) -> list[dict[str, Any]]:
    """Check if pipes directly serving hydrant nodes support the required fire flow.

    For each hydrant, inspects all immediately adjacent edges and reports the
    minimum residual capacity (``capacity - flow``). Edges with no capacity
    attribute are skipped. Returns results sorted by deficit descending.
    """
    results: list[dict[str, Any]] = []

    for hydrant in hydrant_nodes:
        min_residual = math.inf
        binding_edge: str | None = None

        for t in graph.adjacency.get(hydrant, []):
            attrs = graph.edge_attributes.get(t.edge_id, {})
            cap = float(attrs.get(capacity_field, 0) or 0)
            flow = float(attrs.get(flow_field, 0) or 0)
            if cap > 0:
                residual = cap - flow
                if residual < min_residual:
                    min_residual = residual
                    binding_edge = t.edge_id

        adequate = min_residual >= demand_gpm if min_residual < math.inf else False
        deficit = (
            round(max(0.0, demand_gpm - min_residual), 2)
            if min_residual < math.inf
            else demand_gpm
        )
        results.append(
            {
                "hydrant_node": hydrant,
                "required_flow_gpm": demand_gpm,
                "min_residual_capacity_gpm": (
                    round(min_residual, 2) if min_residual < math.inf else None
                ),
                "binding_edge_id": binding_edge,
                "adequate_for_fire_flow": adequate,
                "deficit_gpm": deficit,
            }
        )

    results.sort(key=lambda r: r["deficit_gpm"], reverse=True)
    return results


# ─── GAS ──────────────────────────────────────────────────────────────────────


def gas_pressure_drop_trace(
    graph: NetworkGraph,
    source_node: str,
    inlet_pressure: float,
    flow_field: str = "flow",
    diameter_field: str = "diameter",
    min_delivery_pressure: float = 0.0,
    max_cost: float = math.inf,
) -> dict[str, Any]:
    """Trace gas pressure drop from a source station through a distribution network.

    Uses a simplified Weymouth-style resistance proxy:
    ``resistance = base_cost x (flow / diameter²)``.  Dijkstra accumulates this
    resistance; residual pressure at each node is
    ``inlet_pressure - accumulated_resistance``.  Nodes below
    ``min_delivery_pressure`` are flagged.
    """
    overrides: dict[str, float] = {}
    for eid, attrs in graph.edge_attributes.items():
        flow = float(attrs.get(flow_field, 0) or 0)
        diameter = float(attrs.get(diameter_field, 1) or 1)
        base_cost = float(attrs.get("cost", 1) or 1)
        resistance = base_cost * (max(flow, 0.001) / max(diameter ** 2, 0.001))
        overrides[eid] = resistance

    blocked = _device_state_blocked_edges(graph)
    dist, _, _, _ = _dijkstra(graph, [source_node], max_cost, blocked, overrides)

    zone_nodes: list[dict[str, Any]] = []
    low_pressure_nodes: list[str] = []

    for node, accumulated in dist.items():
        if accumulated >= math.inf:
            continue
        residual = inlet_pressure - accumulated
        is_low = residual < min_delivery_pressure
        zone_nodes.append(
            {
                "node": node,
                "accumulated_pressure_drop": round(accumulated, 4),
                "residual_pressure": round(residual, 4),
                "below_min_delivery": is_low,
            }
        )
        if is_low:
            low_pressure_nodes.append(node)

    zone_nodes.sort(key=lambda r: r["accumulated_pressure_drop"])

    return {
        "source_node": source_node,
        "inlet_pressure": inlet_pressure,
        "min_delivery_pressure": min_delivery_pressure,
        "zone_node_count": len(zone_nodes),
        "low_pressure_node_count": len(low_pressure_nodes),
        "low_pressure_nodes": low_pressure_nodes,
        "pressure_profile": zone_nodes,
    }


def gas_odorization_zone_trace(
    graph: NetworkGraph,
    odorizer_nodes: list[str],
    max_cost: float = math.inf,
) -> list[dict[str, Any]]:
    """Trace the supply zone served by each gas odorizer station.

    Returns one entry per odorizer with its reachable zone, plus an ``overlap_nodes``
    list for nodes served by more than one odorizer (redundant odorization zones).
    """
    blocked = _device_state_blocked_edges(graph)

    zones: dict[str, set[str]] = {}
    for odorizer in odorizer_nodes:
        dist, _, _, _ = _dijkstra(graph, [odorizer], max_cost, blocked, {})
        zones[odorizer] = {n for n, d in dist.items() if d < math.inf}

    node_count: dict[str, int] = {}
    for zone_nodes in zones.values():
        for node in zone_nodes:
            node_count[node] = node_count.get(node, 0) + 1

    results: list[dict[str, Any]] = []
    for odorizer, zone_nodes in zones.items():
        overlap = [n for n in zone_nodes if node_count.get(n, 0) > 1]
        exclusive = [n for n in zone_nodes if node_count.get(n, 0) == 1]
        results.append(
            {
                "odorizer_node": odorizer,
                "zone_node_count": len(zone_nodes),
                "exclusive_node_count": len(exclusive),
                "overlap_node_count": len(overlap),
                "overlap_nodes": sorted(overlap),
                "zone_nodes": sorted(zone_nodes),
            }
        )

    results.sort(key=lambda r: r["zone_node_count"], reverse=True)
    return results


def gas_regulator_station_isolation(
    graph: NetworkGraph,
    regulator_node: str,
    supply_nodes: list[str] | None = None,
    max_cost: float = math.inf,
) -> dict[str, Any]:
    """Identify downstream segments that lose supply when a regulator is removed.

    Runs Dijkstra from ``supply_nodes`` (or all nodes when omitted) to establish
    baseline reachability, then blocks all edges incident to the regulator and
    re-runs from the same origins.  Nodes reachable in the baseline but not
    after removal are reported as isolated.

    Providing ``supply_nodes`` is recommended so that downstream-only nodes are
    not trivially counted as reachable via multi-source self-origin semantics.
    """
    blocked = _device_state_blocked_edges(graph)
    all_nodes = list(graph.nodes)
    origins = supply_nodes if supply_nodes else all_nodes

    baseline_dist, _, _, _ = _dijkstra(graph, origins, max_cost, blocked, {})
    baseline_reachable = {n for n, d in baseline_dist.items() if d < math.inf}

    incident: set[str] = set()
    for t in graph.adjacency.get(regulator_node, []):
        incident.add(t.edge_id)
    for _, tlist in graph.adjacency.items():
        for t in tlist:
            if t.to_node == regulator_node:
                incident.add(t.edge_id)

    post_blocked = blocked | incident
    post_dist, _, _, _ = _dijkstra(graph, origins, max_cost, post_blocked, {})
    post_reachable = {
        n for n, d in post_dist.items() if d < math.inf and n != regulator_node
    }

    isolated_nodes = sorted(
        baseline_reachable - post_reachable - {regulator_node}
    )
    isolated_set = set(isolated_nodes)
    isolated_edges = sorted(
        eid
        for eid, attrs in graph.edge_attributes.items()
        if str(attrs.get("from_node", "")) in isolated_set
        or str(attrs.get("to_node", "")) in isolated_set
    )

    return {
        "regulator_node": regulator_node,
        "isolated_node_count": len(isolated_nodes),
        "isolated_nodes": isolated_nodes,
        "isolated_edge_count": len(isolated_edges),
        "isolated_edge_ids": isolated_edges,
        "still_served_count": len(post_reachable),
        "alternate_path_available": len(isolated_nodes) == 0,
    }


# ─── CROSS-UTILITY / INFRASTRUCTURE ──────────────────────────────────────────


def co_location_conflict_scan(
    graphs: dict[str, NetworkGraph],
    corridor_field: str = "corridor_id",
) -> list[dict[str, Any]]:
    """Scan for edges from different utility types sharing the same node pair or corridor.

    ``graphs`` maps a utility-type label (e.g. ``"electric"``, ``"water"``) to a
    ``NetworkGraph``.  Two conflict types are detected:

    * ``"shared_node_pair"`` - two utilities have edges between the same two nodes.
    * ``"shared_corridor"`` - two utilities share a non-empty ``corridor_id`` attribute.
    """
    pair_index: dict[tuple[str, str], list[dict[str, Any]]] = {}
    corridor_index: dict[str, list[dict[str, Any]]] = {}

    for utility_type, graph in graphs.items():
        for eid, attrs in graph.edge_attributes.items():
            fn = str(attrs.get("from_node", ""))
            tn = str(attrs.get("to_node", ""))
            corridor = str(attrs.get(corridor_field, ""))
            entry: dict[str, Any] = {
                "utility_type": utility_type,
                "edge_id": eid,
                "from_node": fn,
                "to_node": tn,
                "corridor_id": corridor,
            }
            if fn and tn:
                pair = (min(fn, tn), max(fn, tn))
                pair_index.setdefault(pair, []).append(entry)
            if corridor:
                corridor_index.setdefault(corridor, []).append(entry)

    conflicts: list[dict[str, Any]] = []

    for pair, entries in pair_index.items():
        utility_types = {e["utility_type"] for e in entries}
        if len(utility_types) > 1:
            conflicts.append(
                {
                    "conflict_type": "shared_node_pair",
                    "from_node": pair[0],
                    "to_node": pair[1],
                    "corridor_id": None,
                    "utility_types": sorted(utility_types),
                    "edge_ids": [e["edge_id"] for e in entries],
                    "utility_count": len(utility_types),
                }
            )

    for corridor, entries in corridor_index.items():
        utility_types = {e["utility_type"] for e in entries}
        if len(utility_types) > 1:
            conflicts.append(
                {
                    "conflict_type": "shared_corridor",
                    "from_node": None,
                    "to_node": None,
                    "corridor_id": corridor,
                    "utility_types": sorted(utility_types),
                    "edge_ids": [e["edge_id"] for e in entries],
                    "utility_count": len(utility_types),
                }
            )

    conflicts.sort(key=lambda c: c["utility_count"], reverse=True)
    return conflicts


def interdependency_cascade_simulation(
    primary_graph: NetworkGraph,
    dependent_graph: NetworkGraph,
    dependency_map: dict[str, list[str]],
    initial_failed_nodes: list[str],
    max_cascade_rounds: int = 10,
    max_cost: float = math.inf,
) -> dict[str, Any]:
    """Simulate cascading failures from a primary network into a dependent network.

    ``dependency_map`` maps primary-network nodes to the dependent-network nodes
    they supply.  When a primary node becomes isolated, its dependent nodes fail.
    Each round re-checks primary connectivity and propagates further failures.
    """
    failed_primary: set[str] = set(initial_failed_nodes)
    failed_dependent: set[str] = set()
    cascade_log: list[dict[str, Any]] = []

    for round_num in range(1, max_cascade_rounds + 1):
        new_dependent: set[str] = set()
        for pnode in failed_primary:
            for dnode in dependency_map.get(pnode, []):
                if dnode not in failed_dependent:
                    new_dependent.add(dnode)

        if not new_dependent:
            break

        failed_dependent |= new_dependent

        # Block edges incident to failed primary nodes and re-check isolation
        all_blocked = _device_state_blocked_edges(primary_graph)
        for node in failed_primary:
            for t in primary_graph.adjacency.get(node, []):
                all_blocked.add(t.edge_id)
        for dnode in new_dependent:
            for t in primary_graph.adjacency.get(dnode, []):
                all_blocked.add(t.edge_id)

        surviving = [n for n in primary_graph.nodes if n not in failed_primary]
        newly_isolated: set[str] = set()
        if surviving:
            dist, _, _, _ = _dijkstra(
                primary_graph, surviving, max_cost, all_blocked, {}
            )
            newly_isolated = {
                n
                for n, d in dist.items()
                if d >= math.inf and n not in failed_primary
            }
            failed_primary |= newly_isolated

        cascade_log.append(
            {
                "round": round_num,
                "new_dependent_failures": sorted(new_dependent),
                "new_primary_failures": sorted(newly_isolated),
            }
        )

    return {
        "initial_failed_nodes": sorted(initial_failed_nodes),
        "total_primary_failures": len(failed_primary),
        "total_dependent_failures": len(failed_dependent),
        "failed_primary_nodes": sorted(failed_primary),
        "failed_dependent_nodes": sorted(failed_dependent),
        "cascade_rounds": len(cascade_log),
        "cascade_log": cascade_log,
    }


def infrastructure_age_risk_weighted_routing(
    graph: NetworkGraph,
    origin: str,
    destination: str,
    age_field: str = "age_years",
    design_life_field: str = "design_life_years",
    max_cost: float = math.inf,
) -> dict[str, Any]:
    """Route between two nodes minimising cumulative infrastructure age-risk.

    Each edge cost is scaled by ``1 + min(age / design_life, 1.0)``, so older
    pipes near end-of-life carry higher traversal cost.  Returns the path, its
    risk-weighted total cost, base cost, and the risk premium difference.
    """
    overrides: dict[str, float] = {}
    for eid, attrs in graph.edge_attributes.items():
        age = float(attrs.get(age_field, 0) or 0)
        design_life = float(attrs.get(design_life_field, 1) or 1)
        risk_factor = min(age / max(design_life, 1), 1.0)
        base_cost = float(attrs.get("cost", 1) or 1)
        overrides[eid] = base_cost * (1.0 + risk_factor)

    blocked = _device_state_blocked_edges(graph)
    dist, prev_node, prev_edge, _ = _dijkstra(
        graph, [origin], max_cost, blocked, overrides
    )

    if dist.get(destination, math.inf) >= math.inf:
        return {
            "origin": origin,
            "destination": destination,
            "path_found": False,
            "path_nodes": [],
            "path_edges": [],
            "total_risk_weighted_cost": None,
            "total_base_cost": None,
            "risk_premium": None,
        }

    path_nodes: list[str] = []
    path_edges: list[str] = []
    node: str | None = destination
    while node is not None:
        path_nodes.append(node)
        edge = prev_edge.get(node)
        if edge:
            path_edges.append(edge)
        node = prev_node.get(node)
    path_nodes.reverse()
    path_edges.reverse()

    base_cost = sum(
        float(graph.edge_attributes.get(e, {}).get("cost", 0) or 0)
        for e in path_edges
    )

    return {
        "origin": origin,
        "destination": destination,
        "path_found": True,
        "path_nodes": path_nodes,
        "path_edges": path_edges,
        "total_risk_weighted_cost": round(dist[destination], 4),
        "total_base_cost": round(base_cost, 4),
        "risk_premium": round(dist[destination] - base_cost, 4),
    }


def critical_customer_coverage_audit(
    graph: NetworkGraph,
    critical_customer_nodes: list[str],
    supply_nodes: list[str],
    max_cost: float = math.inf,
) -> list[dict[str, Any]]:
    """Audit single points of failure on supply paths to critical customers.

    For each critical customer, reconstructs the shortest path from the nearest
    supply node and then probes whether removing any single path edge disconnects
    supply entirely.  Those edges are reported as single points of failure.
    """
    blocked = _device_state_blocked_edges(graph)
    results: list[dict[str, Any]] = []

    for customer in critical_customer_nodes:
        dist, prev_node, prev_edge, source_map = _dijkstra(
            graph, supply_nodes, max_cost, blocked, {}
        )

        if dist.get(customer, math.inf) >= math.inf:
            results.append(
                {
                    "critical_customer": customer,
                    "reachable": False,
                    "supply_source": None,
                    "path_nodes": [],
                    "path_edges": [],
                    "single_points_of_failure_edges": [],
                }
            )
            continue

        path_nodes: list[str] = []
        path_edges: list[str] = []
        n: str | None = customer
        while n is not None:
            path_nodes.append(n)
            e = prev_edge.get(n)
            if e:
                path_edges.append(e)
            n = prev_node.get(n)
        path_nodes.reverse()
        path_edges.reverse()

        spof: list[str] = []
        for candidate in path_edges:
            test_dist, _, _, _ = _dijkstra(
                graph, supply_nodes, max_cost, blocked | {candidate}, {}
            )
            if test_dist.get(customer, math.inf) >= math.inf:
                spof.append(candidate)

        results.append(
            {
                "critical_customer": customer,
                "reachable": True,
                "supply_source": source_map.get(customer),
                "path_nodes": path_nodes,
                "path_edges": path_edges,
                "single_points_of_failure_edges": spof,
            }
        )

    results.sort(key=lambda r: len(r["single_points_of_failure_edges"]), reverse=True)
    return results


# ─── STORMWATER / DRAINAGE ────────────────────────────────────────────────────


def stormwater_flow_accumulation(
    graph: NetworkGraph,
    runoff_by_node: dict[str, float],
    capacity_field: str = "capacity",
) -> list[dict[str, Any]]:
    """Accumulate stormwater runoff downstream through a directed drainage network.

    Performs a topological-order BFS (Kahn's algorithm) starting from headwater
    nodes.  Each node passes its accumulated flow to immediately downstream
    nodes.  Edges are checked for capacity exceedance.
    """
    in_degree: dict[str, int] = {n: 0 for n in graph.nodes}
    for n in graph.nodes:
        for t in graph.adjacency.get(n, []):
            in_degree[t.to_node] = in_degree.get(t.to_node, 0) + 1

    queue = [n for n, deg in in_degree.items() if deg == 0]
    order: list[str] = []
    while queue:
        node = queue.pop(0)
        order.append(node)
        for t in graph.adjacency.get(node, []):
            in_degree[t.to_node] -= 1
            if in_degree[t.to_node] == 0:
                queue.append(t.to_node)

    accumulated: dict[str, float] = dict(runoff_by_node)
    for node in order:
        node_flow = accumulated.get(node, 0.0)
        for t in graph.adjacency.get(node, []):
            accumulated[t.to_node] = accumulated.get(t.to_node, 0.0) + node_flow

    results: list[dict[str, Any]] = []
    for node in graph.nodes:
        flow = accumulated.get(node, runoff_by_node.get(node, 0.0))
        max_cap = 0.0
        for t in graph.adjacency.get(node, []):
            attrs = graph.edge_attributes.get(t.edge_id, {})
            cap = float(attrs.get(capacity_field, 0) or 0)
            if cap > max_cap:
                max_cap = cap
        overloaded = max_cap > 0 and flow > max_cap
        results.append(
            {
                "node": node,
                "local_runoff": runoff_by_node.get(node, 0.0),
                "accumulated_flow": round(flow, 4),
                "outflow_capacity": round(max_cap, 4) if max_cap > 0 else None,
                "capacity_exceeded": overloaded,
                "overload_ratio": (
                    round(flow / max_cap, 4) if max_cap > 0 else None
                ),
            }
        )

    results.sort(key=lambda r: r["accumulated_flow"], reverse=True)
    return results


def detention_basin_overflow_trace(
    graph: NetworkGraph,
    basin_node: str,
    basin_capacity: float,
    inflow: float,
    overflow_edge_ids: list[str] | None = None,
    max_cost: float = math.inf,
) -> dict[str, Any]:
    """Trace the overflow conveyance path when a basin exceeds its storage capacity.

    When ``inflow > basin_capacity`` the surplus is routed along the lowest-cost
    downstream path from the basin.  Optionally restricts traversal to
    ``overflow_edge_ids`` (designated spillways).
    """
    overflow_volume = max(0.0, inflow - basin_capacity)

    if overflow_volume == 0.0:
        return {
            "basin_node": basin_node,
            "basin_capacity": basin_capacity,
            "inflow": inflow,
            "overflow_volume": 0.0,
            "overflow_occurring": False,
            "overflow_path_nodes": [],
            "overflow_path_edges": [],
            "terminal_node": None,
        }

    blocked: set[str] = set()
    if overflow_edge_ids is not None:
        all_ids = set(graph.edge_attributes.keys())
        blocked = all_ids - set(overflow_edge_ids)
    blocked |= _device_state_blocked_edges(graph)

    dist, prev_node, prev_edge, _ = _dijkstra(
        graph, [basin_node], max_cost, blocked, {}
    )

    reachable = [
        (n, d) for n, d in dist.items() if d < math.inf and n != basin_node
    ]
    if not reachable:
        return {
            "basin_node": basin_node,
            "basin_capacity": basin_capacity,
            "inflow": inflow,
            "overflow_volume": round(overflow_volume, 4),
            "overflow_occurring": True,
            "overflow_path_nodes": [basin_node],
            "overflow_path_edges": [],
            "terminal_node": None,
        }

    terminal_node = max(reachable, key=lambda x: x[1])[0]

    path_nodes: list[str] = []
    path_edges: list[str] = []
    node: str | None = terminal_node
    while node is not None:
        path_nodes.append(node)
        e = prev_edge.get(node)
        if e:
            path_edges.append(e)
        node = prev_node.get(node)
    path_nodes.reverse()
    path_edges.reverse()

    return {
        "basin_node": basin_node,
        "basin_capacity": basin_capacity,
        "inflow": inflow,
        "overflow_volume": round(overflow_volume, 4),
        "overflow_occurring": True,
        "overflow_path_nodes": path_nodes,
        "overflow_path_edges": path_edges,
        "terminal_node": terminal_node,
        "overflow_path_length": len(path_edges),
    }


def inflow_infiltration_scan(
    graph: NetworkGraph,
    observed_flow_field: str = "observed_flow",
    dry_weather_flow_field: str = "dry_weather_flow",
    infiltration_threshold_ratio: float = 1.25,
) -> list[dict[str, Any]]:
    """Scan pipe segments for inflow/infiltration (I&I) above a threshold.

    Computes ``observed_flow / dry_weather_flow`` per edge.  Edges exceeding
    ``infiltration_threshold_ratio`` are flagged.  Edges with no dry-weather
    baseline but non-zero observed flow are flagged with reason
    ``"no_dry_weather_baseline"``.
    """
    results: list[dict[str, Any]] = []

    for eid, attrs in graph.edge_attributes.items():
        observed = float(attrs.get(observed_flow_field, 0) or 0)
        dry_weather = float(attrs.get(dry_weather_flow_field, 0) or 0)

        if dry_weather <= 0:
            if observed > 0:
                results.append(
                    {
                        "edge_id": eid,
                        "from_node": str(attrs.get("from_node", "")),
                        "to_node": str(attrs.get("to_node", "")),
                        "observed_flow": observed,
                        "dry_weather_flow": dry_weather,
                        "infiltration_ratio": None,
                        "flagged": True,
                        "flag_reason": "no_dry_weather_baseline",
                    }
                )
            continue

        ratio = observed / dry_weather
        flagged = ratio > infiltration_threshold_ratio
        results.append(
            {
                "edge_id": eid,
                "from_node": str(attrs.get("from_node", "")),
                "to_node": str(attrs.get("to_node", "")),
                "observed_flow": round(observed, 4),
                "dry_weather_flow": round(dry_weather, 4),
                "infiltration_ratio": round(ratio, 4),
                "flagged": flagged,
                "flag_reason": "exceeds_threshold" if flagged else None,
            }
        )

    results.sort(key=lambda r: r["infiltration_ratio"] or 0.0, reverse=True)
    return results


# ─── TELECOM / FIBER ──────────────────────────────────────────────────────────


def fiber_splice_node_trace(
    graph: NetworkGraph,
    splice_node: str,
    circuit_endpoints: list[tuple[str, str]] | None = None,
    max_cost: float = math.inf,
) -> dict[str, Any]:
    """Enumerate circuits that traverse a splice node.

    When ``circuit_endpoints`` is provided, the shortest path for every
    ``(origin, destination)`` pair is computed and checked for passage through
    ``splice_node``.  Without endpoints, returns the set of edges directly
    incident to the splice node.
    """
    blocked = _device_state_blocked_edges(graph)

    if circuit_endpoints is not None:
        affected: list[dict[str, Any]] = []
        for origin, destination in circuit_endpoints:
            dist, prev_node, prev_edge, _ = _dijkstra(
                graph, [origin], max_cost, blocked, {}
            )
            if dist.get(destination, math.inf) >= math.inf:
                continue
            path_nodes: list[str] = []
            n: str | None = destination
            while n is not None:
                path_nodes.append(n)
                n = prev_node.get(n)
            path_nodes.reverse()
            if splice_node not in path_nodes:
                continue
            path_edges: list[str] = []
            n = destination
            while n is not None:
                e = prev_edge.get(n)
                if e:
                    path_edges.append(e)
                n = prev_node.get(n)
            path_edges.reverse()
            affected.append(
                {
                    "origin": origin,
                    "destination": destination,
                    "path_nodes": path_nodes,
                    "path_edges": path_edges,
                    "path_length": len(path_edges),
                }
            )
        return {
            "splice_node": splice_node,
            "circuits_checked": len(circuit_endpoints),
            "circuits_traversing_splice": len(affected),
            "affected_circuits": affected,
        }

    outgoing = [t.edge_id for t in graph.adjacency.get(splice_node, [])]
    incoming = [
        t.edge_id
        for _, tlist in graph.adjacency.items()
        for t in tlist
        if t.to_node == splice_node
    ]
    all_incident = sorted(set(outgoing) | set(incoming))

    return {
        "splice_node": splice_node,
        "circuits_checked": 0,
        "circuits_traversing_splice": len(all_incident),
        "incident_edge_ids": all_incident,
        "affected_circuits": [],
    }


def ring_redundancy_check(
    graph: NetworkGraph,
    ring_nodes: list[str],
    hub_node: str,
    max_cost: float = math.inf,
) -> list[dict[str, Any]]:
    """Verify each ring node has at least two edge-independent paths to the hub.

    For each ring node, the primary path from ``hub_node`` is found.  Then every
    edge on that path is individually removed to check whether an alternate route
    still exists.  If any single edge cuts the only route, ``has_redundancy`` is
    ``False``.
    """
    blocked = _device_state_blocked_edges(graph)
    results: list[dict[str, Any]] = []

    for node in ring_nodes:
        if node == hub_node:
            continue

        dist, prev_node, prev_edge, _ = _dijkstra(
            graph, [hub_node], max_cost, blocked, {}
        )

        if dist.get(node, math.inf) >= math.inf:
            results.append(
                {
                    "node": node,
                    "reachable_from_hub": False,
                    "has_redundancy": False,
                    "primary_path_edges": [],
                    "alternate_path_found": False,
                    "alternate_path_cost": None,
                }
            )
            continue

        primary_edges: list[str] = []
        n: str | None = node
        while n is not None:
            e = prev_edge.get(n)
            if e:
                primary_edges.append(e)
            n = prev_node.get(n)
        primary_edges.reverse()

        has_redundancy = True
        for edge_to_block in primary_edges:
            alt_dist, _, _, _ = _dijkstra(
                graph, [hub_node], max_cost, blocked | {edge_to_block}, {}
            )
            if alt_dist.get(node, math.inf) >= math.inf:
                has_redundancy = False
                break

        alt_dist, _, _, _ = _dijkstra(
            graph, [hub_node], max_cost, blocked | set(primary_edges), {}
        )
        alt_cost = alt_dist.get(node)

        results.append(
            {
                "node": node,
                "reachable_from_hub": True,
                "has_redundancy": has_redundancy,
                "primary_path_edges": primary_edges,
                "alternate_path_found": alt_cost is not None
                and alt_cost < math.inf,
                "alternate_path_cost": (
                    round(alt_cost, 4)
                    if alt_cost is not None and alt_cost < math.inf
                    else None
                ),
            }
        )

    results.sort(key=lambda r: (0 if not r["has_redundancy"] else 1, r["node"]))
    return results


def fiber_cut_impact_matrix(
    graph: NetworkGraph,
    cut_candidate_edges: list[str],
    circuit_endpoints: list[tuple[str, str]],
    max_cost: float = math.inf,
) -> list[dict[str, Any]]:
    """Compute the number of circuits impacted by each candidate fiber cut.

    For every edge in ``cut_candidate_edges``, removes it from the graph and
    counts how many ``circuit_endpoints`` lose end-to-end connectivity.
    Results are sorted by ``circuits_impacted`` descending.
    """
    blocked = _device_state_blocked_edges(graph)

    baseline: dict[tuple[str, str], bool] = {}
    for origin, destination in circuit_endpoints:
        d, _, _, _ = _dijkstra(graph, [origin], max_cost, blocked, {})
        baseline[(origin, destination)] = d.get(destination, math.inf) < math.inf

    results: list[dict[str, Any]] = []

    for cut_edge in cut_candidate_edges:
        test_blocked = blocked | {cut_edge}
        impacted: list[dict[str, str]] = []
        for origin, destination in circuit_endpoints:
            if not baseline.get((origin, destination), False):
                continue
            d, _, _, _ = _dijkstra(graph, [origin], max_cost, test_blocked, {})
            if d.get(destination, math.inf) >= math.inf:
                impacted.append({"origin": origin, "destination": destination})

        cut_attrs = graph.edge_attributes.get(cut_edge, {})
        results.append(
            {
                "cut_edge_id": cut_edge,
                "from_node": str(cut_attrs.get("from_node", "")),
                "to_node": str(cut_attrs.get("to_node", "")),
                "circuits_impacted": len(impacted),
                "circuits_total": len(circuit_endpoints),
                "impact_ratio": round(
                    len(impacted) / max(1, len(circuit_endpoints)), 4
                ),
                "impacted_circuit_list": impacted,
            }
        )

    results.sort(key=lambda r: r["circuits_impacted"], reverse=True)
    return results


# ─── RELIABILITY & RESTORATION ──────────────────────────────────────────────


def n_minus_one_edge_contingency_screen(
    graph: NetworkGraph,
    source_nodes: list[str],
    demand_by_node: dict[str, float] | None = None,
    candidate_edge_ids: list[str] | None = None,
    critical_nodes: list[str] | None = None,
    max_cost: float = math.inf,
) -> list[dict[str, Any]]:
    """Screen single-edge failures and rank impact severity.

    Baseline reachability is computed from ``source_nodes`` with current device
    states (open switches/valves are blocked). Each candidate edge is then
    removed one-at-a-time and service loss is measured against baseline.
    """
    if not source_nodes:
        raise ValueError("source_nodes must include at least one node")

    blocked = _device_state_blocked_edges(graph)
    baseline_dist, _, _, _ = _dijkstra(graph, source_nodes, max_cost, blocked, {})
    baseline_served = set(baseline_dist.keys())

    demand_map = demand_by_node or {}
    baseline_served_demand = sum(float(demand_map.get(n, 0) or 0) for n in baseline_served)
    critical_set = set(critical_nodes or [])

    candidates = candidate_edge_ids or sorted(graph.edge_attributes.keys())
    results: list[dict[str, Any]] = []

    for edge_id in candidates:
        attrs = graph.edge_attributes.get(edge_id)
        if attrs is None:
            continue

        blocked_with_cut = set(blocked)
        blocked_with_cut.add(edge_id)
        dist_after_cut, _, _, _ = _dijkstra(
            graph, source_nodes, max_cost, blocked_with_cut, {}
        )
        served_after_cut = set(dist_after_cut.keys())

        lost_nodes = sorted(baseline_served - served_after_cut)
        lost_critical = sorted(n for n in lost_nodes if n in critical_set)
        lost_demand = sum(float(demand_map.get(n, 0) or 0) for n in lost_nodes)
        served_demand_after_cut = baseline_served_demand - lost_demand

        # Bias severity toward critical-node outages first, then demand loss.
        severity = (1000.0 * len(lost_critical)) + lost_demand

        results.append(
            {
                "cut_edge_id": edge_id,
                "from_node": str(attrs.get("from_node", "")),
                "to_node": str(attrs.get("to_node", "")),
                "lost_node_count": len(lost_nodes),
                "lost_nodes": lost_nodes,
                "lost_critical_count": len(lost_critical),
                "lost_critical_nodes": lost_critical,
                "lost_demand": round(lost_demand, 4),
                "served_demand_after_cut": round(served_demand_after_cut, 4),
                "baseline_served_demand": round(baseline_served_demand, 4),
                "severity_score": round(severity, 4),
            }
        )

    results.sort(
        key=lambda r: (
            r["lost_critical_count"],
            r["lost_demand"],
            r["lost_node_count"],
        ),
        reverse=True,
    )
    return results


def outage_restoration_tie_options(
    graph: NetworkGraph,
    source_nodes: list[str],
    affected_nodes: list[str],
    tie_edge_ids: list[str] | None = None,
    max_cost: float = math.inf,
) -> list[dict[str, Any]]:
    """Rank normally-open tie edges by restored-node benefit.

    Uses current device states as baseline outage state and simulates closing one
    candidate tie edge at a time.
    """
    if not source_nodes:
        raise ValueError("source_nodes must include at least one node")

    blocked = _device_state_blocked_edges(graph)

    if tie_edge_ids is None:
        tie_edge_ids = []
        for edge_id, attrs in graph.edge_attributes.items():
            device_type = str(attrs.get("device_type", "")).lower()
            state = str(attrs.get("state", "")).lower()
            if device_type in {"tie", "switch"} and state in {"open", "normally_open"}:
                tie_edge_ids.append(edge_id)

    baseline_blocked = set(blocked)
    for tie_edge_id in tie_edge_ids:
        attrs = graph.edge_attributes.get(tie_edge_id, {})
        state = str(attrs.get("state", "")).lower()
        if state in {"open", "normally_open"}:
            baseline_blocked.add(tie_edge_id)

    baseline_dist, _, _, _ = _dijkstra(
        graph, source_nodes, max_cost, baseline_blocked, {}
    )
    baseline_served = set(baseline_dist.keys())
    baseline_unserved_targets = sorted(set(affected_nodes) - baseline_served)

    results: list[dict[str, Any]] = []

    for tie_edge_id in tie_edge_ids:
        attrs = graph.edge_attributes.get(tie_edge_id)
        if attrs is None:
            continue

        blocked_with_tie_closed = set(baseline_blocked)
        blocked_with_tie_closed.discard(tie_edge_id)

        dist_with_tie, _, _, _ = _dijkstra(
            graph, source_nodes, max_cost, blocked_with_tie_closed, {}
        )
        served_with_tie = set(dist_with_tie.keys())

        restored_nodes = sorted(
            node for node in baseline_unserved_targets if node in served_with_tie
        )

        results.append(
            {
                "tie_edge_id": tie_edge_id,
                "from_node": str(attrs.get("from_node", "")),
                "to_node": str(attrs.get("to_node", "")),
                "baseline_unserved_targets": len(baseline_unserved_targets),
                "restored_target_count": len(restored_nodes),
                "restored_targets": restored_nodes,
                "restoration_ratio": round(
                    len(restored_nodes) / max(1, len(baseline_unserved_targets)), 4
                ),
            }
        )

    results.sort(key=lambda r: r["restored_target_count"], reverse=True)
    return results


def n_minus_k_edge_contingency_screen(
    graph: NetworkGraph,
    source_nodes: list[str],
    k: int = 2,
    demand_by_node: dict[str, float] | None = None,
    candidate_edge_ids: list[str] | None = None,
    critical_nodes: list[str] | None = None,
    max_cost: float = math.inf,
    max_combinations: int = 5000,
) -> list[dict[str, Any]]:
    """Screen k-edge outage combinations and rank impact severity."""
    if not source_nodes:
        raise ValueError("source_nodes must include at least one node")
    if k < 1:
        raise ValueError("k must be >= 1")

    blocked = _device_state_blocked_edges(graph)
    baseline_dist, _, _, _ = _dijkstra(graph, source_nodes, max_cost, blocked, {})
    baseline_served = set(baseline_dist.keys())

    demand_map = demand_by_node or {}
    baseline_served_demand = sum(
        float(demand_map.get(n, 0) or 0) for n in baseline_served
    )
    critical_set = set(critical_nodes or [])

    candidates = candidate_edge_ids or sorted(graph.edge_attributes.keys())
    if k > len(candidates):
        return []

    rows: list[dict[str, Any]] = []
    for idx, cut_combo in enumerate(combinations(candidates, k)):
        if idx >= max_combinations:
            break
        test_blocked = set(blocked) | set(cut_combo)
        dist_after_cut, _, _, _ = _dijkstra(
            graph, source_nodes, max_cost, test_blocked, {}
        )
        served_after_cut = set(dist_after_cut.keys())

        lost_nodes = sorted(baseline_served - served_after_cut)
        lost_critical = sorted(n for n in lost_nodes if n in critical_set)
        lost_demand = sum(float(demand_map.get(n, 0) or 0) for n in lost_nodes)
        severity = (1000.0 * len(lost_critical)) + lost_demand

        rows.append(
            {
                "k": k,
                "cut_edge_ids": list(cut_combo),
                "lost_node_count": len(lost_nodes),
                "lost_nodes": lost_nodes,
                "lost_critical_count": len(lost_critical),
                "lost_critical_nodes": lost_critical,
                "lost_demand": round(lost_demand, 4),
                "baseline_served_demand": round(baseline_served_demand, 4),
                "severity_score": round(severity, 4),
            }
        )

    rows.sort(
        key=lambda r: (r["lost_critical_count"], r["lost_demand"], r["lost_node_count"]),
        reverse=True,
    )
    return rows


def crew_dispatch_optimizer(
    graph: NetworkGraph,
    source_nodes: list[str],
    failed_edges: list[str],
    repair_time_by_edge: dict[str, float] | None = None,
    critical_nodes: list[str] | None = None,
    demand_by_node: dict[str, float] | None = None,
    max_cost: float = math.inf,
) -> dict[str, Any]:
    """Greedy repair ordering that maximizes restored service per hour."""
    if not source_nodes:
        raise ValueError("source_nodes must include at least one node")

    blocked_base = _device_state_blocked_edges(graph)
    repair_hours = repair_time_by_edge or {}
    critical_set = set(critical_nodes or [])
    demand_map = demand_by_node or {}

    remaining_failed = [e for e in failed_edges if e in graph.edge_attributes]
    current_blocked = blocked_base | set(remaining_failed)
    current_dist, _, _, _ = _dijkstra(graph, source_nodes, max_cost, current_blocked, {})
    current_served = set(current_dist.keys())

    plan: list[dict[str, Any]] = []
    total_hours = 0.0

    while remaining_failed:
        best_row: dict[str, Any] | None = None
        best_served: set[str] | None = None

        for candidate in remaining_failed:
            test_failed = set(remaining_failed)
            test_failed.discard(candidate)
            test_blocked = blocked_base | test_failed
            test_dist, _, _, _ = _dijkstra(graph, source_nodes, max_cost, test_blocked, {})
            test_served = set(test_dist.keys())

            restored_nodes = sorted(test_served - current_served)
            restored_critical = sorted(n for n in restored_nodes if n in critical_set)
            restored_demand = sum(float(demand_map.get(n, 0) or 0) for n in restored_nodes)

            hours = float(repair_hours.get(candidate, 1.0) or 1.0)
            benefit = (1000.0 * len(restored_critical)) + restored_demand + len(restored_nodes)
            score = benefit / max(0.01, hours)

            row = {
                "repair_edge_id": candidate,
                "repair_hours": round(hours, 4),
                "restored_node_count": len(restored_nodes),
                "restored_nodes": restored_nodes,
                "restored_critical_count": len(restored_critical),
                "restored_critical_nodes": restored_critical,
                "restored_demand": round(restored_demand, 4),
                "benefit_per_hour": round(score, 6),
            }

            if best_row is None or score > float(best_row["benefit_per_hour"]):
                best_row = row
                best_served = test_served

        if best_row is None or best_served is None:
            break

        remaining_failed.remove(str(best_row["repair_edge_id"]))
        total_hours += float(best_row["repair_hours"])
        current_served = best_served
        best_row["remaining_failed_edges"] = len(remaining_failed)
        best_row["cumulative_repair_hours"] = round(total_hours, 4)
        plan.append(best_row)

    return {
        "repair_plan": plan,
        "final_served_node_count": len(current_served),
        "total_repairs_planned": len(plan),
        "total_repair_hours": round(total_hours, 4),
    }


def pressure_zone_reconfiguration_planner(
    graph: NetworkGraph,
    source_nodes: list[str],
    pressure_min: float = 30.0,
    pressure_max: float = 120.0,
    valve_edge_ids: list[str] | None = None,
    source_pressure: float = 80.0,
    pressure_drop_per_cost: float = 2.0,
    max_cost: float = math.inf,
) -> list[dict[str, Any]]:
    """Rank valve operations by pressure-band compliance improvement."""
    if not source_nodes:
        raise ValueError("source_nodes must include at least one node")

    blocked = _device_state_blocked_edges(graph)

    if valve_edge_ids is None:
        valve_edge_ids = []
        for edge_id, attrs in graph.edge_attributes.items():
            if str(attrs.get("device_type", "")).lower() in {"valve", "switch", "prv"}:
                valve_edge_ids.append(edge_id)

    def _evaluate(blocked_edges: set[str]) -> tuple[int, int, dict[str, float]]:
        dist, _, _, _ = _dijkstra(graph, source_nodes, max_cost, blocked_edges, {})
        estimates: dict[str, float] = {}
        within = 0
        for node, cost in dist.items():
            pressure = source_pressure - (pressure_drop_per_cost * float(cost))
            estimates[node] = round(pressure, 4)
            if pressure_min <= pressure <= pressure_max:
                within += 1
        return len(dist), within, estimates

    baseline_reachable, baseline_within, _ = _evaluate(set(blocked))

    rows: list[dict[str, Any]] = []
    for valve_edge_id in valve_edge_ids:
        attrs = graph.edge_attributes.get(valve_edge_id)
        if attrs is None:
            continue

        state = str(attrs.get("state", "")).lower()
        if state in {"open", "normally_open"}:
            operation = "close"
            test_blocked = set(blocked)
            test_blocked.add(valve_edge_id)
        else:
            operation = "open"
            test_blocked = set(blocked)
            test_blocked.discard(valve_edge_id)

        reach_after, within_after, _ = _evaluate(test_blocked)
        rows.append(
            {
                "valve_edge_id": valve_edge_id,
                "operation": operation,
                "from_node": str(attrs.get("from_node", "")),
                "to_node": str(attrs.get("to_node", "")),
                "baseline_reachable_nodes": baseline_reachable,
                "baseline_within_pressure_band": baseline_within,
                "reachable_nodes_after": reach_after,
                "within_pressure_band_after": within_after,
                "delta_within_pressure_band": within_after - baseline_within,
            }
        )

    rows.sort(
        key=lambda r: (r["delta_within_pressure_band"], r["within_pressure_band_after"]),
        reverse=True,
    )
    return rows


def pump_station_failure_cascade(
    graph: NetworkGraph,
    pump_nodes: list[str],
    initial_failed_pumps: list[str],
    dependency_map: dict[str, list[str]] | None = None,
    source_nodes: list[str] | None = None,
    max_rounds: int = 5,
    max_cost: float = math.inf,
) -> dict[str, Any]:
    """Simulate cascading pump failures through dependencies and isolation."""
    pump_set = set(pump_nodes)
    failed = set(initial_failed_pumps) & pump_set
    dependencies = dependency_map or {}
    sources = source_nodes or []

    rounds: list[dict[str, Any]] = []

    for round_idx in range(1, max_rounds + 1):
        newly_failed: set[str] = set()

        for failed_pump in list(failed):
            for dep in dependencies.get(failed_pump, []):
                if dep in pump_set and dep not in failed:
                    newly_failed.add(dep)

        if sources:
            blocked = _device_state_blocked_edges(graph)
            for pump in failed:
                for step in graph.adjacency.get(pump, []):
                    blocked.add(step.edge_id)

            dist, _, _, _ = _dijkstra(graph, sources, max_cost, blocked, {})
            reachable = set(dist.keys())
            for pump in pump_set:
                if pump not in failed and pump not in reachable:
                    newly_failed.add(pump)

        if not newly_failed:
            break

        failed |= newly_failed
        rounds.append(
            {
                "round": round_idx,
                "newly_failed_pumps": sorted(newly_failed),
                "total_failed_pumps": sorted(failed),
                "total_failed_count": len(failed),
            }
        )

    return {
        "initial_failed_pumps": sorted(set(initial_failed_pumps) & pump_set),
        "final_failed_pumps": sorted(failed),
        "final_failed_count": len(failed),
        "rounds": rounds,
    }


def feeder_reconfiguration_optimizer(
    graph: NetworkGraph,
    source_nodes: list[str],
    tie_edge_ids: list[str],
    demand_by_node: dict[str, float] | None = None,
    critical_nodes: list[str] | None = None,
    max_switch_actions: int = 2,
    max_cost: float = math.inf,
) -> dict[str, Any]:
    """Greedy tie-switch closure sequence to maximize restored value."""
    if not source_nodes:
        raise ValueError("source_nodes must include at least one node")

    blocked = _device_state_blocked_edges(graph)
    demand_map = demand_by_node or {}
    critical_set = set(critical_nodes or [])

    open_ties = [e for e in tie_edge_ids if e in graph.edge_attributes]
    closed_ties: set[str] = set()

    def _served_for_closed(closed: set[str]) -> set[str]:
        test_blocked = set(blocked)
        for tie in open_ties:
            attrs = graph.edge_attributes.get(tie, {})
            state = str(attrs.get("state", "")).lower()
            if state in {"open", "normally_open"} and tie not in closed:
                test_blocked.add(tie)
            elif tie in closed:
                test_blocked.discard(tie)
        dist, _, _, _ = _dijkstra(graph, source_nodes, max_cost, test_blocked, {})
        return set(dist.keys())

    current_served = _served_for_closed(closed_ties)
    actions: list[dict[str, Any]] = []

    for _ in range(max_switch_actions):
        best_tie: str | None = None
        best_row: dict[str, Any] | None = None
        best_served: set[str] | None = None

        for tie in open_ties:
            if tie in closed_ties:
                continue
            test_closed = set(closed_ties)
            test_closed.add(tie)
            test_served = _served_for_closed(test_closed)

            restored = sorted(test_served - current_served)
            restored_critical = sorted(n for n in restored if n in critical_set)
            restored_demand = sum(float(demand_map.get(n, 0) or 0) for n in restored)
            objective = (1000.0 * len(restored_critical)) + restored_demand + len(restored)

            row = {
                "tie_edge_id": tie,
                "restored_node_count": len(restored),
                "restored_nodes": restored,
                "restored_critical_count": len(restored_critical),
                "restored_critical_nodes": restored_critical,
                "restored_demand": round(restored_demand, 4),
                "objective_gain": round(objective, 4),
            }

            if best_row is None or objective > float(best_row["objective_gain"]):
                best_row = row
                best_tie = tie
                best_served = test_served

        if best_tie is None or best_row is None or best_served is None:
            break
        if best_row["restored_node_count"] <= 0:
            break

        closed_ties.add(best_tie)
        current_served = best_served
        actions.append(best_row)

    return {
        "switch_actions": actions,
        "closed_tie_edges": sorted(closed_ties),
        "final_served_node_count": len(current_served),
    }


def resilience_capex_prioritization(
    graph: NetworkGraph,
    project_candidates: list[dict[str, Any]],
    source_nodes: list[str],
    demand_by_node: dict[str, float] | None = None,
    critical_nodes: list[str] | None = None,
    max_cost: float = math.inf,
) -> list[dict[str, Any]]:
    """Rank candidate capital projects by resilience gain per capex unit."""
    demand_map = demand_by_node or {}
    critical = critical_nodes or []

    base_rows = n_minus_one_edge_contingency_screen(
        graph,
        source_nodes=source_nodes,
        demand_by_node=demand_map,
        critical_nodes=critical,
        max_cost=max_cost,
    )
    if base_rows:
        base_avg_lost_demand = sum(float(r["lost_demand"]) for r in base_rows) / len(base_rows)
        base_avg_lost_critical = sum(float(r["lost_critical_count"]) for r in base_rows) / len(base_rows)
    else:
        base_avg_lost_demand = 0.0
        base_avg_lost_critical = 0.0

    existing_edges: list[NetworkEdge] = [dict(attrs) for attrs in graph.edge_attributes.values()]
    output: list[dict[str, Any]] = []

    for project in project_candidates:
        project_id = str(project.get("project_id", ""))
        capex = float(project.get("capex_cost", 1.0) or 1.0)
        add_edges = [dict(e) for e in project.get("add_edges", [])]
        hardened_edges = set(str(e) for e in project.get("hardened_edge_ids", []))

        test_edges = existing_edges + add_edges
        test_graph = build_network_graph(test_edges, directed=graph.directed)

        candidates = [
            edge_id
            for edge_id in test_graph.edge_attributes.keys()
            if edge_id not in hardened_edges
        ]

        test_rows = n_minus_one_edge_contingency_screen(
            test_graph,
            source_nodes=source_nodes,
            demand_by_node=demand_map,
            candidate_edge_ids=candidates,
            critical_nodes=critical,
            max_cost=max_cost,
        )

        if test_rows:
            test_avg_lost_demand = sum(float(r["lost_demand"]) for r in test_rows) / len(test_rows)
            test_avg_lost_critical = sum(float(r["lost_critical_count"]) for r in test_rows) / len(test_rows)
        else:
            test_avg_lost_demand = 0.0
            test_avg_lost_critical = 0.0

        avoided_demand = max(0.0, base_avg_lost_demand - test_avg_lost_demand)
        avoided_critical = max(0.0, base_avg_lost_critical - test_avg_lost_critical)
        value = (1000.0 * avoided_critical) + avoided_demand
        score = value / max(1.0, capex)

        output.append(
            {
                "project_id": project_id,
                "capex_cost": round(capex, 4),
                "added_edge_count": len(add_edges),
                "hardened_edge_count": len(hardened_edges),
                "avg_lost_demand_baseline": round(base_avg_lost_demand, 4),
                "avg_lost_demand_with_project": round(test_avg_lost_demand, 4),
                "avg_lost_critical_baseline": round(base_avg_lost_critical, 4),
                "avg_lost_critical_with_project": round(test_avg_lost_critical, 4),
                "avoided_lost_demand": round(avoided_demand, 4),
                "avoided_lost_critical": round(avoided_critical, 4),
                "resilience_value_per_capex": round(score, 8),
            }
        )

    output.sort(key=lambda r: r["resilience_value_per_capex"], reverse=True)
    return output


__all__ = [
    "NetworkEdge",
    "NetworkGraph",
    "NetworkRouter",
    "Traversal",
    "allocate_demand_to_supply",
    "analyze_network_topology",
    "build_landmark_index",
    "build_network_graph",
    "capacity_constrained_od_assignment",
    "co_location_conflict_scan",
    "constrained_flow_assignment",
    "critical_customer_coverage_audit",
    "criticality_ranking_by_node_removal",
    "detention_basin_overflow_trace",
    "edge_impedance_cost",
    "feeder_load_balance_swap",
    "fiber_cut_impact_matrix",
    "fiber_splice_node_trace",
    "fire_flow_demand_check",
    "gas_odorization_zone_trace",
    "gas_pressure_drop_trace",
    "gas_regulator_station_isolation",
    "gas_shutdown_impact",
    "inflow_infiltration_scan",
    "infrastructure_age_risk_weighted_routing",
    "interdependency_cascade_simulation",
    "landmark_lower_bound",
    "load_transfer_feasibility",
    "multi_criteria_shortest_path",
    "n_minus_k_edge_contingency_screen",
    "n_minus_one_edge_contingency_screen",
    "od_cost_matrix",
    "crew_dispatch_optimizer",
    "outage_restoration_tie_options",
    "pressure_zone_reconfiguration_planner",
    "pump_station_failure_cascade",
    "feeder_reconfiguration_optimizer",
    "resilience_capex_prioritization",
    "pipe_break_isolation_zones",
    "pressure_reducing_valve_trace",
    "ring_redundancy_check",
    "run_utility_scenarios",
    "service_area",
    "shortest_path",
    "stormwater_flow_accumulation",
    "trace_electric_feeder",
    "trace_water_pressure_zones",
    "utility_bottlenecks",
    "utility_outage_isolation",
]
