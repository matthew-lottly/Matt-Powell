from __future__ import annotations

from geoprompt.network import (
    build_network_graph,
    detention_basin_overflow_trace,
    inflow_infiltration_scan,
    stormwater_flow_accumulation,
)


def main() -> None:
    graph = build_network_graph(
        [
            {"edge_id": "e1", "from_node": "inlet-1", "to_node": "junction", "cost": 1.0, "capacity": 35.0, "observed_flow": 52.0, "dry_weather_flow": 30.0},
            {"edge_id": "e2", "from_node": "inlet-2", "to_node": "junction", "cost": 1.0, "capacity": 35.0, "observed_flow": 45.0, "dry_weather_flow": 28.0},
            {"edge_id": "e3", "from_node": "junction", "to_node": "basin", "cost": 1.0, "capacity": 70.0, "observed_flow": 80.0, "dry_weather_flow": 35.0},
        ],
        directed=True,
    )

    accumulation = stormwater_flow_accumulation(graph, runoff_by_node={"inlet-1": 12.0, "inlet-2": 9.0, "junction": 3.0})
    overflow = detention_basin_overflow_trace(graph, basin_node="basin", basin_capacity=20.0, inflow=24.0)
    infiltration = inflow_infiltration_scan(graph, infiltration_threshold_ratio=1.4)

    print("accumulation", accumulation)
    print("overflow", overflow)
    print("infiltration", infiltration)


if __name__ == "__main__":
    main()
