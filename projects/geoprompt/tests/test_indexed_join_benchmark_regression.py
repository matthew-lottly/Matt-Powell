from __future__ import annotations

import os
import time

import pytest

from geoprompt.frame import GeoPromptFrame


BENCHMARK_ENABLED = os.environ.get("GEOPROMPT_RUN_BENCHMARKS") == "1"


def _grid_points(rows: int, cols: int, spacing: float = 0.01) -> GeoPromptFrame:
    records = []
    for row in range(rows):
        for col in range(cols):
            records.append(
                {
                    "site_id": f"p_{row}_{col}",
                    "group": "left" if (row + col) % 2 == 0 else "right",
                    "geometry": {
                        "type": "Point",
                        "coordinates": (-112.0 + col * spacing, 40.0 + row * spacing),
                    },
                }
            )
    return GeoPromptFrame.from_records(records, crs="EPSG:4326")


@pytest.mark.skipif(not BENCHMARK_ENABLED, reason="set GEOPROMPT_RUN_BENCHMARKS=1 to run benchmark regression checks")
def test_nearest_join_indexed_benchmark_budget() -> None:
    left = _grid_points(40, 40)
    right = _grid_points(40, 40)

    started = time.perf_counter()
    non_indexed = left.nearest_join(right, k=2, use_spatial_index=False)
    non_indexed_elapsed = time.perf_counter() - started

    started = time.perf_counter()
    indexed = left.nearest_join(right, k=2, use_spatial_index=True)
    indexed_elapsed = time.perf_counter() - started

    assert len(indexed) == len(non_indexed)
    assert indexed_elapsed <= non_indexed_elapsed * 1.5
    assert indexed_elapsed < 8.0


@pytest.mark.skipif(not BENCHMARK_ENABLED, reason="set GEOPROMPT_RUN_BENCHMARKS=1 to run benchmark regression checks")
def test_proximity_join_indexed_benchmark_budget() -> None:
    left = _grid_points(36, 36)
    right = _grid_points(36, 36)

    started = time.perf_counter()
    non_indexed = left.proximity_join(right, max_distance=0.015, use_spatial_index=False)
    non_indexed_elapsed = time.perf_counter() - started

    started = time.perf_counter()
    indexed = left.proximity_join(right, max_distance=0.015, use_spatial_index=True)
    indexed_elapsed = time.perf_counter() - started

    assert len(indexed) == len(non_indexed)
    assert indexed_elapsed <= non_indexed_elapsed * 1.5
    assert indexed_elapsed < 8.0


@pytest.mark.skipif(not BENCHMARK_ENABLED, reason="set GEOPROMPT_RUN_BENCHMARKS=1 to run benchmark regression checks")
def test_spatial_join_indexed_benchmark_budget() -> None:
    left = _grid_points(30, 30)
    right = _grid_points(30, 30)

    started = time.perf_counter()
    non_indexed = left.spatial_join(right, predicate="intersects", use_spatial_index=False)
    non_indexed_elapsed = time.perf_counter() - started

    started = time.perf_counter()
    indexed = left.spatial_join(right, predicate="intersects", use_spatial_index=True)
    indexed_elapsed = time.perf_counter() - started

    assert len(indexed) == len(non_indexed)
    assert indexed_elapsed <= non_indexed_elapsed * 1.5
    assert indexed_elapsed < 8.0
