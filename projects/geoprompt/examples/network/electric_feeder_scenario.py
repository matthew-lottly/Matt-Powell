from __future__ import annotations

from geoprompt.network import build_network_graph, run_utility_scenarios


def main() -> None:
    graph = build_network_graph(
        [
            {"edge_id": "e1", "from_node": "S", "to_node": "A", "cost": 1.0, "capacity": 200.0},
            {"edge_id": "e2", "from_node": "A", "to_node": "B", "cost": 1.0, "capacity": 120.0},
            {"edge_id": "tie", "from_node": "S", "to_node": "B", "cost": 2.5, "capacity": 90.0, "device_type": "tie", "state": "normally_open"},
        ],
        directed=False,
    )

    scenarios = run_utility_scenarios(
        graph,
        source_nodes=["S"],
        outage_edges=["e2"],
        restoration_edges=["e2"],
    )
    print(scenarios)


if __name__ == "__main__":
    main()
