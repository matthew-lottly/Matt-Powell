from __future__ import annotations

import heapq

import numpy as np


def _neighbors_8(r: int, c: int, rows: int, cols: int):
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                yield nr, nc


def cumulative_cost_distance(cost_raster: np.ndarray, source: tuple[int, int]) -> np.ndarray:
    rows, cols = cost_raster.shape
    sr, sc = source
    if not (0 <= sr < rows and 0 <= sc < cols):
        raise ValueError("Source cell is outside raster bounds")

    dist = np.full((rows, cols), np.inf, dtype=float)
    dist[sr, sc] = 0.0

    pq: list[tuple[float, int, int]] = [(0.0, sr, sc)]
    while pq:
        current, r, c = heapq.heappop(pq)
        if current > dist[r, c]:
            continue

        for nr, nc in _neighbors_8(r, c, rows, cols):
            step = 0.5 * (cost_raster[r, c] + cost_raster[nr, nc])
            candidate = current + step
            if candidate < dist[nr, nc]:
                dist[nr, nc] = candidate
                heapq.heappush(pq, (candidate, nr, nc))

    return dist


def least_cost_path(
    cumulative_cost: np.ndarray,
    source: tuple[int, int],
    target: tuple[int, int],
) -> list[tuple[int, int]]:
    rows, cols = cumulative_cost.shape
    tr, tc = target
    if not (0 <= tr < rows and 0 <= tc < cols):
        raise ValueError("Target cell is outside raster bounds")

    path = [target]
    r, c = target
    while (r, c) != source:
        options = [(cumulative_cost[nr, nc], nr, nc) for nr, nc in _neighbors_8(r, c, rows, cols)]
        best_cost, br, bc = min(options, key=lambda x: x[0])
        if not np.isfinite(best_cost):
            raise RuntimeError("Could not trace path to source; disconnected cost surface")
        if (br, bc) == (r, c):
            raise RuntimeError("Path tracing stalled")
        r, c = br, bc
        path.append((r, c))

    path.reverse()
    return path


def corridor_mask(cumulative_cost: np.ndarray, quantile: float) -> np.ndarray:
    if quantile <= 0 or quantile >= 1:
        raise ValueError("quantile must be between 0 and 1 (exclusive)")
    threshold = float(np.quantile(cumulative_cost[np.isfinite(cumulative_cost)], quantile))
    return cumulative_cost <= threshold
