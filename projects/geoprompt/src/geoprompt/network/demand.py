"""Network demand: origin-destination matrices, demand allocation, bottleneck analysis."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

from .core import NetworkGraph, _as_non_negative, _iter_chunks, get_network_workload_preset
from .routing import _dijkstra
from ..equations import utility_capacity_stress_index, utility_service_deficit

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Sequence


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
    for batch in iter_od_cost_matrix_batches(
        graph,
        origins=origins,
        destinations=destinations,
        origin_batch_size=max(1, len(origins) if origins else 1),
        max_cost=max_cost,
        blocked_edges=blocked_edges,
        edge_cost_overrides=edge_cost_overrides,
    ):
        rows.extend(batch)
    rows.sort(key=lambda item: (str(item["origin"]), str(item["destination"])))
    return rows


def od_cost_matrix_with_preset(
    graph: NetworkGraph,
    origins: list[str],
    destinations: list[str],
    *,
    preset: str = "large",
    max_cost: float | None = None,
    blocked_edges: Sequence[str] | None = None,
    edge_cost_overrides: dict[str, float] | None = None,
    origin_batch_size: int | None = None,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> list[dict[str, Any]]:
    """Convenience OD matrix wrapper using named batch-size presets."""
    settings = get_network_workload_preset(preset)
    batch_size = origin_batch_size if origin_batch_size is not None else settings["origin_batch_size"]
    rows: list[dict[str, Any]] = []
    for batch in iter_od_cost_matrix_batches(
        graph,
        origins=origins,
        destinations=destinations,
        origin_batch_size=batch_size,
        max_cost=max_cost,
        blocked_edges=blocked_edges,
        edge_cost_overrides=edge_cost_overrides,
        progress_callback=progress_callback,
    ):
        rows.extend(batch)
    rows.sort(key=lambda item: (str(item["origin"]), str(item["destination"])))
    return rows


def iter_od_cost_matrix_batches(
    graph: NetworkGraph,
    origins: Sequence[str],
    destinations: Sequence[str],
    origin_batch_size: int = 100,
    max_cost: float | None = None,
    blocked_edges: Sequence[str] | None = None,
    edge_cost_overrides: dict[str, float] | None = None,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> Iterable[list[dict[str, Any]]]:
    """Yield OD least-cost rows in origin-sized batches.

    This is intended for large workloads where materializing the full
    |origins| x |destinations| matrix at once is expensive.
    """
    if origin_batch_size <= 0:
        raise ValueError("origin_batch_size must be >= 1")
    blocked = set(blocked_edges or [])
    processed_origins = 0
    for origin_batch in _iter_chunks(origins, origin_batch_size):
        batch_rows: list[dict[str, Any]] = []
        for origin in origin_batch:
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
                batch_rows.append(
                    {
                        "origin": origin,
                        "destination": destination,
                        "reachable": math.isfinite(total_cost),
                        "least_cost": total_cost,
                    }
                )
            processed_origins += 1
        if progress_callback is not None:
            progress_callback(
                {
                    "event": "origin_batch",
                    "origin_batch_size": len(origin_batch),
                    "processed_origins": processed_origins,
                    "rows_emitted": len(batch_rows),
                }
            )
        yield batch_rows


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


def utility_bottlenecks_stream(
    graph: NetworkGraph,
    od_demands: Iterable[tuple[str, str, float]],
    capacity_field: str = "capacity",
    blocked_edges: Sequence[str] | None = None,
    edge_cost_overrides: dict[str, float] | None = None,
    demand_batch_size: int = 50000,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> list[dict[str, Any]]:
    """Streaming version of ``utility_bottlenecks`` for large OD demand sets."""
    if demand_batch_size <= 0:
        raise ValueError("demand_batch_size must be >= 1")
    edge_loads: dict[str, float] = {edge_id: 0.0 for edge_id in graph.edge_attributes}
    blocked = set(blocked_edges or [])
    processed_demands = 0

    for demand_batch in _iter_chunks(od_demands, demand_batch_size):
        processed_demands += len(demand_batch)
        origin_groups: dict[str, list[tuple[str, float]]] = {}
        for origin, destination, demand in demand_batch:
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
                current = destination
                while current != origin:
                    edge_id = prev_edge.get(current)
                    if edge_id is None:
                        break
                    edge_loads[edge_id] += demand_value
                    current = prev_node[current]
        if progress_callback is not None:
            progress_callback(
                {
                    "event": "demand_batch",
                    "batch_size": len(demand_batch),
                    "processed_demands": processed_demands,
                }
            )

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


def utility_bottlenecks_with_preset(
    graph: NetworkGraph,
    od_demands: Iterable[tuple[str, str, float]],
    *,
    preset: str = "large",
    capacity_field: str = "capacity",
    blocked_edges: Sequence[str] | None = None,
    edge_cost_overrides: dict[str, float] | None = None,
    demand_batch_size: int | None = None,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> list[dict[str, Any]]:
    """Convenience bottleneck wrapper using named batch-size presets."""
    settings = get_network_workload_preset(preset)
    batch_size = demand_batch_size if demand_batch_size is not None else settings["demand_batch_size"]
    return utility_bottlenecks_stream(
        graph,
        od_demands,
        capacity_field=capacity_field,
        blocked_edges=blocked_edges,
        edge_cost_overrides=edge_cost_overrides,
        demand_batch_size=batch_size,
        progress_callback=progress_callback,
    )
