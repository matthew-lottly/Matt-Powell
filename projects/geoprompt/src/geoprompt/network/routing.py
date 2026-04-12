"""Network routing: shortest paths, service areas, multi-criteria routing."""

from __future__ import annotations

import math
from heapq import heappop, heappush
from typing import TYPE_CHECKING, Any, cast

from .core import (
    NetworkEdge,
    NetworkGraph,
    Traversal,
    _as_node,
    _as_non_negative,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence


def build_network_graph(
    edges: Sequence[NetworkEdge],
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
        resolved_edge = cast(NetworkEdge, dict(edge))
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
    """Dijkstra shortest path algorithm from multiple origins.
    
    Returns distances, previous_node, previous_edge, and source_for_node.
    """
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
