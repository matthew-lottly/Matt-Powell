from __future__ import annotations

from geoprompt.network import (
    build_network_graph,
    fire_flow_demand_check,
    trace_water_pressure_zones,
)


def main() -> None:
    graph = build_network_graph(
        [
            {"edge_id": "p1", "from_node": "PLANT", "to_node": "N1", "cost": 1.2, "capacity": 2000.0, "flow": 600.0},
            {"edge_id": "p2", "from_node": "N1", "to_node": "N2", "cost": 1.6, "capacity": 1500.0, "flow": 700.0},
            {"edge_id": "p3", "from_node": "N2", "to_node": "HYD", "cost": 0.9, "capacity": 1200.0, "flow": 500.0},
        ],
        directed=False,
    )

    pressure = trace_water_pressure_zones(graph, source_nodes=["PLANT"], max_headloss=5.0)
    fire = fire_flow_demand_check(graph, hydrant_nodes=["HYD"], demand_gpm=1000.0)
    print("pressure", pressure)
    print("fire", fire)


if __name__ == "__main__":
    main()
