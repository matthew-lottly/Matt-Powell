from __future__ import annotations

from geoprompt.network import (
    build_network_graph,
    fiber_cut_impact_matrix,
    ring_redundancy_check,
)


def main() -> None:
    graph = build_network_graph(
        [
            {"edge_id": "a", "from_node": "HUB", "to_node": "A", "cost": 1.0},
            {"edge_id": "b", "from_node": "A", "to_node": "B", "cost": 1.0},
            {"edge_id": "c", "from_node": "B", "to_node": "C", "cost": 1.0},
            {"edge_id": "d", "from_node": "C", "to_node": "HUB", "cost": 1.0},
        ],
        directed=False,
    )

    ring = ring_redundancy_check(graph, ring_nodes=["A", "B", "C"], hub_node="HUB")
    impact = fiber_cut_impact_matrix(graph, cut_candidate_edges=["a", "b", "c", "d"], circuit_endpoints=[("A", "C"), ("HUB", "B")])

    print("ring", ring)
    print("impact", impact)


if __name__ == "__main__":
    main()
