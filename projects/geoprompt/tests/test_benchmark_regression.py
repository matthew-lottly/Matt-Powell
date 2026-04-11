from __future__ import annotations

import os
import time

import pytest

from geoprompt.network import build_network_graph, shortest_path, utility_bottlenecks_stream


def _grid_graph(rows: int, cols: int):
    edges = []
    for r in range(rows):
        for c in range(cols):
            node = f"n{r}_{c}"
            if c + 1 < cols:
                edges.append(
                    {
                        "edge_id": f"e_h_{r}_{c}",
                        "from_node": node,
                        "to_node": f"n{r}_{c+1}",
                        "cost": 1.0,
                        "capacity": 100.0,
                    }
                )
            if r + 1 < rows:
                edges.append(
                    {
                        "edge_id": f"e_v_{r}_{c}",
                        "from_node": node,
                        "to_node": f"n{r+1}_{c}",
                        "cost": 1.0,
                        "capacity": 100.0,
                    }
                )
    return build_network_graph(edges, directed=False)


BENCHMARK_ENABLED = os.environ.get("GEOPROMPT_RUN_BENCHMARKS") == "1"


@pytest.mark.skipif(not BENCHMARK_ENABLED, reason="set GEOPROMPT_RUN_BENCHMARKS=1 to run benchmark regression checks")
def test_shortest_path_regression_budget() -> None:
    graph = _grid_graph(30, 30)
    pairs = [("n0_0", "n29_29"), ("n0_15", "n29_15"), ("n10_10", "n20_20")]

    started = time.perf_counter()
    for _ in range(60):
        for origin, destination in pairs:
            shortest_path(graph, origin, destination)
    elapsed = time.perf_counter() - started

    # Budget is intentionally generous and only meant to catch major regressions.
    assert elapsed < 8.0


@pytest.mark.skipif(not BENCHMARK_ENABLED, reason="set GEOPROMPT_RUN_BENCHMARKS=1 to run benchmark regression checks")
def test_stream_bottlenecks_regression_budget() -> None:
    graph = _grid_graph(25, 25)
    demands = [(f"n0_{i}", f"n24_{i}", 2.0) for i in range(25)] * 40

    started = time.perf_counter()
    rows = utility_bottlenecks_stream(graph, demands, demand_batch_size=200)
    elapsed = time.perf_counter() - started

    assert rows
    assert elapsed < 8.0