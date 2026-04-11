"""Micro-benchmark suite for geoprompt.network core algorithms.

Run: python benchmarks/bench_network.py
"""
from __future__ import annotations

import random
import time

from geoprompt.network import (
    NetworkGraph,
    build_network_graph,
    od_cost_matrix,
    run_utility_scenarios,
    service_area,
    shortest_path,
    utility_bottlenecks,
    NetworkRouter,
)


def _grid_graph(rows: int, cols: int, seed: int = 42) -> NetworkGraph:
    """Build a grid network with *rows x cols* nodes."""
    rng = random.Random(seed)
    edges: list[dict] = []
    for r in range(rows):
        for c in range(cols):
            node = f"n{r}_{c}"
            if c + 1 < cols:
                right = f"n{r}_{c + 1}"
                cost = rng.uniform(0.5, 5.0)
                edges.append(
                    {
                        "edge_id": f"e_{node}_{right}",
                        "from_node": node,
                        "to_node": right,
                        "cost": cost,
                        "capacity": rng.uniform(50, 200),
                    }
                )
            if r + 1 < rows:
                down = f"n{r + 1}_{c}"
                cost = rng.uniform(0.5, 5.0)
                edges.append(
                    {
                        "edge_id": f"e_{node}_{down}",
                        "from_node": node,
                        "to_node": down,
                        "cost": cost,
                        "capacity": rng.uniform(50, 200),
                    }
                )
    return build_network_graph(edges, directed=False)


def bench(name: str, func, *args, repeats: int = 3, **kwargs) -> None:
    times = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        func(*args, **kwargs)
        times.append(time.perf_counter() - t0)
    avg = sum(times) / len(times)
    best = min(times)
    print(f"{name:50s}  avg={avg:.4f}s  best={best:.4f}s  (n={repeats})")


def main() -> None:
    print("=" * 78)
    print("GeoPrompt Network Benchmark Suite")
    print("=" * 78)

    for size_label, rows, cols in [("small 5x5", 5, 5), ("medium 10x10", 10, 10), ("large 20x20", 20, 20)]:
        graph = _grid_graph(rows, cols)
        node_count = len(graph.nodes)
        edge_count = len(graph.edge_attributes)
        print(f"\n--- {size_label}  ({node_count} nodes, {edge_count} edges) ---")

        origin = "n0_0"
        dest = f"n{rows - 1}_{cols - 1}"

        bench(f"shortest_path ({size_label})", shortest_path, graph, origin, dest)
        bench(f"service_area ({size_label})", service_area, graph, [origin], max_cost=50.0)
        bench(
            f"od_cost_matrix 4x4 ({size_label})",
            od_cost_matrix,
            graph,
            origins=[f"n0_{c}" for c in range(min(4, cols))],
            destinations=[f"n{rows - 1}_{c}" for c in range(min(4, cols))],
        )

        od_demands = [
            (f"n0_{c}", f"n{rows - 1}_{c}", 10.0) for c in range(min(4, cols))
        ]
        bench(f"utility_bottlenecks 4 OD ({size_label})", utility_bottlenecks, graph, od_demands)

    # --- NetworkRouter caching comparison ---
    print("\n--- NetworkRouter cache benefit (20x20 grid) ---")
    graph = _grid_graph(20, 20)
    router = NetworkRouter(graph)
    pairs = [("n0_0", "n19_19"), ("n0_0", "n10_10"), ("n5_5", "n15_15"), ("n0_0", "n0_19")]

    def _uncached_batch():
        for o, d in pairs:
            shortest_path(graph, o, d)

    def _cached_batch():
        for o, d in pairs:
            router.shortest_path(o, d)

    bench("shortest_path (uncached, 4 pairs)", _uncached_batch)
    bench("NetworkRouter  (cached, 4 pairs)", _cached_batch)

    # --- run_utility_scenarios on small graph ---
    print("\n--- run_utility_scenarios (5x5 grid) ---")
    small = _grid_graph(5, 5)
    supply = {"n0_0": 100.0}
    demand = {"n4_4": 50.0}
    bench(
        "run_utility_scenarios (5x5)",
        run_utility_scenarios,
        small,
        source_nodes=["n0_0"],
    )

    print("\n" + "=" * 78)
    print("Done.")


if __name__ == "__main__":
    main()
