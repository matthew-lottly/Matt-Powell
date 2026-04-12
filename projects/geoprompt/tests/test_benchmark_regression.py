from __future__ import annotations

import os
import time

import pytest

from geoprompt import GeoPromptFrame
from geoprompt.network import (
    build_network_graph,
    capacity_constrained_od_assignment,
    od_cost_matrix_with_preset,
    shortest_path,
    utility_bottlenecks_stream,
)


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


def _grid_points(rows: int, cols: int, spacing: float = 0.01) -> GeoPromptFrame:
    records = []
    for row in range(rows):
        for col in range(cols):
            records.append(
                {
                    "site_id": f"p_{row}_{col}",
                    "geometry": {
                        "type": "Point",
                        "coordinates": (-112.0 + col * spacing, 40.0 + row * spacing),
                    },
                }
            )
    return GeoPromptFrame.from_records(records, crs="EPSG:4326")


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


@pytest.mark.skipif(not BENCHMARK_ENABLED, reason="set GEOPROMPT_RUN_BENCHMARKS=1 to run benchmark regression checks")
def test_od_cost_matrix_regression_budget() -> None:
    graph = _grid_graph(35, 35)
    origins = [f"n0_{i}" for i in range(20)]
    destinations = [f"n34_{i}" for i in range(20)]

    started = time.perf_counter()
    rows = od_cost_matrix_with_preset(
        graph,
        origins=origins,
        destinations=destinations,
        preset="small",
        origin_batch_size=8,
    )
    elapsed = time.perf_counter() - started

    assert len(rows) == len(origins) * len(destinations)
    assert elapsed < 10.0


@pytest.mark.skipif(not BENCHMARK_ENABLED, reason="set GEOPROMPT_RUN_BENCHMARKS=1 to run benchmark regression checks")
def test_capacity_assignment_regression_budget() -> None:
    graph = _grid_graph(20, 20)
    demands = [(f"n0_{i}", f"n19_{i}", 3.0) for i in range(20)] * 25

    started = time.perf_counter()
    result = capacity_constrained_od_assignment(
        graph,
        od_demands=demands,
        max_rounds=4,
    )
    elapsed = time.perf_counter() - started

    assert result["total_requested"] > 0
    assert result["total_delivered"] >= 0
    assert elapsed < 10.0


@pytest.mark.skipif(not BENCHMARK_ENABLED, reason="set GEOPROMPT_RUN_BENCHMARKS=1 to run benchmark regression checks")
def test_indexed_join_regression_budget() -> None:
    left = _grid_points(30, 30)
    right = _grid_points(30, 30)

    started = time.perf_counter()
    non_indexed = left.nearest_join(right, k=2, use_spatial_index=False)
    non_indexed_elapsed = time.perf_counter() - started

    started = time.perf_counter()
    indexed = left.nearest_join(right, k=2, use_spatial_index=True)
    indexed_elapsed = time.perf_counter() - started

    assert len(indexed) == len(non_indexed)
    assert indexed_elapsed <= non_indexed_elapsed * 1.5
    assert indexed_elapsed < 8.0