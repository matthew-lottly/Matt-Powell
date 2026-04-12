"""Network topology diagnostics and cross-network conflict scans."""

from __future__ import annotations

from collections import deque
from itertools import combinations
from typing import Any

from .core import NetworkGraph


def analyze_network_topology(graph: NetworkGraph) -> dict[str, Any]:
    """Summarize graph structure for QA and topology screening."""
    self_loops: list[str] = []
    duplicate_pairs: list[dict[str, str]] = []
    seen_pairs: dict[frozenset[str], str] = {}

    for edge_id, edge in graph.edge_attributes.items():
        from_node = str(edge.get("from_node", ""))
        to_node = str(edge.get("to_node", ""))
        if from_node == to_node:
            self_loops.append(edge_id)
        pair_key = frozenset((from_node, to_node))
        if pair_key in seen_pairs:
            duplicate_pairs.append(
                {
                    "first_edge_id": seen_pairs[pair_key],
                    "duplicate_edge_id": edge_id,
                    "from_node": from_node,
                    "to_node": to_node,
                }
            )
        else:
            seen_pairs[pair_key] = edge_id

    visited: set[str] = set()
    component_count = 0
    for start in graph.adjacency:
        if start in visited:
            continue
        component_count += 1
        queue: deque[str] = deque([start])
        visited.add(start)
        while queue:
            node = queue.popleft()
            for step in graph.adjacency.get(node, []):
                if step.to_node not in visited:
                    visited.add(step.to_node)
                    queue.append(step.to_node)

    return {
        "node_count": len(graph.adjacency),
        "edge_count": len(graph.edge_attributes),
        "component_count": component_count,
        "self_loop_edge_ids": sorted(self_loops),
        "duplicate_edge_pairs": duplicate_pairs,
    }


def co_location_conflict_scan(networks: dict[str, NetworkGraph]) -> list[dict[str, Any]]:
    """Find shared node-pair corridors between utility networks."""
    rows: list[dict[str, Any]] = []
    for service_a, service_b in combinations(sorted(networks.keys()), 2):
        graph_a = networks[service_a]
        graph_b = networks[service_b]

        pairs_a: set[frozenset[str]] = set()
        for edge in graph_a.edge_attributes.values():
            pairs_a.add(frozenset((str(edge.get("from_node", "")), str(edge.get("to_node", "")))))

        pairs_b: set[frozenset[str]] = set()
        for edge in graph_b.edge_attributes.values():
            pairs_b.add(frozenset((str(edge.get("from_node", "")), str(edge.get("to_node", "")))))

        for shared in sorted(pairs_a.intersection(pairs_b), key=lambda item: sorted(item)):
            nodes = sorted(shared)
            rows.append(
                {
                    "service_a": service_a,
                    "service_b": service_b,
                    "conflict_type": "shared_node_pair",
                    "node_a": nodes[0] if nodes else "",
                    "node_b": nodes[1] if len(nodes) > 1 else nodes[0] if nodes else "",
                }
            )
    return rows
