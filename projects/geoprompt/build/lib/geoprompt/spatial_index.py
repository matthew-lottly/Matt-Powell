from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal, Sequence


BoundsTuple = tuple[float, float, float, float]
Coordinate = tuple[float, float]
SpatialIndexQueryMode = Literal["intersects", "within", "contains"]


def _bounds_intersect(left: BoundsTuple, right: BoundsTuple) -> bool:
    return not (
        left[2] < right[0]
        or left[0] > right[2]
        or left[3] < right[1]
        or left[1] > right[3]
    )


def _bounds_within(candidate: BoundsTuple, container: BoundsTuple) -> bool:
    return (
        candidate[0] >= container[0]
        and candidate[1] >= container[1]
        and candidate[2] <= container[2]
        and candidate[3] <= container[3]
    )


def _point_bounds(point: Coordinate) -> BoundsTuple:
    return (point[0], point[1], point[0], point[1])


def _resolve_cell_size(bounds: Sequence[BoundsTuple], requested: float | None) -> float:
    if requested is not None:
        if requested <= 0:
            raise ValueError("cell_size must be greater than zero")
        return float(requested)
    if not bounds:
        return 1.0

    min_x = min(bound[0] for bound in bounds)
    min_y = min(bound[1] for bound in bounds)
    max_x = max(bound[2] for bound in bounds)
    max_y = max(bound[3] for bound in bounds)
    extent = max(max_x - min_x, max_y - min_y, 1e-9)
    average_span = max(
        sum(max(bound[2] - bound[0], bound[3] - bound[1], 1e-9) for bound in bounds) / len(bounds),
        1e-9,
    )
    target_cells = max(int(math.sqrt(len(bounds))), 1)
    return max(average_span, extent / target_cells, 1e-9)


@dataclass(frozen=True)
class SpatialIndexStats:
    item_count: int
    cell_count: int
    cell_size: float


class SpatialIndex:
    def __init__(self, bounds: Sequence[BoundsTuple], cell_size: float | None = None) -> None:
        self._bounds = [
            (float(min_x), float(min_y), float(max_x), float(max_y))
            for min_x, min_y, max_x, max_y in bounds
        ]
        self.cell_size = _resolve_cell_size(self._bounds, cell_size)
        self._cells: dict[tuple[int, int], list[int]] = {}
        for index, bound in enumerate(self._bounds):
            for cell in self._iter_cells(bound):
                self._cells.setdefault(cell, []).append(index)

    @classmethod
    def from_points(cls, coordinates: Sequence[Coordinate], cell_size: float | None = None) -> "SpatialIndex":
        return cls([_point_bounds(point) for point in coordinates], cell_size=cell_size)

    def __len__(self) -> int:
        return len(self._bounds)

    def stats(self) -> SpatialIndexStats:
        return SpatialIndexStats(item_count=len(self._bounds), cell_count=len(self._cells), cell_size=self.cell_size)

    def query(self, bounds: BoundsTuple, mode: SpatialIndexQueryMode = "intersects") -> list[int]:
        if mode == "intersects":
            predicate = _bounds_intersect
        elif mode == "within":
            predicate = _bounds_within
        elif mode == "contains":
            predicate = lambda candidate, query: _bounds_within(query, candidate)
        else:
            raise ValueError("mode must be 'intersects', 'within', or 'contains'")

        candidate_indexes: set[int] = set()
        for cell in self._iter_cells(bounds):
            candidate_indexes.update(self._cells.get(cell, []))
        return sorted(index for index in candidate_indexes if predicate(self._bounds[index], bounds))

    def _iter_cells(self, bounds: BoundsTuple) -> list[tuple[int, int]]:
        min_x, min_y, max_x, max_y = bounds
        start_x = math.floor(min_x / self.cell_size)
        end_x = math.floor(max_x / self.cell_size)
        start_y = math.floor(min_y / self.cell_size)
        end_y = math.floor(max_y / self.cell_size)

        cells: list[tuple[int, int]] = []
        for cell_x in range(start_x, end_x + 1):
            for cell_y in range(start_y, end_y + 1):
                cells.append((cell_x, cell_y))
        return cells


__all__ = ["SpatialIndex", "SpatialIndexQueryMode", "SpatialIndexStats"]