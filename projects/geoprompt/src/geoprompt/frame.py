from __future__ import annotations

import importlib
import math
import random
from dataclasses import dataclass
from heapq import heappop, heappush, nsmallest
from typing import Any, Iterable, Literal, Sequence

from .equations import accessibility_index, area_similarity, coordinate_distance, corridor_strength, directional_alignment, gravity_model, prompt_decay, prompt_influence, prompt_interaction
from .geometry import Geometry, geometry_area, geometry_bounds, geometry_centroid, geometry_contains, geometry_convex_hull, geometry_distance, geometry_envelope, geometry_intersects, geometry_intersects_bounds, geometry_length, geometry_type, geometry_vertices, geometry_within, geometry_within_bounds, normalize_geometry, transform_geometry
from .overlay import buffer_geometries, clip_geometries, dissolve_geometries, overlay_intersections, overlay_union_faces, polygon_split_faces
from .spatial_index import SpatialIndex


Record = dict[str, Any]
BoundsQueryMode = Literal["intersects", "within", "centroid"]
SpatialJoinPredicate = Literal["intersects", "within", "contains"]
SpatialJoinMode = Literal["inner", "left"]
AggregationName = Literal["sum", "mean", "min", "max", "first", "count"]
OverlayNormalizeMode = Literal["left", "right", "both"]
ZoneGroupAggregation = Literal["max", "mean", "sum"]
CorridorDistanceMode = Literal["direct", "network"]
CorridorScoreMode = Literal["distance", "strength", "alignment", "combined"]
ClusterRecommendMetric = Literal["silhouette", "sse"]
CorridorPathAnchor = Literal["start", "end", "nearest"]
GridShape = Literal["fishnet", "hexbin"]
SpatialLagMode = Literal["k_nearest", "distance_band", "intersects"]
SpatialLagWeightMode = Literal["binary", "inverse_distance"]
ChangeClass = Literal["unchanged", "moved", "modified", "split", "merge", "removed", "added"]
TrajectoryTransitionMode = Literal["network_cost", "hmm"]


Coordinate = tuple[float, float]


def _row_sort_key(row: Record) -> str:
    return str(row.get("site_id", row.get("region_id", "")))


def _bounds_intersect(left: tuple[float, float, float, float], right: tuple[float, float, float, float]) -> bool:
    return not (
        left[2] < right[0]
        or left[0] > right[2]
        or left[3] < right[1]
        or left[1] > right[3]
    )


def _bounds_within(candidate: tuple[float, float, float, float], container: tuple[float, float, float, float]) -> bool:
    return (
        candidate[0] >= container[0]
        and candidate[1] >= container[1]
        and candidate[2] <= container[2]
        and candidate[3] <= container[3]
    )


@dataclass(frozen=True)
class Bounds:
    min_x: float
    min_y: float
    max_x: float
    max_y: float


class GeoPromptFrame:
    def __init__(self, rows: Sequence[Record], geometry_column: str = "geometry", crs: str | None = None) -> None:
        self.geometry_column = geometry_column
        self.crs = crs
        self._rows = [dict(row) for row in rows]
        self._cache: dict[tuple[Any, ...], Any] = {}
        for row in self._rows:
            row[self.geometry_column] = normalize_geometry(row[self.geometry_column])

    @classmethod
    def from_records(cls, records: Iterable[Record], geometry: str = "geometry", crs: str | None = None) -> "GeoPromptFrame":
        return cls(list(records), geometry_column=geometry, crs=crs)

    @classmethod
    def _from_internal_rows(
        cls,
        rows: Sequence[Record],
        geometry_column: str = "geometry",
        crs: str | None = None,
    ) -> "GeoPromptFrame":
        frame = cls.__new__(cls)
        frame.geometry_column = geometry_column
        frame.crs = crs
        frame._rows = [dict(row) for row in rows]
        frame._cache = {}
        return frame

    def __len__(self) -> int:
        return len(self._rows)

    def __iter__(self):
        return iter(self._rows)

    def __repr__(self) -> str:
        geometry_col = self.geometry_column
        row_count = len(self._rows)
        col_count = len(self.columns)
        crs_label = self.crs or "None"
        return f"GeoPromptFrame({row_count} rows, {col_count} columns, crs={crs_label})"

    def __getitem__(self, name: str) -> list[Any]:
        return [row.get(name) for row in self._rows]

    @property
    def columns(self) -> list[str]:
        return list(self._rows[0].keys()) if self._rows else []

    def head(self, count: int = 5) -> list[Record]:
        return [dict(row) for row in self._rows[:count]]

    def to_records(self) -> list[Record]:
        return [dict(row) for row in self._rows]

    def bounds(self) -> Bounds:
        xs: list[float] = []
        ys: list[float] = []
        for row in self._rows:
            min_x, min_y, max_x, max_y = geometry_bounds(row[self.geometry_column])
            xs.extend([min_x, max_x])
            ys.extend([min_y, max_y])
        return Bounds(min_x=min(xs), min_y=min(ys), max_x=max(xs), max_y=max(ys))

    def centroid(self) -> Coordinate:
        centroids = [geometry_centroid(row[self.geometry_column]) for row in self._rows]
        xs = [coord[0] for coord in centroids]
        ys = [coord[1] for coord in centroids]
        return (sum(xs) / len(xs), sum(ys) / len(ys))

    def _centroids(self, rows: Sequence[Record] | None = None, geometry_column: str | None = None) -> list[Coordinate]:
        active_rows = rows if rows is not None else self._rows
        active_geometry_column = geometry_column or self.geometry_column
        return [geometry_centroid(row[active_geometry_column]) for row in active_rows]

    def spatial_index(self, mode: Literal["geometry", "centroid"] = "geometry", cell_size: float | None = None) -> SpatialIndex:
        cache_key = ("spatial_index", mode, None if cell_size is None else float(cell_size))
        if cache_key in self._cache:
            return self._cache[cache_key]
        if mode == "geometry":
            index = SpatialIndex([geometry_bounds(row[self.geometry_column]) for row in self._rows], cell_size=cell_size)
            self._cache[cache_key] = index
            return index
        if mode == "centroid":
            index = SpatialIndex.from_points(self._centroids(), cell_size=cell_size)
            self._cache[cache_key] = index
            return index
        raise ValueError("mode must be 'geometry' or 'centroid'")

    def _resolve_anchor_geometry(self, anchor: str | Geometry | Coordinate, id_column: str) -> tuple[Geometry, str | None]:
        if isinstance(anchor, str):
            self._require_column(id_column)
            anchor_row = next((row for row in self._rows if str(row[id_column]) == anchor), None)
            if anchor_row is None:
                raise KeyError(f"anchor '{anchor}' was not found in column '{id_column}'")
            return anchor_row[self.geometry_column], anchor
        return normalize_geometry(anchor), None

    def _aggregate_rows(
        self,
        rows: Sequence[Record],
        aggregations: dict[str, AggregationName] | None,
        suffix: str,
    ) -> dict[str, Any]:
        aggregate_values: dict[str, Any] = {}
        for column, operation in (aggregations or {}).items():
            values = [row[column] for row in rows if column in row and row[column] is not None]
            output_name = f"{column}_{operation}_{suffix}"
            if not values:
                aggregate_values[output_name] = None
                continue
            if operation == "sum":
                aggregate_values[output_name] = sum(float(value) for value in values)
            elif operation == "mean":
                aggregate_values[output_name] = sum(float(value) for value in values) / len(values)
            elif operation == "min":
                aggregate_values[output_name] = min(values)
            elif operation == "max":
                aggregate_values[output_name] = max(values)
            elif operation == "first":
                aggregate_values[output_name] = values[0]
            elif operation == "count":
                aggregate_values[output_name] = len(values)
            else:
                raise ValueError(f"unsupported aggregation: {operation}")
        return aggregate_values

    def distance_matrix(self, distance_method: str = "euclidean") -> list[list[float]]:
        return [
            [
                geometry_distance(origin=row[self.geometry_column], destination=other[self.geometry_column], method=distance_method)
                for other in self._rows
            ]
            for row in self._rows
        ]

    def geometry_types(self) -> list[str]:
        return [geometry_type(row[self.geometry_column]) for row in self._rows]

    def geometry_lengths(self) -> list[float]:
        return [geometry_length(row[self.geometry_column]) for row in self._rows]

    def geometry_areas(self) -> list[float]:
        return [geometry_area(row[self.geometry_column]) for row in self._rows]

    def nearest_neighbors(
        self,
        id_column: str = "site_id",
        k: int = 1,
        distance_method: str = "euclidean",
    ) -> list[Record]:
        self._require_column(id_column)
        if k <= 0:
            raise ValueError("k must be greater than zero")

        centroids = self._centroids()
        geometry_types = self.geometry_types()
        nearest: list[Record] = []
        for origin_index, origin in enumerate(self._rows):
            candidates = [
                (
                    destination,
                    geometry_types[destination_index],
                    coordinate_distance(centroids[origin_index], centroids[destination_index], method=distance_method),
                )
                for destination_index, destination in enumerate(self._rows)
                if destination_index != origin_index
            ]
            for rank, (destination, destination_geometry_type, distance_value) in enumerate(
                nsmallest(k, candidates, key=lambda item: (float(item[2]), _row_sort_key(item[0]))),
                start=1,
            ):
                nearest.append(
                    {
                        "origin": origin[id_column],
                        "neighbor": destination[id_column],
                        "distance": distance_value,
                        "origin_geometry_type": geometry_types[origin_index],
                        "neighbor_geometry_type": destination_geometry_type,
                        "rank": rank,
                        "distance_method": distance_method,
                    }
                )
        return nearest

    def _nearest_row_matches(
        self,
        origin_centroid: Coordinate,
        right_rows: Sequence[Record],
        right_centroids: Sequence[Coordinate],
        k: int,
        distance_method: str,
        max_distance: float | None = None,
        candidate_indexes: Sequence[int] | None = None,
    ) -> list[tuple[Record, float]]:
        candidates: list[tuple[Record, float]] = []
        indexes = candidate_indexes if candidate_indexes is not None else range(len(right_rows))
        for index in indexes:
            right_row = right_rows[index]
            right_centroid = right_centroids[index]
            if max_distance is not None and distance_method == "euclidean":
                if abs(origin_centroid[0] - right_centroid[0]) > max_distance or abs(origin_centroid[1] - right_centroid[1]) > max_distance:
                    continue
            distance_value = coordinate_distance(origin_centroid, right_centroid, method=distance_method)
            if max_distance is None or distance_value <= max_distance:
                candidates.append((right_row, distance_value))
        return nsmallest(k, candidates, key=lambda item: (float(item[1]), _row_sort_key(item[0])))

    def nearest_join(
        self,
        other: "GeoPromptFrame",
        k: int = 1,
        how: SpatialJoinMode = "inner",
        lsuffix: str = "left",
        rsuffix: str = "right",
        max_distance: float | None = None,
        distance_method: str = "euclidean",
    ) -> "GeoPromptFrame":
        if k <= 0:
            raise ValueError("k must be greater than zero")
        if how not in {"inner", "left"}:
            raise ValueError("how must be 'inner' or 'left'")
        if max_distance is not None and max_distance < 0:
            raise ValueError("max_distance must be zero or greater")
        if self.crs and other.crs and self.crs != other.crs:
            raise ValueError("frames must share the same CRS before nearest joins")

        right_rows = list(other._rows)
        right_columns = [column for column in other.columns if column != other.geometry_column]
        left_centroids = self._centroids()
        right_centroids = other._centroids()
        right_index = other.spatial_index(mode="centroid", cell_size=max_distance) if distance_method == "euclidean" and max_distance is not None and right_rows else None
        joined_rows: list[Record] = []

        for left_row, left_centroid in zip(self._rows, left_centroids, strict=True):
            candidate_indexes = None
            if right_index is not None and max_distance is not None:
                candidate_indexes = right_index.query(
                    (
                        left_centroid[0] - max_distance,
                        left_centroid[1] - max_distance,
                        left_centroid[0] + max_distance,
                        left_centroid[1] + max_distance,
                    )
                )
            row_matches = self._nearest_row_matches(
                origin_centroid=left_centroid,
                right_rows=right_rows,
                right_centroids=right_centroids,
                k=k,
                distance_method=distance_method,
                max_distance=max_distance,
                candidate_indexes=candidate_indexes,
            )

            if not row_matches and how == "left":
                merged_row = dict(left_row)
                for column in right_columns:
                    target_name = column if column not in merged_row else f"{column}_{rsuffix}"
                    merged_row[target_name] = None
                merged_row[f"{other.geometry_column}_{rsuffix}"] = None
                merged_row[f"distance_{rsuffix}"] = None
                merged_row[f"distance_method_{rsuffix}"] = distance_method
                merged_row[f"nearest_rank_{rsuffix}"] = None
                joined_rows.append(merged_row)

            for rank, (right_row, distance_value) in enumerate(row_matches, start=1):
                merged_row = dict(left_row)
                for column in right_columns:
                    target_name = column if column not in merged_row else f"{column}_{rsuffix}"
                    merged_row[target_name] = right_row[column]
                merged_row[f"{other.geometry_column}_{rsuffix}"] = right_row[other.geometry_column]
                merged_row[f"distance_{rsuffix}"] = distance_value
                merged_row[f"distance_method_{rsuffix}"] = distance_method
                merged_row[f"nearest_rank_{rsuffix}"] = rank
                joined_rows.append(merged_row)

        return GeoPromptFrame._from_internal_rows(joined_rows, geometry_column=self.geometry_column, crs=self.crs or other.crs)

    def assign_nearest(
        self,
        targets: "GeoPromptFrame",
        how: SpatialJoinMode = "inner",
        max_distance: float | None = None,
        distance_method: str = "euclidean",
        origin_suffix: str = "origin",
    ) -> "GeoPromptFrame":
        if how not in {"inner", "left"}:
            raise ValueError("how must be 'inner' or 'left'")
        if max_distance is not None and max_distance < 0:
            raise ValueError("max_distance must be zero or greater")
        return targets.nearest_join(
            self,
            k=1,
            how=how,
            rsuffix=origin_suffix,
            max_distance=max_distance,
            distance_method=distance_method,
        )

    def summarize_assignments(
        self,
        targets: "GeoPromptFrame",
        origin_id_column: str = "site_id",
        target_id_column: str = "site_id",
        aggregations: dict[str, AggregationName] | None = None,
        how: SpatialJoinMode = "left",
        max_distance: float | None = None,
        distance_method: str = "euclidean",
        assignment_suffix: str = "assigned",
    ) -> "GeoPromptFrame":
        if how not in {"inner", "left"}:
            raise ValueError("how must be 'inner' or 'left'")
        if max_distance is not None and max_distance < 0:
            raise ValueError("max_distance must be zero or greater")
        if self.crs and targets.crs and self.crs != targets.crs:
            raise ValueError("frames must share the same CRS before assignment summaries")

        self._require_column(origin_id_column)
        targets._require_column(target_id_column)

        origin_centroids = self._centroids()
        target_rows = list(targets._rows)
        target_centroids = targets._centroids()
        origin_index = self.spatial_index(mode="centroid", cell_size=max_distance) if distance_method == "euclidean" and max_distance is not None and self._rows else None
        assignments: dict[str, list[tuple[Record, float]]] = {}

        for target_row, target_centroid in zip(target_rows, target_centroids, strict=True):
            candidate_indexes = None
            if origin_index is not None and max_distance is not None:
                candidate_indexes = origin_index.query(
                    (
                        target_centroid[0] - max_distance,
                        target_centroid[1] - max_distance,
                        target_centroid[0] + max_distance,
                        target_centroid[1] + max_distance,
                    )
                )
            row_matches = self._nearest_row_matches(
                origin_centroid=target_centroid,
                right_rows=self._rows,
                right_centroids=origin_centroids,
                k=1,
                distance_method=distance_method,
                max_distance=max_distance,
                candidate_indexes=candidate_indexes,
            )
            if not row_matches:
                continue
            origin_row, distance_value = row_matches[0]
            origin_key = str(origin_row[origin_id_column])
            assignments.setdefault(origin_key, []).append((target_row, distance_value))

        rows: list[Record] = []
        for origin_row in self._rows:
            origin_key = str(origin_row[origin_id_column])
            assigned_matches = assignments.get(origin_key, [])
            if not assigned_matches and how == "inner":
                continue

            assigned_rows = [row for row, _ in assigned_matches]
            assigned_distances = [distance for _, distance in assigned_matches]
            resolved_row = dict(origin_row)
            resolved_row[f"{target_id_column}s_{assignment_suffix}"] = [str(row[target_id_column]) for row in assigned_rows]
            resolved_row[f"count_{assignment_suffix}"] = len(assigned_rows)
            resolved_row[f"distance_method_{assignment_suffix}"] = distance_method
            resolved_row[f"distance_min_{assignment_suffix}"] = min(assigned_distances) if assigned_distances else None
            resolved_row[f"distance_max_{assignment_suffix}"] = max(assigned_distances) if assigned_distances else None
            resolved_row[f"distance_mean_{assignment_suffix}"] = (
                sum(assigned_distances) / len(assigned_distances) if assigned_distances else None
            )
            resolved_row.update(self._aggregate_rows(assigned_rows, aggregations=aggregations, suffix=assignment_suffix))
            rows.append(resolved_row)

        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs or targets.crs)

    def catchment_competition(
        self,
        targets: "GeoPromptFrame",
        max_distance: float,
        origin_id_column: str = "site_id",
        target_id_column: str = "site_id",
        aggregations: dict[str, AggregationName] | None = None,
        how: SpatialJoinMode = "left",
        distance_method: str = "euclidean",
        competition_suffix: str = "catchment",
    ) -> "GeoPromptFrame":
        if max_distance < 0:
            raise ValueError("max_distance must be zero or greater")
        if how not in {"inner", "left"}:
            raise ValueError("how must be 'inner' or 'left'")
        if self.crs and targets.crs and self.crs != targets.crs:
            raise ValueError("frames must share the same CRS before catchment competition summaries")

        self._require_column(origin_id_column)
        targets._require_column(target_id_column)

        origin_centroids = self._centroids()
        target_rows = list(targets._rows)
        target_centroids = targets._centroids()
        origin_index = self.spatial_index(mode="centroid", cell_size=max_distance) if distance_method == "euclidean" and self._rows else None

        coverage_buckets: dict[str, dict[str, list[Record]]] = {
            str(origin_row[origin_id_column]): {
                "covered": [],
                "exclusive": [],
                "shared": [],
                "won": [],
            }
            for origin_row in self._rows
        }
        unserved_target_ids: list[str] = []

        for target_row, target_centroid in zip(target_rows, target_centroids, strict=True):
            candidate_indexes = None
            if origin_index is not None:
                candidate_indexes = origin_index.query(
                    (
                        target_centroid[0] - max_distance,
                        target_centroid[1] - max_distance,
                        target_centroid[0] + max_distance,
                        target_centroid[1] + max_distance,
                    )
                )
            row_matches = self._nearest_row_matches(
                origin_centroid=target_centroid,
                right_rows=self._rows,
                right_centroids=origin_centroids,
                k=len(self._rows),
                distance_method=distance_method,
                max_distance=max_distance,
                candidate_indexes=candidate_indexes,
            )
            if not row_matches:
                unserved_target_ids.append(str(target_row[target_id_column]))
                continue

            is_shared = len(row_matches) > 1
            for origin_row, _distance_value in row_matches:
                origin_key = str(origin_row[origin_id_column])
                coverage_buckets[origin_key]["covered"].append(target_row)
                coverage_buckets[origin_key]["shared" if is_shared else "exclusive"].append(target_row)

            winning_origin, _winning_distance = row_matches[0]
            coverage_buckets[str(winning_origin[origin_id_column])]["won"].append(target_row)

        rows: list[Record] = []
        for origin_row in self._rows:
            origin_key = str(origin_row[origin_id_column])
            bucket = coverage_buckets[origin_key]
            covered_rows = bucket["covered"]
            if not covered_rows and how == "inner":
                continue

            resolved_row = dict(origin_row)
            resolved_row[f"{target_id_column}s_{competition_suffix}"] = [str(row[target_id_column]) for row in covered_rows]
            resolved_row[f"count_{competition_suffix}"] = len(covered_rows)
            resolved_row[f"{target_id_column}s_exclusive_{competition_suffix}"] = [
                str(row[target_id_column]) for row in bucket["exclusive"]
            ]
            resolved_row[f"count_exclusive_{competition_suffix}"] = len(bucket["exclusive"])
            resolved_row[f"{target_id_column}s_shared_{competition_suffix}"] = [
                str(row[target_id_column]) for row in bucket["shared"]
            ]
            resolved_row[f"count_shared_{competition_suffix}"] = len(bucket["shared"])
            resolved_row[f"{target_id_column}s_won_{competition_suffix}"] = [
                str(row[target_id_column]) for row in bucket["won"]
            ]
            resolved_row[f"count_won_{competition_suffix}"] = len(bucket["won"])
            resolved_row[f"{target_id_column}s_unserved_{competition_suffix}"] = list(unserved_target_ids)
            resolved_row[f"count_unserved_{competition_suffix}"] = len(unserved_target_ids)
            resolved_row[f"distance_limit_{competition_suffix}"] = max_distance
            resolved_row[f"distance_method_{competition_suffix}"] = distance_method
            resolved_row.update(self._aggregate_rows(covered_rows, aggregations=aggregations, suffix=competition_suffix))
            rows.append(resolved_row)

        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs or targets.crs)

    def query_radius(
        self,
        anchor: str | Geometry | Coordinate,
        max_distance: float,
        id_column: str = "site_id",
        include_anchor: bool = False,
        distance_method: str = "euclidean",
    ) -> "GeoPromptFrame":
        if max_distance < 0:
            raise ValueError("max_distance must be zero or greater")

        anchor_geometry, anchor_id = self._resolve_anchor_geometry(anchor, id_column=id_column)
        anchor_centroid = geometry_centroid(anchor_geometry)
        centroid_index = self.spatial_index(mode="centroid", cell_size=max_distance) if distance_method == "euclidean" and self._rows else None
        candidate_indexes = (
            centroid_index.query(
                (
                    anchor_centroid[0] - max_distance,
                    anchor_centroid[1] - max_distance,
                    anchor_centroid[0] + max_distance,
                    anchor_centroid[1] + max_distance,
                )
            )
            if centroid_index is not None
            else list(range(len(self._rows)))
        )

        rows: list[Record] = []
        for index in candidate_indexes:
            row = self._rows[index]
            row_id = str(row.get(id_column)) if id_column in row else None
            distance_value = coordinate_distance(anchor_centroid, geometry_centroid(row[self.geometry_column]), method=distance_method)
            if anchor_id is not None and not include_anchor and row_id == anchor_id:
                continue
            if distance_value <= max_distance:
                resolved_row = dict(row)
                resolved_row["distance"] = distance_value
                resolved_row["distance_method"] = distance_method
                if anchor_id is not None:
                    resolved_row["anchor_id"] = anchor_id
                rows.append(resolved_row)

        rows.sort(key=lambda item: (float(item["distance"]), str(item.get(id_column, ""))))
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    def within_distance(
        self,
        anchor: str | Geometry | Coordinate,
        max_distance: float,
        id_column: str = "site_id",
        include_anchor: bool = False,
        distance_method: str = "euclidean",
    ) -> list[bool]:
        if max_distance < 0:
            raise ValueError("max_distance must be zero or greater")

        anchor_geometry, anchor_id = self._resolve_anchor_geometry(anchor, id_column=id_column)
        anchor_centroid = geometry_centroid(anchor_geometry)
        centroids = self._centroids()
        centroid_index = self.spatial_index(mode="centroid", cell_size=max_distance) if distance_method == "euclidean" and self._rows else None
        candidate_indexes = set(
            centroid_index.query(
                (
                    anchor_centroid[0] - max_distance,
                    anchor_centroid[1] - max_distance,
                    anchor_centroid[0] + max_distance,
                    anchor_centroid[1] + max_distance,
                )
            )
        ) if centroid_index is not None else set(range(len(self._rows)))

        mask: list[bool] = []
        for index, (row, centroid) in enumerate(zip(self._rows, centroids, strict=True)):
            if anchor_id is not None and not include_anchor and id_column in row and str(row[id_column]) == anchor_id:
                mask.append(False)
                continue
            if index not in candidate_indexes:
                mask.append(False)
                continue
            mask.append(coordinate_distance(anchor_centroid, centroid, method=distance_method) <= max_distance)
        return mask

    def proximity_join(
        self,
        other: "GeoPromptFrame",
        max_distance: float,
        how: SpatialJoinMode = "inner",
        lsuffix: str = "left",
        rsuffix: str = "right",
        distance_method: str = "euclidean",
    ) -> "GeoPromptFrame":
        if max_distance < 0:
            raise ValueError("max_distance must be zero or greater")
        if how not in {"inner", "left"}:
            raise ValueError("how must be 'inner' or 'left'")
        if self.crs and other.crs and self.crs != other.crs:
            raise ValueError("frames must share the same CRS before proximity joins")

        right_rows = list(other._rows)
        right_columns = [column for column in other.columns if column != other.geometry_column]
        left_centroids = self._centroids()
        right_centroids = other._centroids()
        right_index = other.spatial_index(mode="centroid", cell_size=max_distance) if distance_method == "euclidean" and right_rows else None
        joined_rows: list[Record] = []

        for left_row, left_centroid in zip(self._rows, left_centroids, strict=True):
            row_matches: list[tuple[Record, float]] = []
            candidate_indexes = (
                right_index.query(
                    (
                        left_centroid[0] - max_distance,
                        left_centroid[1] - max_distance,
                        left_centroid[0] + max_distance,
                        left_centroid[1] + max_distance,
                    )
                )
                if right_index is not None
                else range(len(right_rows))
            )
            for index in candidate_indexes:
                right_row = right_rows[index]
                right_centroid = right_centroids[index]
                if distance_method == "euclidean":
                    if abs(left_centroid[0] - right_centroid[0]) > max_distance or abs(left_centroid[1] - right_centroid[1]) > max_distance:
                        continue
                distance_value = coordinate_distance(left_centroid, right_centroid, method=distance_method)
                if distance_value <= max_distance:
                    row_matches.append((right_row, distance_value))

            row_matches.sort(key=lambda item: (float(item[1]), str(item[0].get("site_id", item[0].get("region_id", "")))))

            if not row_matches and how == "left":
                merged_row = dict(left_row)
                for column in right_columns:
                    target_name = column if column not in merged_row else f"{column}_{rsuffix}"
                    merged_row[target_name] = None
                merged_row[f"{other.geometry_column}_{rsuffix}"] = None
                merged_row[f"distance_{rsuffix}"] = None
                merged_row[f"distance_method_{rsuffix}"] = distance_method
                joined_rows.append(merged_row)

            for right_row, distance_value in row_matches:
                merged_row = dict(left_row)
                for column in right_columns:
                    target_name = column if column not in merged_row else f"{column}_{rsuffix}"
                    merged_row[target_name] = right_row[column]
                merged_row[f"{other.geometry_column}_{rsuffix}"] = right_row[other.geometry_column]
                merged_row[f"distance_{rsuffix}"] = distance_value
                merged_row[f"distance_method_{rsuffix}"] = distance_method
                joined_rows.append(merged_row)

        return GeoPromptFrame._from_internal_rows(joined_rows, geometry_column=self.geometry_column, crs=self.crs or other.crs)

    def buffer(self, distance: float, resolution: int = 16) -> "GeoPromptFrame":
        buffered_groups = buffer_geometries(
            [row[self.geometry_column] for row in self._rows],
            distance=distance,
            resolution=resolution,
        )
        rows: list[Record] = []
        for row, buffered_geometries in zip(self._rows, buffered_groups, strict=True):
            for buffered_geometry in buffered_geometries:
                buffered_row = dict(row)
                buffered_row[self.geometry_column] = buffered_geometry
                rows.append(buffered_row)
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    def buffer_join(
        self,
        other: "GeoPromptFrame",
        distance: float,
        how: SpatialJoinMode = "inner",
        lsuffix: str = "left",
        rsuffix: str = "right",
        resolution: int = 16,
    ) -> "GeoPromptFrame":
        if distance < 0:
            raise ValueError("distance must be zero or greater")
        if how not in {"inner", "left"}:
            raise ValueError("how must be 'inner' or 'left'")
        if self.crs and other.crs and self.crs != other.crs:
            raise ValueError("frames must share the same CRS before buffer joins")

        right_rows = list(other._rows)
        right_columns = [column for column in other.columns if column != other.geometry_column]
        right_index = other.spatial_index(mode="geometry") if right_rows else None
        buffered_groups = buffer_geometries(
            [row[self.geometry_column] for row in self._rows],
            distance=distance,
            resolution=resolution,
        )

        joined_rows: list[Record] = []
        for left_row, buffered_geometries in zip(self._rows, buffered_groups, strict=True):
            row_matches: list[tuple[Record, Geometry]] = []
            for buffered_geometry in buffered_geometries:
                buffered_bounds = geometry_bounds(buffered_geometry)
                candidate_indexes = right_index.query(buffered_bounds) if right_index is not None else []
                for index in candidate_indexes:
                    right_row = right_rows[index]
                    right_bound = geometry_bounds(right_row[other.geometry_column])
                    if not _bounds_intersect(buffered_bounds, right_bound):
                        continue
                    if geometry_intersects(buffered_geometry, right_row[other.geometry_column]):
                        row_matches.append((right_row, buffered_geometry))

            if not row_matches and how == "left":
                merged_row = dict(left_row)
                merged_row[f"buffer_geometry_{lsuffix}"] = None
                merged_row[f"buffer_distance_{lsuffix}"] = distance
                for column in right_columns:
                    target_name = column if column not in merged_row else f"{column}_{rsuffix}"
                    merged_row[target_name] = None
                merged_row[f"{other.geometry_column}_{rsuffix}"] = None
                joined_rows.append(merged_row)

            for right_row, buffered_geometry in row_matches:
                merged_row = dict(left_row)
                merged_row[f"buffer_geometry_{lsuffix}"] = buffered_geometry
                merged_row[f"buffer_distance_{lsuffix}"] = distance
                for column in right_columns:
                    target_name = column if column not in merged_row else f"{column}_{rsuffix}"
                    merged_row[target_name] = right_row[column]
                merged_row[f"{other.geometry_column}_{rsuffix}"] = right_row[other.geometry_column]
                joined_rows.append(merged_row)

        return GeoPromptFrame._from_internal_rows(joined_rows, geometry_column=self.geometry_column, crs=self.crs or other.crs)

    def coverage_summary(
        self,
        targets: "GeoPromptFrame",
        predicate: SpatialJoinPredicate = "intersects",
        target_id_column: str = "site_id",
        aggregations: dict[str, AggregationName] | None = None,
        rsuffix: str = "covered",
    ) -> "GeoPromptFrame":
        if self.crs and targets.crs and self.crs != targets.crs:
            raise ValueError("frames must share the same CRS before coverage summaries")
        if predicate not in {"intersects", "within", "contains"}:
            raise ValueError(f"unsupported spatial join predicate: {predicate}")

        targets._require_column(target_id_column)
        target_rows = list(targets._rows)
        target_index = targets.spatial_index(mode="geometry") if target_rows else None
        predicate_bounds_filter = {
            "intersects": _bounds_intersect,
            "within": _bounds_within,
            "contains": lambda left, right: _bounds_within(right, left),
        }

        def matches(left_geometry: Geometry, right_geometry: Geometry) -> bool:
            if predicate == "intersects":
                return geometry_intersects(left_geometry, right_geometry)
            if predicate == "within":
                return geometry_within(left_geometry, right_geometry)
            return geometry_contains(left_geometry, right_geometry)

        rows: list[Record] = []
        for row in self._rows:
            left_geometry = row[self.geometry_column]
            left_bounds = geometry_bounds(left_geometry)
            matched_rows: list[Record] = []
            candidate_indexes = target_index.query(left_bounds) if target_index is not None else []
            for index in candidate_indexes:
                target_row = target_rows[index]
                target_bound = geometry_bounds(target_row[targets.geometry_column])
                if not predicate_bounds_filter[predicate](left_bounds, target_bound):
                    continue
                if matches(left_geometry, target_row[targets.geometry_column]):
                    matched_rows.append(target_row)

            resolved_row = dict(row)
            resolved_row[f"{target_id_column}s_{rsuffix}"] = [str(item[target_id_column]) for item in matched_rows]
            resolved_row[f"count_{rsuffix}"] = len(matched_rows)
            resolved_row[f"predicate_{rsuffix}"] = predicate
            resolved_row.update(self._aggregate_rows(matched_rows, aggregations=aggregations, suffix=rsuffix))
            rows.append(resolved_row)

        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs or targets.crs)

    def query_bounds(
        self,
        min_x: float,
        min_y: float,
        max_x: float,
        max_y: float,
        mode: BoundsQueryMode = "intersects",
    ) -> "GeoPromptFrame":
        if min_x > max_x or min_y > max_y:
            raise ValueError("query bounds must be ordered from minimum to maximum")

        rows: list[Record] = []
        active_index = self.spatial_index(mode="centroid") if mode == "centroid" else self.spatial_index(mode="geometry")
        query_mode = "within" if mode == "within" else "intersects"
        candidate_indexes = active_index.query((min_x, min_y, max_x, max_y), mode=query_mode)
        for index in candidate_indexes:
            row = self._rows[index]
            geometry = row[self.geometry_column]
            if mode == "intersects":
                include_row = geometry_intersects_bounds(geometry, min_x=min_x, min_y=min_y, max_x=max_x, max_y=max_y)
            elif mode == "within":
                include_row = geometry_within_bounds(geometry, min_x=min_x, min_y=min_y, max_x=max_x, max_y=max_y)
            elif mode == "centroid":
                centroid_x, centroid_y = geometry_centroid(geometry)
                include_row = min_x <= centroid_x <= max_x and min_y <= centroid_y <= max_y
            else:
                raise ValueError(f"unsupported bounds query mode: {mode}")

            if include_row:
                rows.append(dict(row))

        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    def set_crs(self, crs: str, allow_override: bool = False) -> "GeoPromptFrame":
        if self.crs is not None and self.crs != crs and not allow_override:
            raise ValueError("frame already has a CRS; pass allow_override=True to replace it")
        return GeoPromptFrame(rows=self.to_records(), geometry_column=self.geometry_column, crs=crs)

    def to_crs(self, target_crs: str) -> "GeoPromptFrame":
        if self.crs is None:
            raise ValueError("frame CRS is not set; call set_crs before reprojecting")
        if self.crs == target_crs:
            return GeoPromptFrame(rows=self.to_records(), geometry_column=self.geometry_column, crs=self.crs)

        try:
            pyproj = importlib.import_module("pyproj")
        except ImportError as exc:
            raise RuntimeError("Install projection support with 'pip install -e .[projection]' before calling to_crs.") from exc

        transformer = pyproj.Transformer.from_crs(self.crs, target_crs, always_xy=True)

        def reproject_coordinate(coordinate: Coordinate) -> Coordinate:
            x_value, y_value = transformer.transform(coordinate[0], coordinate[1])
            return (float(x_value), float(y_value))

        rows = self.to_records()
        for row in rows:
            row[self.geometry_column] = transform_geometry(row[self.geometry_column], reproject_coordinate)
        return GeoPromptFrame(rows=rows, geometry_column=self.geometry_column, crs=target_crs)

    def spatial_join(
        self,
        other: "GeoPromptFrame",
        predicate: SpatialJoinPredicate = "intersects",
        how: SpatialJoinMode = "inner",
        lsuffix: str = "left",
        rsuffix: str = "right",
        include_diagnostics: bool = False,
    ) -> "GeoPromptFrame":
        if how not in {"inner", "left"}:
            raise ValueError("how must be 'inner' or 'left'")
        if self.crs and other.crs and self.crs != other.crs:
            raise ValueError("frames must share the same CRS before spatial joins")

        right_columns = [column for column in other.columns if column != other.geometry_column]
        joined_rows: list[Record] = []
        right_rows = list(other._rows)
        right_index = other.spatial_index(mode="geometry") if right_rows else None

        predicate_bounds_filter = {
            "intersects": _bounds_intersect,
            "within": _bounds_within,
            "contains": lambda left, right: _bounds_within(right, left),
        }
        if predicate not in predicate_bounds_filter:
            raise ValueError(f"unsupported spatial join predicate: {predicate}")

        def matches(left_geometry: Geometry, right_geometry: Geometry) -> bool:
            if predicate == "intersects":
                return geometry_intersects(left_geometry, right_geometry)
            if predicate == "within":
                return geometry_within(left_geometry, right_geometry)
            if predicate == "contains":
                return geometry_contains(left_geometry, right_geometry)
            raise ValueError(f"unsupported spatial join predicate: {predicate}")

        for left_index, left_row in enumerate(self._rows):
            left_geometry = left_row[self.geometry_column]
            left_bounds = geometry_bounds(left_geometry)
            row_matches = []
            candidate_indexes = right_index.query(left_bounds) if right_index is not None else []
            for candidate_index in candidate_indexes:
                right_row = right_rows[candidate_index]
                right_bound = geometry_bounds(right_row[other.geometry_column])
                if not predicate_bounds_filter[predicate](left_bounds, right_bound):
                    continue
                if matches(left_geometry, right_row[other.geometry_column]):
                    row_matches.append(right_row)

            if not row_matches and how == "left":
                merged_row = dict(left_row)
                for column in right_columns:
                    target_name = column if column not in merged_row else f"{column}_{rsuffix}"
                    merged_row[target_name] = None
                merged_row[f"join_predicate_{rsuffix}"] = predicate
                if include_diagnostics:
                    merged_row[f"candidate_count_{rsuffix}"] = len(candidate_indexes)
                    merged_row[f"pruning_ratio_{rsuffix}"] = 1.0 - (len(candidate_indexes) / len(right_rows) if right_rows else 0.0)
                    merged_row[f"match_count_{rsuffix}"] = 0
                joined_rows.append(merged_row)

            for right_row in row_matches:
                merged_row = dict(left_row)
                for column in right_columns:
                    target_name = column if column not in merged_row else f"{column}_{rsuffix}"
                    merged_row[target_name] = right_row[column]
                merged_row[f"{other.geometry_column}_{rsuffix}"] = right_row[other.geometry_column]
                merged_row[f"join_predicate_{rsuffix}"] = predicate
                if include_diagnostics:
                    merged_row[f"candidate_count_{rsuffix}"] = len(candidate_indexes)
                    merged_row[f"pruning_ratio_{rsuffix}"] = 1.0 - (len(candidate_indexes) / len(right_rows) if right_rows else 0.0)
                    merged_row[f"match_count_{rsuffix}"] = len(row_matches)
                joined_rows.append(merged_row)

        return GeoPromptFrame._from_internal_rows(joined_rows, geometry_column=self.geometry_column, crs=self.crs or other.crs)

    def overlay_summary(
        self,
        other: "GeoPromptFrame",
        right_id_column: str = "region_id",
        aggregations: dict[str, AggregationName] | None = None,
        how: SpatialJoinMode = "left",
        group_by: str | None = None,
        normalize_by: OverlayNormalizeMode = "left",
        top_n_groups: int | None = None,
        summary_suffix: str = "overlay",
    ) -> "GeoPromptFrame":
        if how not in {"inner", "left"}:
            raise ValueError("how must be 'inner' or 'left'")
        if self.crs and other.crs and self.crs != other.crs:
            raise ValueError("frames must share the same CRS before overlay summaries")
        if normalize_by not in {"left", "right", "both"}:
            raise ValueError("normalize_by must be 'left', 'right', or 'both'")
        if top_n_groups is not None and top_n_groups <= 0:
            raise ValueError("top_n_groups must be greater than zero")

        other._require_column(right_id_column)
        if group_by is not None:
            other._require_column(group_by)
        other_rows = list(other._rows)
        grouped: dict[int, list[tuple[int, list[Geometry]]]] = {}
        for left_index, right_index, geometries in overlay_intersections(
            [row[self.geometry_column] for row in self._rows],
            [row[other.geometry_column] for row in other_rows],
        ):
            grouped.setdefault(left_index, []).append((right_index, geometries))

        rows: list[Record] = []
        for left_index, left_row in enumerate(self._rows):
            matches = grouped.get(left_index, [])
            if not matches and how == "inner":
                continue

            matched_rows = [other_rows[right_index] for right_index, _ in matches]
            overlap_area = sum(geometry_area(geometry) for _right_index, geometries in matches for geometry in geometries)
            overlap_length = sum(geometry_length(geometry) for _right_index, geometries in matches for geometry in geometries)
            intersection_count = sum(len(geometries) for _right_index, geometries in matches)
            right_area_total = sum(geometry_area(other_rows[right_index][other.geometry_column]) for right_index, _ in matches)
            right_length_total = sum(geometry_length(other_rows[right_index][other.geometry_column]) for right_index, _ in matches)

            left_geometry = left_row[self.geometry_column]
            left_area = geometry_area(left_geometry)
            left_length = geometry_length(left_geometry)

            resolved_row = dict(left_row)
            resolved_row[f"{right_id_column}s_{summary_suffix}"] = [str(row[right_id_column]) for row in matched_rows]
            resolved_row[f"count_{summary_suffix}"] = len(matched_rows)
            resolved_row[f"intersection_count_{summary_suffix}"] = intersection_count
            resolved_row[f"area_overlap_{summary_suffix}"] = overlap_area
            resolved_row[f"length_overlap_{summary_suffix}"] = overlap_length
            resolved_row[f"area_share_{summary_suffix}"] = (overlap_area / left_area) if left_area > 0 and normalize_by in {"left", "both"} else None
            resolved_row[f"length_share_{summary_suffix}"] = (overlap_length / left_length) if left_length > 0 and normalize_by in {"left", "both"} else None
            resolved_row[f"area_share_right_{summary_suffix}"] = (overlap_area / right_area_total) if right_area_total > 0 and normalize_by in {"right", "both"} else None
            resolved_row[f"length_share_right_{summary_suffix}"] = (overlap_length / right_length_total) if right_length_total > 0 and normalize_by in {"right", "both"} else None
            if group_by is not None:
                grouped_matches: dict[str, dict[str, Any]] = {}
                for right_index, geometries in matches:
                    group_value = str(other_rows[right_index][group_by])
                    bucket = grouped_matches.setdefault(
                        group_value,
                        {
                            "group": group_value,
                            "count": 0,
                            "intersection_count": 0,
                            "area_overlap": 0.0,
                            "length_overlap": 0.0,
                            f"{right_id_column}s": [],
                            "right_area_total": 0.0,
                            "right_length_total": 0.0,
                        },
                    )
                    bucket["count"] += 1
                    bucket["intersection_count"] += len(geometries)
                    bucket["area_overlap"] += sum(geometry_area(geometry) for geometry in geometries)
                    bucket["length_overlap"] += sum(geometry_length(geometry) for geometry in geometries)
                    bucket[f"{right_id_column}s"].append(str(other_rows[right_index][right_id_column]))
                    bucket["right_area_total"] += geometry_area(other_rows[right_index][other.geometry_column])
                    bucket["right_length_total"] += geometry_length(other_rows[right_index][other.geometry_column])

                group_summaries = []
                for group_summary in grouped_matches.values():
                    group_record = dict(group_summary)
                    group_record["area_share_left"] = (group_summary["area_overlap"] / left_area) if left_area > 0 and normalize_by in {"left", "both"} else None
                    group_record["length_share_left"] = (group_summary["length_overlap"] / left_length) if left_length > 0 and normalize_by in {"left", "both"} else None
                    group_record["area_share_right"] = (group_summary["area_overlap"] / group_summary["right_area_total"]) if group_summary["right_area_total"] > 0 and normalize_by in {"right", "both"} else None
                    group_record["length_share_right"] = (group_summary["length_overlap"] / group_summary["right_length_total"]) if group_summary["right_length_total"] > 0 and normalize_by in {"right", "both"} else None
                    group_record.pop("right_area_total")
                    group_record.pop("right_length_total")
                    group_summaries.append(group_record)

                group_summaries.sort(key=lambda item: (-float(item["area_overlap"]), -float(item["length_overlap"]), str(item["group"])))
                if top_n_groups is not None:
                    group_summaries = group_summaries[:top_n_groups]
                resolved_row[f"groups_{summary_suffix}"] = group_summaries
                resolved_row[f"best_group_{summary_suffix}"] = group_summaries[0]["group"] if group_summaries else None
            resolved_row.update(self._aggregate_rows(matched_rows, aggregations=aggregations, suffix=summary_suffix))
            rows.append(resolved_row)

        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs or other.crs)

    def clip(self, mask: "GeoPromptFrame") -> "GeoPromptFrame":
        if self.crs and mask.crs and self.crs != mask.crs:
            raise ValueError("frames must share the same CRS before clip operations")

        mask_rows = list(mask)
        clipped_groups = clip_geometries(
            [row[self.geometry_column] for row in self._rows],
            [row[mask.geometry_column] for row in mask_rows],
        )
        rows: list[Record] = []
        for row, clipped_geometries in zip(self._rows, clipped_groups, strict=True):
            for clipped_geometry in clipped_geometries:
                clipped_row = dict(row)
                clipped_row[self.geometry_column] = clipped_geometry
                rows.append(clipped_row)
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs or mask.crs)

    def overlay_intersections(
        self,
        other: "GeoPromptFrame",
        lsuffix: str = "left",
        rsuffix: str = "right",
    ) -> "GeoPromptFrame":
        if self.crs and other.crs and self.crs != other.crs:
            raise ValueError("frames must share the same CRS before overlay operations")

        intersections = overlay_intersections(
            [row[self.geometry_column] for row in self._rows],
            [row[other.geometry_column] for row in other],
        )
        right_columns = [column for column in other.columns if column != other.geometry_column]
        rows: list[Record] = []
        for left_index, right_index, geometries in intersections:
            left_row = self._rows[left_index]
            right_row = other.to_records()[right_index]
            for geometry in geometries:
                merged_row = dict(left_row)
                for column in right_columns:
                    target_name = column if column not in merged_row else f"{column}_{rsuffix}"
                    merged_row[target_name] = right_row[column]
                merged_row[f"{other.geometry_column}_{rsuffix}"] = right_row[other.geometry_column]
                merged_row[self.geometry_column] = geometry
                rows.append(merged_row)
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs or other.crs)

    def overlay_union(
        self,
        other: "GeoPromptFrame",
        left_id_column: str = "site_id",
        right_id_column: str = "site_id",
        rsuffix: str = "right",
        union_suffix: str = "union",
    ) -> "GeoPromptFrame":
        if self.crs and other.crs and self.crs != other.crs:
            raise ValueError("frames must share the same CRS before overlay operations")
        if any(geometry_type(row[self.geometry_column]) != "Polygon" for row in self._rows):
            raise ValueError("overlay_union currently requires Polygon geometries on the left frame")
        if any(geometry_type(row[other.geometry_column]) != "Polygon" for row in other._rows):
            raise ValueError("overlay_union currently requires Polygon geometries on the right frame")
        self._require_column(left_id_column)
        other._require_column(right_id_column)

        faces = overlay_union_faces(
            [row[self.geometry_column] for row in self._rows],
            [row[other.geometry_column] for row in other._rows],
        )
        left_columns = [column for column in self.columns if column != self.geometry_column]
        right_columns = [column for column in other.columns if column != other.geometry_column]
        right_rows = list(other._rows)
        rows: list[Record] = []

        for left_indexes, right_indexes, geometry in faces:
            resolved: Record = {}
            for column in left_columns:
                resolved[column] = self._rows[left_indexes[0]][column] if len(left_indexes) == 1 else None
            for column in right_columns:
                target_name = column if column not in resolved else f"{column}_{rsuffix}"
                resolved[target_name] = right_rows[right_indexes[0]][column] if len(right_indexes) == 1 else None
            resolved[f"{left_id_column}s_{union_suffix}"] = [str(self._rows[index][left_id_column]) for index in left_indexes]
            resolved[f"{right_id_column}s_{union_suffix}"] = [str(right_rows[index][right_id_column]) for index in right_indexes]
            resolved[f"left_count_{union_suffix}"] = len(left_indexes)
            resolved[f"right_count_{union_suffix}"] = len(right_indexes)
            resolved[f"source_side_{union_suffix}"] = "both" if left_indexes and right_indexes else ("left" if left_indexes else "right")
            resolved[f"area_{union_suffix}"] = geometry_area(geometry)
            resolved[self.geometry_column] = geometry
            rows.append(resolved)

        rows.sort(
            key=lambda row: (
                str(row[f"source_side_{union_suffix}"]),
                tuple(row[f"{left_id_column}s_{union_suffix}"]),
                tuple(row[f"{right_id_column}s_{union_suffix}"]),
            )
        )
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs or other.crs)

    def overlay_difference(
        self,
        other: "GeoPromptFrame",
        left_id_column: str = "site_id",
        right_id_column: str = "site_id",
        difference_suffix: str = "difference",
    ) -> "GeoPromptFrame":
        if self.crs and other.crs and self.crs != other.crs:
            raise ValueError("frames must share the same CRS before overlay operations")
        if any(geometry_type(row[self.geometry_column]) != "Polygon" for row in self._rows):
            raise ValueError("overlay_difference currently requires Polygon geometries on the left frame")
        if any(geometry_type(row[other.geometry_column]) != "Polygon" for row in other._rows):
            raise ValueError("overlay_difference currently requires Polygon geometries on the right frame")
        self._require_column(left_id_column)
        other._require_column(right_id_column)

        faces = overlay_union_faces(
            [row[self.geometry_column] for row in self._rows],
            [row[other.geometry_column] for row in other._rows],
        )
        retained_faces = [(left_indexes, geometry) for left_indexes, right_indexes, geometry in faces if left_indexes and not right_indexes]
        retained_totals: dict[int, float] = {}
        part_counts: dict[int, int] = {}
        for left_indexes, geometry in retained_faces:
            if len(left_indexes) != 1:
                continue
            left_index = left_indexes[0]
            retained_totals[left_index] = retained_totals.get(left_index, 0.0) + geometry_area(geometry)
            part_counts[left_index] = part_counts.get(left_index, 0) + 1

        rows: list[Record] = []
        for left_indexes, geometry in retained_faces:
            resolved: Record = {}
            for column in self.columns:
                if column == self.geometry_column:
                    continue
                resolved[column] = self._rows[left_indexes[0]][column] if len(left_indexes) == 1 else None
            left_ids = [str(self._rows[index][left_id_column]) for index in left_indexes]
            resolved[f"{left_id_column}s_{difference_suffix}"] = left_ids
            resolved[f"{right_id_column}s_{difference_suffix}"] = []
            resolved[f"left_count_{difference_suffix}"] = len(left_indexes)
            resolved[f"right_count_{difference_suffix}"] = 0
            resolved[f"source_side_{difference_suffix}"] = "left"
            resolved[f"area_{difference_suffix}"] = geometry_area(geometry)
            if len(left_indexes) == 1:
                left_index = left_indexes[0]
                source_area = geometry_area(self._rows[left_index][self.geometry_column])
                retained_area = retained_totals.get(left_index, 0.0)
                removed_area = max(0.0, source_area - retained_area)
                resolved[f"source_area_{difference_suffix}"] = source_area
                resolved[f"retained_area_{difference_suffix}"] = retained_area
                resolved[f"removed_area_{difference_suffix}"] = removed_area
                resolved[f"removed_share_{difference_suffix}"] = (removed_area / source_area) if source_area > 0.0 else None
                resolved[f"part_count_{difference_suffix}"] = part_counts.get(left_index, 0)
            else:
                resolved[f"source_area_{difference_suffix}"] = None
                resolved[f"retained_area_{difference_suffix}"] = None
                resolved[f"removed_area_{difference_suffix}"] = None
                resolved[f"removed_share_{difference_suffix}"] = None
                resolved[f"part_count_{difference_suffix}"] = None
            resolved[self.geometry_column] = geometry
            rows.append(resolved)

        rows.sort(
            key=lambda row: (
                tuple(row[f"{left_id_column}s_{difference_suffix}"]),
                round(geometry_centroid(row[self.geometry_column])[0], 12),
                round(geometry_centroid(row[self.geometry_column])[1], 12),
            )
        )
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs or other.crs)

    def overlay_symmetric_difference(
        self,
        other: "GeoPromptFrame",
        left_id_column: str = "site_id",
        right_id_column: str = "site_id",
        rsuffix: str = "right",
        difference_suffix: str = "symdiff",
    ) -> "GeoPromptFrame":
        if self.crs and other.crs and self.crs != other.crs:
            raise ValueError("frames must share the same CRS before overlay operations")
        if any(geometry_type(row[self.geometry_column]) != "Polygon" for row in self._rows):
            raise ValueError("overlay_symmetric_difference currently requires Polygon geometries on the left frame")
        if any(geometry_type(row[other.geometry_column]) != "Polygon" for row in other._rows):
            raise ValueError("overlay_symmetric_difference currently requires Polygon geometries on the right frame")
        self._require_column(left_id_column)
        other._require_column(right_id_column)

        faces = overlay_union_faces(
            [row[self.geometry_column] for row in self._rows],
            [row[other.geometry_column] for row in other._rows],
        )
        left_columns = [column for column in self.columns if column != self.geometry_column]
        right_columns = [column for column in other.columns if column != other.geometry_column]
        right_rows = list(other._rows)
        rows: list[Record] = []

        for left_indexes, right_indexes, geometry in faces:
            if bool(left_indexes) == bool(right_indexes):
                continue
            resolved: Record = {}
            for column in left_columns:
                resolved[column] = self._rows[left_indexes[0]][column] if len(left_indexes) == 1 else None
            for column in right_columns:
                target_name = column if column not in resolved else f"{column}_{rsuffix}"
                resolved[target_name] = right_rows[right_indexes[0]][column] if len(right_indexes) == 1 else None
            resolved[f"{left_id_column}s_{difference_suffix}"] = [str(self._rows[index][left_id_column]) for index in left_indexes]
            resolved[f"{right_id_column}s_{difference_suffix}"] = [str(right_rows[index][right_id_column]) for index in right_indexes]
            resolved[f"left_count_{difference_suffix}"] = len(left_indexes)
            resolved[f"right_count_{difference_suffix}"] = len(right_indexes)
            resolved[f"source_side_{difference_suffix}"] = "left" if left_indexes else "right"
            resolved[f"area_{difference_suffix}"] = geometry_area(geometry)
            resolved[self.geometry_column] = geometry
            rows.append(resolved)

        rows.sort(
            key=lambda row: (
                str(row[f"source_side_{difference_suffix}"]),
                tuple(row[f"{left_id_column}s_{difference_suffix}"]),
                tuple(row[f"{right_id_column}s_{difference_suffix}"]),
            )
        )
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs or other.crs)

    def dissolve(
        self,
        by: str,
        aggregations: dict[str, AggregationName] | None = None,
    ) -> "GeoPromptFrame":
        self._require_column(by)
        grouped_rows: dict[Any, list[Record]] = {}
        for row in self._rows:
            grouped_rows.setdefault(row[by], []).append(row)

        rows: list[Record] = []
        for group_value, group_rows in grouped_rows.items():
            dissolved_geometries = dissolve_geometries([row[self.geometry_column] for row in group_rows])
            aggregate_values: dict[str, Any] = {by: group_value}
            for column in self.columns:
                if column in {by, self.geometry_column}:
                    continue
                operation = (aggregations or {}).get(column)
                values = [row[column] for row in group_rows if column in row]
                if not values:
                    continue
                if operation is None:
                    aggregate_values[column] = values[0]
                elif operation == "sum":
                    aggregate_values[column] = sum(float(value) for value in values)
                elif operation == "mean":
                    aggregate_values[column] = sum(float(value) for value in values) / len(values)
                elif operation == "min":
                    aggregate_values[column] = min(values)
                elif operation == "max":
                    aggregate_values[column] = max(values)
                elif operation == "first":
                    aggregate_values[column] = values[0]
                elif operation == "count":
                    aggregate_values[column] = len(values)
                else:
                    raise ValueError(f"unsupported aggregation: {operation}")

            for geometry in dissolved_geometries:
                rows.append({**aggregate_values, self.geometry_column: geometry})

        return GeoPromptFrame(rows=rows, geometry_column=self.geometry_column, crs=self.crs)

    def with_column(self, name: str, values: Sequence[Any]) -> "GeoPromptFrame":
        if len(values) != len(self._rows):
            raise ValueError("column length must match the frame length")
        rows = self.to_records()
        for row, value in zip(rows, values, strict=True):
            row[name] = value
        return GeoPromptFrame(rows=rows, geometry_column=self.geometry_column, crs=self.crs)

    def assign(self, **columns: Any) -> "GeoPromptFrame":
        frame = self
        for name, value in columns.items():
            if callable(value):
                resolved = value(frame)
            else:
                resolved = value

            if isinstance(resolved, Sequence) and not isinstance(resolved, (str, bytes)):
                values = list(resolved)
            else:
                values = [resolved for _ in frame._rows]

            frame = frame.with_column(name=name, values=values)
        return frame

    def _require_column(self, name: str) -> None:
        if name not in self.columns:
            raise KeyError(f"column '{name}' is not present")

    def neighborhood_pressure(
        self,
        weight_column: str,
        scale: float = 1.0,
        power: float = 2.0,
        include_self: bool = False,
        distance_method: str = "euclidean",
    ) -> list[float]:
        self._require_column(weight_column)
        pressures: list[float] = []
        for row in self._rows:
            total = 0.0
            for other in self._rows:
                if not include_self and row is other:
                    continue
                distance_value = geometry_distance(row[self.geometry_column], other[self.geometry_column], method=distance_method)
                total += prompt_influence(
                    weight=float(other[weight_column]),
                    distance_value=distance_value,
                    scale=scale,
                    power=power,
                )
            pressures.append(total)
        return pressures

    def anchor_influence(
        self,
        weight_column: str,
        anchor: str,
        id_column: str = "site_id",
        scale: float = 1.0,
        power: float = 2.0,
        distance_method: str = "euclidean",
    ) -> list[float]:
        self._require_column(weight_column)
        self._require_column(id_column)
        anchor_row = next((row for row in self._rows if row[id_column] == anchor), None)
        if anchor_row is None:
            raise KeyError(f"anchor '{anchor}' was not found in column '{id_column}'")

        return [
            prompt_influence(
                weight=float(row[weight_column]),
                distance_value=geometry_distance(anchor_row[self.geometry_column], row[self.geometry_column], method=distance_method),
                scale=scale,
                power=power,
            )
            for row in self._rows
        ]

    def corridor_accessibility(
        self,
        weight_column: str,
        anchor: str,
        id_column: str = "site_id",
        scale: float = 1.0,
        power: float = 2.0,
        distance_method: str = "euclidean",
    ) -> list[float]:
        self._require_column(weight_column)
        self._require_column(id_column)
        anchor_row = next((row for row in self._rows if row[id_column] == anchor), None)
        if anchor_row is None:
            raise KeyError(f"anchor '{anchor}' was not found in column '{id_column}'")

        return [
            corridor_strength(
                weight=float(row[weight_column]),
                corridor_length=geometry_length(row[self.geometry_column]),
                distance_value=geometry_distance(anchor_row[self.geometry_column], row[self.geometry_column], method=distance_method),
                scale=scale,
                power=power,
            )
            for row in self._rows
        ]

    def area_similarity_table(
        self,
        id_column: str = "site_id",
        scale: float = 1.0,
        power: float = 1.0,
        distance_method: str = "euclidean",
    ) -> list[Record]:
        self._require_column(id_column)
        interactions: list[Record] = []
        for origin in self._rows:
            for destination in self._rows:
                if origin is destination:
                    continue
                interactions.append(
                    {
                        "origin": origin[id_column],
                        "destination": destination[id_column],
                        "area_similarity": area_similarity(
                            origin_area=geometry_area(origin[self.geometry_column]),
                            destination_area=geometry_area(destination[self.geometry_column]),
                            distance_value=geometry_distance(origin[self.geometry_column], destination[self.geometry_column], method=distance_method),
                            scale=scale,
                            power=power,
                        ),
                        "distance_method": distance_method,
                    }
                )
        return interactions

    def interaction_table(
        self,
        origin_weight: str,
        destination_weight: str,
        id_column: str = "site_id",
        scale: float = 1.0,
        power: float = 2.0,
        preferred_bearing: float | None = None,
        distance_method: str = "euclidean",
    ) -> list[Record]:
        self._require_column(origin_weight)
        self._require_column(destination_weight)
        self._require_column(id_column)

        interactions: list[Record] = []
        for origin in self._rows:
            for destination in self._rows:
                if origin is destination:
                    continue
                distance_value = geometry_distance(origin[self.geometry_column], destination[self.geometry_column], method=distance_method)
                interaction = prompt_interaction(
                    origin_weight=float(origin[origin_weight]),
                    destination_weight=float(destination[destination_weight]),
                    distance_value=distance_value,
                    scale=scale,
                    power=power,
                )
                record: Record = {
                    "origin": origin[id_column],
                    "destination": destination[id_column],
                    "distance": distance_value,
                    "interaction": interaction,
                    "distance_method": distance_method,
                }
                if preferred_bearing is not None:
                    record["directional_alignment"] = directional_alignment(
                        origin=geometry_centroid(origin[self.geometry_column]),
                        destination=geometry_centroid(destination[self.geometry_column]),
                        preferred_bearing=preferred_bearing,
                    )
                interactions.append(record)
        return interactions

    def select(self, *columns: str) -> "GeoPromptFrame":
        missing = [col for col in columns if col not in self.columns]
        if missing:
            raise KeyError(f"columns not found: {missing}")
        selected_columns = list(columns)
        if self.geometry_column not in selected_columns:
            selected_columns.append(self.geometry_column)
        rows = [{col: row[col] for col in selected_columns if col in row} for row in self._rows]
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    def rename_columns(self, mapping: dict[str, str]) -> "GeoPromptFrame":
        new_geometry_column = mapping.get(self.geometry_column, self.geometry_column)
        rows: list[Record] = []
        for row in self._rows:
            new_row = {mapping.get(key, key): value for key, value in row.items()}
            rows.append(new_row)
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=new_geometry_column, crs=self.crs)

    def filter(self, predicate: Any) -> "GeoPromptFrame":
        if callable(predicate):
            rows = [row for row in self._rows if predicate(row)]
        elif isinstance(predicate, Sequence) and not isinstance(predicate, (str, bytes)) and all(isinstance(v, bool) for v in predicate):
            if len(predicate) != len(self._rows):
                raise ValueError("boolean mask length must match frame length")
            rows = [row for row, keep in zip(self._rows, predicate, strict=True) if keep]
        else:
            raise TypeError("predicate must be a callable or a boolean sequence")
        return GeoPromptFrame._from_internal_rows([dict(r) for r in rows], geometry_column=self.geometry_column, crs=self.crs)

    def sort(self, by: str, descending: bool = False) -> "GeoPromptFrame":
        self._require_column(by)
        non_null_rows = [row for row in self._rows if row.get(by) is not None]
        null_rows = [row for row in self._rows if row.get(by) is None]
        sorted_rows = sorted(non_null_rows, key=lambda row: row.get(by), reverse=descending) + null_rows
        return GeoPromptFrame._from_internal_rows([dict(r) for r in sorted_rows], geometry_column=self.geometry_column, crs=self.crs)

    def describe(self) -> dict[str, dict[str, Any]]:
        stats: dict[str, dict[str, Any]] = {}
        for column in self.columns:
            if column == self.geometry_column:
                continue
            values = [row[column] for row in self._rows if column in row and row[column] is not None]
            numeric = [float(v) for v in values if isinstance(v, (int, float))]
            if not numeric:
                continue
            stats[column] = {
                "count": len(numeric),
                "min": min(numeric),
                "max": max(numeric),
                "mean": sum(numeric) / len(numeric),
                "sum": sum(numeric),
            }
        return stats

    def spatial_lag(
        self,
        value_column: str,
        id_column: str = "site_id",
        mode: SpatialLagMode = "k_nearest",
        k: int = 4,
        max_distance: float | None = None,
        include_self: bool = False,
        distance_method: str = "euclidean",
        weight_mode: SpatialLagWeightMode = "binary",
        include_diagnostics: bool = False,
        lag_suffix: str = "lag",
    ) -> "GeoPromptFrame":
        self._require_column(value_column)
        self._require_column(id_column)
        if mode not in {"k_nearest", "distance_band", "intersects"}:
            raise ValueError("mode must be 'k_nearest', 'distance_band', or 'intersects'")
        if weight_mode not in {"binary", "inverse_distance"}:
            raise ValueError("weight_mode must be 'binary' or 'inverse_distance'")
        if k <= 0:
            raise ValueError("k must be greater than zero")
        if max_distance is not None and max_distance < 0:
            raise ValueError("max_distance must be zero or greater")
        if mode == "distance_band" and max_distance is None:
            raise ValueError("max_distance is required when mode='distance_band'")

        row_count = len(self._rows)
        centroids = self._centroids()
        geometry_index = self.spatial_index(mode="geometry") if mode == "intersects" and self._rows else None
        centroid_index = self.spatial_index(mode="centroid", cell_size=max_distance) if mode == "distance_band" and distance_method == "euclidean" and max_distance is not None and self._rows else None
        rows: list[Record] = []

        for origin_index, origin_row in enumerate(self._rows):
            candidate_indexes: list[int]
            if mode == "distance_band" and centroid_index is not None and max_distance is not None:
                origin_centroid = centroids[origin_index]
                candidate_indexes = centroid_index.query(
                    (
                        origin_centroid[0] - max_distance,
                        origin_centroid[1] - max_distance,
                        origin_centroid[0] + max_distance,
                        origin_centroid[1] + max_distance,
                    )
                )
            elif mode == "intersects" and geometry_index is not None:
                candidate_indexes = geometry_index.query(geometry_bounds(origin_row[self.geometry_column]))
            else:
                candidate_indexes = list(range(row_count))

            neighbor_candidates: list[tuple[int, float]] = []
            for candidate_index in candidate_indexes:
                if not include_self and candidate_index == origin_index:
                    continue
                candidate_row = self._rows[candidate_index]
                if mode == "intersects":
                    if not geometry_intersects(origin_row[self.geometry_column], candidate_row[self.geometry_column]):
                        continue
                    distance_value = coordinate_distance(centroids[origin_index], centroids[candidate_index], method=distance_method)
                else:
                    distance_value = coordinate_distance(centroids[origin_index], centroids[candidate_index], method=distance_method)
                    if mode == "distance_band" and max_distance is not None and distance_value > max_distance:
                        continue
                neighbor_candidates.append((candidate_index, distance_value))

            if mode == "k_nearest":
                neighbor_candidates = nsmallest(
                    k,
                    neighbor_candidates,
                    key=lambda item: (float(item[1]), _row_sort_key(self._rows[item[0]])),
                )
            else:
                neighbor_candidates.sort(key=lambda item: (float(item[1]), _row_sort_key(self._rows[item[0]])))

            weights: list[float] = []
            weighted_values: list[float] = []
            neighbor_ids: list[str] = []
            for candidate_index, distance_value in neighbor_candidates:
                if weight_mode == "binary":
                    weight = 1.0
                elif distance_value <= 1e-12:
                    weight = 1.0
                else:
                    weight = 1.0 / distance_value
                weights.append(weight)
                weighted_values.append(float(self._rows[candidate_index][value_column]) * weight)
                neighbor_ids.append(str(self._rows[candidate_index][id_column]))

            weight_sum = sum(weights)
            lag_value = (sum(weighted_values) / weight_sum) if weight_sum > 0.0 else None
            resolved = dict(origin_row)
            resolved[f"{value_column}_{lag_suffix}"] = lag_value
            resolved[f"neighbor_count_{lag_suffix}"] = len(neighbor_candidates)
            resolved[f"neighbor_ids_{lag_suffix}"] = neighbor_ids
            if include_diagnostics:
                denominator = row_count if include_self else max(0, row_count - 1)
                resolved[f"candidate_count_{lag_suffix}"] = len(candidate_indexes)
                resolved[f"pruning_ratio_{lag_suffix}"] = 1.0 - (len(candidate_indexes) / denominator if denominator else 0.0)
                resolved[f"weight_sum_{lag_suffix}"] = weight_sum
                resolved[f"neighbor_weights_{lag_suffix}"] = weights
                resolved[f"mode_{lag_suffix}"] = mode
                resolved[f"weight_mode_{lag_suffix}"] = weight_mode
                resolved[f"distance_method_{lag_suffix}"] = distance_method
            rows.append(resolved)

        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    def spatial_autocorrelation(
        self,
        value_column: str,
        id_column: str = "site_id",
        mode: SpatialLagMode = "k_nearest",
        k: int = 4,
        max_distance: float | None = None,
        include_self: bool = False,
        distance_method: str = "euclidean",
        weight_mode: SpatialLagWeightMode = "binary",
        permutations: int = 0,
        random_seed: int = 0,
        significance_level: float = 0.05,
        include_diagnostics: bool = False,
        autocorr_suffix: str = "autocorr",
    ) -> "GeoPromptFrame":
        if permutations < 0:
            raise ValueError("permutations must be zero or greater")
        if not 0.0 <= significance_level <= 1.0:
            raise ValueError("significance_level must be between zero and one")
        lagged = self.spatial_lag(
            value_column=value_column,
            id_column=id_column,
            mode=mode,
            k=k,
            max_distance=max_distance,
            include_self=include_self,
            distance_method=distance_method,
            weight_mode=weight_mode,
            include_diagnostics=True,
            lag_suffix=autocorr_suffix,
        )
        lagged_rows = lagged.to_records()
        values = [float(row[value_column]) for row in lagged_rows]
        row_count = len(values)
        mean_value = (sum(values) / row_count) if row_count else 0.0
        centered_values = [value - mean_value for value in values]
        variance_sum = sum(value * value for value in centered_values)
        m2 = (variance_sum / row_count) if row_count else 0.0
        id_to_index = {str(row[id_column]): index for index, row in enumerate(lagged_rows)}
        neighbor_indexes = [
            [id_to_index[neighbor_id] for neighbor_id in row[f"neighbor_ids_{autocorr_suffix}"]]
            for row in lagged_rows
        ]
        neighbor_weights = [
            [float(weight) for weight in row[f"neighbor_weights_{autocorr_suffix}"]]
            for row in lagged_rows
        ]
        autocorr_stats = _autocorrelation_statistics(values, neighbor_indexes, neighbor_weights)
        global_moran = autocorr_stats["global_moran"]
        global_geary = autocorr_stats["global_geary"]
        total_weight = autocorr_stats["total_weight"]
        local_moran_values = autocorr_stats["local_moran_values"]
        local_geary_values = autocorr_stats["local_geary_values"]

        global_moran_p_value = None
        global_geary_p_value = None
        local_moran_p_values: list[float | None] = [None] * row_count
        local_geary_p_values: list[float | None] = [None] * row_count
        if permutations > 0 and row_count > 1 and total_weight > 0.0 and variance_sum > 0.0:
            rng = random.Random(random_seed)
            global_moran_hits = 0
            global_geary_hits = 0
            local_moran_hits = [0] * row_count
            local_geary_hits = [0] * row_count
            observed_global_moran = global_moran
            observed_global_geary = global_geary
            for _ in range(permutations):
                permuted_values = rng.sample(values, row_count)
                permutation_stats = _autocorrelation_statistics(permuted_values, neighbor_indexes, neighbor_weights)
                permutation_global_moran = permutation_stats["global_moran"]
                permutation_global_geary = permutation_stats["global_geary"]
                if observed_global_moran is not None and permutation_global_moran is not None and abs(permutation_global_moran) >= abs(observed_global_moran):
                    global_moran_hits += 1
                if observed_global_geary is not None and permutation_global_geary is not None and abs(permutation_global_geary - 1.0) >= abs(observed_global_geary - 1.0):
                    global_geary_hits += 1
                for origin_index, permutation_local_moran in enumerate(permutation_stats["local_moran_values"]):
                    observed_local_moran = local_moran_values[origin_index]
                    if observed_local_moran is not None and permutation_local_moran is not None and abs(permutation_local_moran) >= abs(observed_local_moran):
                        local_moran_hits[origin_index] += 1
                for origin_index, permutation_local_geary in enumerate(permutation_stats["local_geary_values"]):
                    observed_local_geary = local_geary_values[origin_index]
                    if observed_local_geary is not None and permutation_local_geary is not None and abs(permutation_local_geary - 1.0) >= abs(observed_local_geary - 1.0):
                        local_geary_hits[origin_index] += 1

            if observed_global_moran is not None:
                global_moran_p_value = (global_moran_hits + 1) / (permutations + 1)
            if observed_global_geary is not None:
                global_geary_p_value = (global_geary_hits + 1) / (permutations + 1)
            local_moran_p_values = [
                ((hits + 1) / (permutations + 1)) if local_moran_values[index] is not None else None
                for index, hits in enumerate(local_moran_hits)
            ]
            local_geary_p_values = [
                ((hits + 1) / (permutations + 1)) if local_geary_values[index] is not None else None
                for index, hits in enumerate(local_geary_hits)
            ]

        rows: list[Record] = []
        for index, (row, local_moran, local_geary) in enumerate(zip(lagged_rows, local_moran_values, local_geary_values, strict=True)):
            resolved = dict(row)
            lag_value = row.get(f"{value_column}_{autocorr_suffix}")
            lag_centered_value = (float(lag_value) - mean_value) if lag_value is not None else None
            resolved[f"mean_{autocorr_suffix}"] = mean_value
            resolved[f"global_moran_i_{autocorr_suffix}"] = global_moran
            resolved[f"global_geary_c_{autocorr_suffix}"] = global_geary
            resolved[f"global_moran_p_value_{autocorr_suffix}"] = global_moran_p_value
            resolved[f"global_geary_p_value_{autocorr_suffix}"] = global_geary_p_value
            resolved[f"local_moran_i_{autocorr_suffix}"] = local_moran
            resolved[f"local_geary_c_{autocorr_suffix}"] = local_geary
            resolved[f"local_moran_p_value_{autocorr_suffix}"] = local_moran_p_values[index]
            resolved[f"local_geary_p_value_{autocorr_suffix}"] = local_geary_p_values[index]
            cluster_label = _local_cluster_label(
                centered_values[index],
                lag_centered_value,
                local_moran,
                local_moran_p_values[index],
                significance_level,
            )
            cluster_family = _local_cluster_family(cluster_label)
            resolved[f"local_cluster_label_{autocorr_suffix}"] = cluster_label
            resolved[f"local_cluster_code_{autocorr_suffix}"] = _local_cluster_code(cluster_label)
            resolved[f"local_cluster_family_{autocorr_suffix}"] = cluster_family
            resolved[f"significant_cluster_{autocorr_suffix}"] = bool(local_moran_p_values[index] is not None and local_moran_p_values[index] <= significance_level)
            resolved[f"hotspot_{autocorr_suffix}"] = cluster_family == "hotspot"
            resolved[f"coldspot_{autocorr_suffix}"] = cluster_family == "coldspot"
            resolved[f"spatial_outlier_{autocorr_suffix}"] = cluster_family == "outlier"
            if not include_diagnostics:
                resolved.pop(f"candidate_count_{autocorr_suffix}", None)
                resolved.pop(f"pruning_ratio_{autocorr_suffix}", None)
                resolved.pop(f"weight_sum_{autocorr_suffix}", None)
                resolved.pop(f"neighbor_weights_{autocorr_suffix}", None)
                resolved.pop(f"mode_{autocorr_suffix}", None)
                resolved.pop(f"weight_mode_{autocorr_suffix}", None)
                resolved.pop(f"distance_method_{autocorr_suffix}", None)
            else:
                resolved[f"variance_sum_{autocorr_suffix}"] = variance_sum
                resolved[f"total_weight_{autocorr_suffix}"] = total_weight
                resolved[f"permutations_{autocorr_suffix}"] = permutations
                resolved[f"significance_level_{autocorr_suffix}"] = significance_level
            rows.append(resolved)

        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    def summarize_autocorrelation(
        self,
        value_column: str,
        id_column: str = "site_id",
        autocorr_suffix: str = "autocorr",
    ) -> "GeoPromptFrame":
        self._require_column(value_column)
        self._require_column(id_column)
        self._require_column(f"local_cluster_family_{autocorr_suffix}")
        self._require_column(f"local_cluster_label_{autocorr_suffix}")
        self._require_column(f"local_moran_i_{autocorr_suffix}")
        self._require_column(f"local_geary_c_{autocorr_suffix}")
        self._require_column(f"significant_cluster_{autocorr_suffix}")

        grouped_rows: dict[str, list[Record]] = {}
        for row in self._rows:
            family = str(row.get(f"local_cluster_family_{autocorr_suffix}") or "unclassified")
            grouped_rows.setdefault(family, []).append(row)

        rows: list[Record] = []
        for family, family_rows in sorted(grouped_rows.items(), key=lambda item: (item[0], len(item[1]))):
            label_counts: dict[str, int] = {}
            for row in family_rows:
                label = str(row.get(f"local_cluster_label_{autocorr_suffix}") or "unclassified")
                label_counts[label] = label_counts.get(label, 0) + 1
            mean_centroid = _mean_centroid_geometry(family_rows, self.geometry_column)
            local_moran_values = [
                float(row[f"local_moran_i_{autocorr_suffix}"])
                for row in family_rows
                if row.get(f"local_moran_i_{autocorr_suffix}") is not None
            ]
            local_geary_values = [
                float(row[f"local_geary_c_{autocorr_suffix}"])
                for row in family_rows
                if row.get(f"local_geary_c_{autocorr_suffix}") is not None
            ]
            significant_count = sum(1 for row in family_rows if bool(row.get(f"significant_cluster_{autocorr_suffix}")))
            summary_row: Record = {
                f"local_cluster_family_{autocorr_suffix}": family,
                f"feature_count_{autocorr_suffix}": len(family_rows),
                f"{id_column}s_{autocorr_suffix}": [str(row[id_column]) for row in family_rows],
                f"label_counts_{autocorr_suffix}": label_counts,
                f"significant_count_{autocorr_suffix}": significant_count,
                f"significant_share_{autocorr_suffix}": (significant_count / len(family_rows)) if family_rows else 0.0,
                f"{value_column}_mean_{autocorr_suffix}": sum(float(row[value_column]) for row in family_rows) / len(family_rows),
                f"local_moran_i_mean_{autocorr_suffix}": (sum(local_moran_values) / len(local_moran_values)) if local_moran_values else None,
                f"local_geary_c_mean_{autocorr_suffix}": (sum(local_geary_values) / len(local_geary_values)) if local_geary_values else None,
                f"global_moran_i_{autocorr_suffix}": family_rows[0].get(f"global_moran_i_{autocorr_suffix}"),
                f"global_geary_c_{autocorr_suffix}": family_rows[0].get(f"global_geary_c_{autocorr_suffix}"),
                self.geometry_column: mean_centroid,
            }
            rows.append(summary_row)

        rows.sort(
            key=lambda row: (
                -int(row[f"feature_count_{autocorr_suffix}"]),
                str(row[f"local_cluster_family_{autocorr_suffix}"]),
            )
        )
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    def report_autocorrelation_patterns(
        self,
        value_column: str,
        id_column: str = "site_id",
        autocorr_suffix: str = "autocorr",
        include_families: Sequence[str] = ("hotspot", "coldspot", "outlier"),
        top_ids: int = 5,
    ) -> "GeoPromptFrame":
        if top_ids <= 0:
            raise ValueError("top_ids must be greater than zero")

        summary = self.summarize_autocorrelation(
            value_column=value_column,
            id_column=id_column,
            autocorr_suffix=autocorr_suffix,
        )
        summary_rows = summary.to_records()
        family_filter = {str(value) for value in include_families}
        if not family_filter:
            raise ValueError("include_families must contain at least one family")

        total_feature_count = sum(int(row[f"feature_count_{autocorr_suffix}"]) for row in summary_rows)
        report_rows: list[Record] = []
        for row in summary_rows:
            family = str(row[f"local_cluster_family_{autocorr_suffix}"])
            if family not in family_filter:
                continue
            label_counts = dict(row[f"label_counts_{autocorr_suffix}"])
            primary_labels = [
                label
                for label, _count in sorted(label_counts.items(), key=lambda item: (-int(item[1]), str(item[0])))
            ]
            feature_count = int(row[f"feature_count_{autocorr_suffix}"])
            feature_share = (feature_count / total_feature_count) if total_feature_count else 0.0
            mean_local_moran = row.get(f"local_moran_i_mean_{autocorr_suffix}")
            intensity_score = (
                abs(float(mean_local_moran)) * float(row[f"significant_share_{autocorr_suffix}"]) * feature_share
                if mean_local_moran is not None
                else 0.0
            )
            report_row: Record = {
                f"local_cluster_family_{autocorr_suffix}": family,
                f"report_label_{autocorr_suffix}": _autocorr_report_label(family),
                f"feature_count_{autocorr_suffix}": feature_count,
                f"feature_share_{autocorr_suffix}": feature_share,
                f"significant_count_{autocorr_suffix}": row[f"significant_count_{autocorr_suffix}"],
                f"significant_share_{autocorr_suffix}": row[f"significant_share_{autocorr_suffix}"],
                f"primary_labels_{autocorr_suffix}": primary_labels,
                f"representative_ids_{autocorr_suffix}": list(row[f"{id_column}s_{autocorr_suffix}"][:top_ids]),
                f"intensity_score_{autocorr_suffix}": intensity_score,
                f"report_priority_{autocorr_suffix}": _autocorr_report_priority(family, intensity_score),
                f"{value_column}_mean_{autocorr_suffix}": row[f"{value_column}_mean_{autocorr_suffix}"],
                f"local_moran_i_mean_{autocorr_suffix}": row[f"local_moran_i_mean_{autocorr_suffix}"],
                f"local_geary_c_mean_{autocorr_suffix}": row[f"local_geary_c_mean_{autocorr_suffix}"],
                self.geometry_column: row[self.geometry_column],
            }
            report_rows.append(report_row)

        report_rows.sort(
            key=lambda row: (
                -float(row[f"intensity_score_{autocorr_suffix}"]),
                -int(row[f"feature_count_{autocorr_suffix}"]),
                str(row[f"local_cluster_family_{autocorr_suffix}"]),
            )
        )
        for index, row in enumerate(report_rows, start=1):
            row[f"report_rank_{autocorr_suffix}"] = index
        return GeoPromptFrame._from_internal_rows(report_rows, geometry_column=self.geometry_column, crs=self.crs)

    def snap_geometries(
        self,
        tolerance: float,
        include_diagnostics: bool = False,
        snap_suffix: str = "snap",
    ) -> "GeoPromptFrame":
        if tolerance <= 0:
            raise ValueError("tolerance must be greater than zero")
        if not self._rows:
            return GeoPromptFrame._from_internal_rows([], geometry_column=self.geometry_column, crs=self.crs)

        unique_vertices: dict[str, Coordinate] = {}
        for row in self._rows:
            geometry = row[self.geometry_column]
            geometry_kind = geometry_type(geometry)
            coordinates = geometry_vertices(geometry)
            if geometry_kind == "Polygon":
                coordinates = coordinates[:-1]
            for coordinate in coordinates:
                unique_vertices.setdefault(_coordinate_key(coordinate), coordinate)

        vertex_values = list(unique_vertices.values())
        vertex_index = SpatialIndex.from_points(vertex_values, cell_size=tolerance)
        snap_lookup = _build_snap_coordinate_lookup(vertex_values, vertex_index, tolerance)

        rows: list[Record] = []
        for row in self._rows:
            resolved = dict(row)
            snapped_geometry, changed_vertex_count, collapsed = _snap_geometry(
                row[self.geometry_column],
                snap_lookup,
            )
            resolved[self.geometry_column] = snapped_geometry
            resolved[f"changed_{snap_suffix}"] = changed_vertex_count > 0
            resolved[f"changed_vertex_count_{snap_suffix}"] = changed_vertex_count
            if include_diagnostics:
                vertex_count = len(geometry_vertices(row[self.geometry_column]))
                if geometry_type(row[self.geometry_column]) == "Polygon":
                    vertex_count -= 1
                resolved[f"vertex_count_{snap_suffix}"] = vertex_count
                resolved[f"collapsed_{snap_suffix}"] = collapsed
                resolved[f"unique_vertex_count_{snap_suffix}"] = len(unique_vertices)
                resolved[f"tolerance_{snap_suffix}"] = tolerance
            rows.append(resolved)

        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    def clean_topology(
        self,
        tolerance: float | None = None,
        min_segment_length: float = 0.0,
        include_diagnostics: bool = False,
        clean_suffix: str = "clean",
    ) -> "GeoPromptFrame":
        if tolerance is not None and tolerance <= 0:
            raise ValueError("tolerance must be greater than zero")
        if min_segment_length < 0:
            raise ValueError("min_segment_length must be zero or greater")
        if not self._rows:
            return GeoPromptFrame._from_internal_rows([], geometry_column=self.geometry_column, crs=self.crs)

        working_rows = self.snap_geometries(tolerance=tolerance, include_diagnostics=False)._rows if tolerance is not None else self._rows
        rows: list[Record] = []
        for original_row, working_row in zip(self._rows, working_rows, strict=True):
            cleaned_geometry, diagnostics = _clean_geometry(
                original_geometry=original_row[self.geometry_column],
                working_geometry=working_row[self.geometry_column],
                min_segment_length=min_segment_length,
            )
            resolved = dict(original_row)
            resolved[self.geometry_column] = cleaned_geometry
            resolved[f"changed_{clean_suffix}"] = diagnostics["changed"]
            resolved[f"removed_vertex_count_{clean_suffix}"] = diagnostics["removed_vertex_count"]
            resolved[f"removed_short_segment_count_{clean_suffix}"] = diagnostics["removed_short_segment_count"]
            if include_diagnostics:
                resolved[f"input_vertex_count_{clean_suffix}"] = diagnostics["input_vertex_count"]
                resolved[f"output_vertex_count_{clean_suffix}"] = diagnostics["output_vertex_count"]
                resolved[f"collapsed_{clean_suffix}"] = diagnostics["collapsed"]
                resolved[f"tolerance_{clean_suffix}"] = tolerance
                resolved[f"min_segment_length_{clean_suffix}"] = min_segment_length
            rows.append(resolved)

        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    def line_split(
        self,
        splitters: "GeoPromptFrame | None" = None,
        id_column: str = "site_id",
        splitter_id_column: str = "site_id",
        split_at_intersections: bool = True,
        include_diagnostics: bool = False,
        split_suffix: str = "split",
    ) -> "GeoPromptFrame":
        self._require_column(id_column)
        if any(geometry_type(row[self.geometry_column]) != "LineString" for row in self._rows):
            raise ValueError("line_split requires all geometries to be LineString")
        if splitters is not None and self.crs and splitters.crs and self.crs != splitters.crs:
            raise ValueError("frames must share the same CRS before line splitting")
        if splitters is not None and splitter_id_column not in splitters.columns:
            raise KeyError(f"column '{splitter_id_column}' is not present")
        if not self._rows:
            return GeoPromptFrame._from_internal_rows([], geometry_column=self.geometry_column, crs=self.crs)

        line_infos = [
            _build_linestring_info(row[self.geometry_column])
            for row in self._rows
        ]
        cut_points: list[dict[str, Coordinate]] = [
            {
                _coordinate_key(line_info["coordinates"][0]): line_info["coordinates"][0],
                _coordinate_key(line_info["coordinates"][-1]): line_info["coordinates"][-1],
            }
            for line_info in line_infos
        ]
        splitter_sources: list[set[str]] = [set() for _ in self._rows]
        splitter_point_counts = [0 for _ in self._rows]
        line_splitter_counts = [0 for _ in self._rows]
        self_intersection_counts = [0 for _ in self._rows]

        source_segments = _line_segment_records(self._rows, self.geometry_column)
        source_segment_index = SpatialIndex([record["bounds"] for record in source_segments]) if source_segments else SpatialIndex([])

        if split_at_intersections and source_segments:
            for segment_index, segment in enumerate(source_segments):
                for other_index in source_segment_index.query(segment["bounds"]):
                    if other_index <= segment_index:
                        continue
                    other = source_segments[other_index]
                    if segment["source_index"] == other["source_index"] and abs(segment["segment_index"] - other["segment_index"]) <= 1:
                        continue
                    intersection_points = _segment_intersection_points(segment["start"], segment["end"], other["start"], other["end"])
                    for point in intersection_points:
                        added_left = _register_cut_point(cut_points[segment["source_index"]], point)
                        added_right = _register_cut_point(cut_points[other["source_index"]], point)
                        if added_left:
                            self_intersection_counts[segment["source_index"]] += 1
                        if added_right:
                            self_intersection_counts[other["source_index"]] += 1

        if splitters is not None and splitters._rows:
            line_index = self.spatial_index(mode="geometry")
            point_splitters = [row for row in splitters._rows if geometry_type(row[splitters.geometry_column]) == "Point"]
            line_splitters = [row for row in splitters._rows if geometry_type(row[splitters.geometry_column]) == "LineString"]
            unsupported_types = [geometry_type(row[splitters.geometry_column]) for row in splitters._rows if geometry_type(row[splitters.geometry_column]) not in {"Point", "LineString"}]
            if unsupported_types:
                raise ValueError("line_split splitters must contain only Point or LineString geometries")

            for splitter_row in point_splitters:
                point = _as_coordinate(splitter_row[splitters.geometry_column]["coordinates"])
                point_bounds = (point[0], point[1], point[0], point[1])
                splitter_id = str(splitter_row[splitter_id_column])
                for line_index_value in line_index.query(point_bounds):
                    coordinates = line_infos[line_index_value]["coordinates"]
                    if any(_point_on_segment(point, start, end) for start, end in zip(coordinates, coordinates[1:])):
                        if _register_cut_point(cut_points[line_index_value], point):
                            splitter_point_counts[line_index_value] += 1
                        splitter_sources[line_index_value].add(splitter_id)

            if line_splitters:
                splitter_segments = _line_segment_records(line_splitters, splitters.geometry_column)
                for splitter_segment in splitter_segments:
                    splitter_id = str(line_splitters[splitter_segment["source_index"]][splitter_id_column])
                    for source_segment_index_value in source_segment_index.query(splitter_segment["bounds"]):
                        source_segment = source_segments[source_segment_index_value]
                        for point in _segment_intersection_points(
                            source_segment["start"],
                            source_segment["end"],
                            splitter_segment["start"],
                            splitter_segment["end"],
                        ):
                            if _register_cut_point(cut_points[source_segment["source_index"]], point):
                                line_splitter_counts[source_segment["source_index"]] += 1
                            splitter_sources[source_segment["source_index"]].add(splitter_id)

        rows: list[Record] = []
        for row_index, row in enumerate(self._rows):
            line_info = line_infos[row_index]
            fractions = sorted(
                {
                    0.0,
                    1.0,
                    *(
                        _locate_point_fraction_on_linestring(line_info, point)
                        for point in cut_points[row_index].values()
                    ),
                }
            )
            split_ranges = [
                (start_fraction, end_fraction)
                for start_fraction, end_fraction in zip(fractions, fractions[1:])
                if end_fraction > start_fraction + 1e-9
            ]
            part_rows: list[Record] = []
            source_id = str(row[id_column])
            ordered_splitter_ids = sorted(splitter_sources[row_index])
            for part_index, (start_fraction, end_fraction) in enumerate(split_ranges, start=1):
                split_geometry = _linestring_subgeometry(row[self.geometry_column], start_fraction, end_fraction)
                if split_geometry is None:
                    continue
                resolved = dict(row)
                resolved[self.geometry_column] = split_geometry
                resolved[f"source_id_{split_suffix}"] = source_id
                resolved[f"part_id_{split_suffix}"] = f"{source_id}-part-{part_index:05d}"
                resolved[f"part_index_{split_suffix}"] = part_index
                resolved[f"start_fraction_{split_suffix}"] = start_fraction
                resolved[f"end_fraction_{split_suffix}"] = end_fraction
                resolved[f"split_point_count_{split_suffix}"] = max(0, len(fractions) - 2)
                resolved[f"splitter_ids_{split_suffix}"] = ordered_splitter_ids
                if include_diagnostics:
                    resolved[f"self_intersection_count_{split_suffix}"] = self_intersection_counts[row_index]
                    resolved[f"point_splitter_count_{split_suffix}"] = splitter_point_counts[row_index]
                    resolved[f"line_splitter_count_{split_suffix}"] = line_splitter_counts[row_index]
                part_rows.append(resolved)
            for resolved in part_rows:
                resolved[f"part_count_{split_suffix}"] = len(part_rows)
                rows.append(resolved)

        rows.sort(key=lambda item: (str(item[f"source_id_{split_suffix}"]), int(item[f"part_index_{split_suffix}"])))
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs or (splitters.crs if splitters is not None else None))

    def polygon_split(
        self,
        splitters: "GeoPromptFrame",
        id_column: str = "site_id",
        splitter_id_column: str = "site_id",
        include_diagnostics: bool = False,
        split_suffix: str = "split",
    ) -> "GeoPromptFrame":
        self._require_column(id_column)
        splitters._require_column(splitter_id_column)
        if any(geometry_type(row[self.geometry_column]) != "Polygon" for row in self._rows):
            raise ValueError("polygon_split requires all geometries to be Polygon")
        if self.crs and splitters.crs and self.crs != splitters.crs:
            raise ValueError("frames must share the same CRS before polygon splitting")

        splitter_rows = list(splitters._rows)
        unsupported_types = [
            geometry_type(row[splitters.geometry_column])
            for row in splitter_rows
            if geometry_type(row[splitters.geometry_column]) not in {"LineString", "Polygon"}
        ]
        if unsupported_types:
            raise ValueError("polygon_split splitters must contain only LineString or Polygon geometries")
        if not self._rows:
            return GeoPromptFrame._from_internal_rows([], geometry_column=self.geometry_column, crs=self.crs)

        splitter_index = splitters.spatial_index(mode="geometry") if splitter_rows else SpatialIndex([])
        rows: list[Record] = []

        for row in self._rows:
            source_geometry = row[self.geometry_column]
            source_id = str(row[id_column])
            source_area = geometry_area(source_geometry)
            candidate_indexes = sorted(splitter_index.query(geometry_bounds(source_geometry)))
            applicable_indexes = [
                index
                for index in candidate_indexes
                if geometry_intersects(source_geometry, splitter_rows[index][splitters.geometry_column])
            ]
            faces = polygon_split_faces(
                source_geometry,
                [splitter_rows[index][splitters.geometry_column] for index in applicable_indexes],
            )
            ordered_faces = sorted(
                faces,
                key=lambda item: (
                    round(geometry_centroid(item[1])[0], 12),
                    round(geometry_centroid(item[1])[1], 12),
                    round(geometry_area(item[1]), 12),
                    str(item[1]["coordinates"]),
                ),
            )
            part_rows: list[Record] = []
            for part_index, (local_splitter_indexes, geometry) in enumerate(ordered_faces, start=1):
                splitter_ids = sorted(
                    {
                        str(splitter_rows[applicable_indexes[local_index]][splitter_id_column])
                        for local_index in local_splitter_indexes
                    }
                )
                resolved = dict(row)
                resolved[self.geometry_column] = geometry
                resolved[f"source_id_{split_suffix}"] = source_id
                resolved[f"part_id_{split_suffix}"] = f"{source_id}-part-{part_index:05d}"
                resolved[f"part_index_{split_suffix}"] = part_index
                resolved[f"splitter_ids_{split_suffix}"] = splitter_ids
                resolved[f"splitter_count_{split_suffix}"] = len(splitter_ids)
                resolved[f"area_{split_suffix}"] = geometry_area(geometry)
                if include_diagnostics:
                    resolved[f"candidate_splitter_count_{split_suffix}"] = len(candidate_indexes)
                    resolved[f"applied_splitter_count_{split_suffix}"] = len(applicable_indexes)
                    resolved[f"split_detected_{split_suffix}"] = len(ordered_faces) > 1
                    resolved[f"area_ratio_{split_suffix}"] = 0.0 if source_area <= 0.0 else geometry_area(geometry) / source_area
                part_rows.append(resolved)

            for resolved in part_rows:
                resolved[f"part_count_{split_suffix}"] = len(part_rows)
                rows.append(resolved)

        rows.sort(key=lambda item: (str(item[f"source_id_{split_suffix}"]), int(item[f"part_index_{split_suffix}"])))
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs or splitters.crs)

    def fishnet(
        self,
        cell_width: float,
        cell_height: float | None = None,
        include_empty: bool = False,
        grid_id_column: str = "grid_id",
    ) -> "GeoPromptFrame":
        if cell_width <= 0:
            raise ValueError("cell_width must be greater than zero")
        resolved_cell_height = cell_height if cell_height is not None else cell_width
        if resolved_cell_height <= 0:
            raise ValueError("cell_height must be greater than zero")
        if not self._rows:
            return GeoPromptFrame._from_internal_rows([], geometry_column=self.geometry_column, crs=self.crs)

        bounds = self.bounds()
        geometry_index = self.spatial_index(mode="geometry")
        rows: list[Record] = []

        row_index = 0
        y_value = bounds.min_y
        while y_value < bounds.max_y or math.isclose(y_value, bounds.max_y):
            column_index = 0
            x_value = bounds.min_x
            while x_value < bounds.max_x or math.isclose(x_value, bounds.max_x):
                cell_geometry = _rectangle_polygon(
                    x_value,
                    y_value,
                    min(x_value + cell_width, bounds.max_x),
                    min(y_value + resolved_cell_height, bounds.max_y),
                )
                cell_bounds = geometry_bounds(cell_geometry)
                candidate_indexes = geometry_index.query(cell_bounds)
                if include_empty or any(
                    geometry_intersects(cell_geometry, self._rows[index][self.geometry_column])
                    for index in candidate_indexes
                ):
                    rows.append(
                        {
                            grid_id_column: f"cell-{row_index:04d}-{column_index:04d}",
                            "grid_row": row_index,
                            "grid_column": column_index,
                            "cell_width": cell_width,
                            "cell_height": resolved_cell_height,
                            self.geometry_column: cell_geometry,
                        }
                    )
                column_index += 1
                x_value += cell_width
                if x_value > bounds.max_x and not math.isclose(x_value, bounds.max_x):
                    break
            row_index += 1
            y_value += resolved_cell_height
            if y_value > bounds.max_y and not math.isclose(y_value, bounds.max_y):
                break

        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    def hexbin(
        self,
        size: float,
        include_empty: bool = False,
        grid_id_column: str = "grid_id",
    ) -> "GeoPromptFrame":
        if size <= 0:
            raise ValueError("size must be greater than zero")
        if not self._rows:
            return GeoPromptFrame._from_internal_rows([], geometry_column=self.geometry_column, crs=self.crs)

        bounds = self.bounds()
        geometry_index = self.spatial_index(mode="geometry")
        hex_width = math.sqrt(3.0) * size
        vertical_step = 1.5 * size
        rows: list[Record] = []

        row_index = 0
        center_y = bounds.min_y + size
        while center_y <= bounds.max_y + size:
            offset_x = hex_width / 2.0 if row_index % 2 else 0.0
            column_index = 0
            center_x = bounds.min_x + offset_x
            while center_x <= bounds.max_x + hex_width:
                hex_geometry = _hexagon_polygon(center_x, center_y, size)
                hex_bounds = geometry_bounds(hex_geometry)
                candidate_indexes = geometry_index.query(hex_bounds)
                if include_empty or any(
                    geometry_intersects(hex_geometry, self._rows[index][self.geometry_column])
                    for index in candidate_indexes
                ):
                    rows.append(
                        {
                            grid_id_column: f"hex-{row_index:04d}-{column_index:04d}",
                            "grid_row": row_index,
                            "grid_column": column_index,
                            "hex_size": size,
                            self.geometry_column: hex_geometry,
                        }
                    )
                column_index += 1
                center_x += hex_width
            row_index += 1
            center_y += vertical_step

        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    def hotspot_grid(
        self,
        cell_size: float,
        shape: GridShape = "fishnet",
        value_column: str | None = None,
        aggregation: AggregationName = "count",
        include_empty: bool = False,
        include_diagnostics: bool = False,
        hotspot_suffix: str = "hotspot",
    ) -> "GeoPromptFrame":
        if cell_size <= 0:
            raise ValueError("cell_size must be greater than zero")
        if aggregation not in {"count", "sum", "mean", "min", "max"}:
            raise ValueError("aggregation must be 'count', 'sum', 'mean', 'min', or 'max'")
        if value_column is None and aggregation != "count":
            raise ValueError("value_column is required when aggregation is not 'count'")
        if value_column is not None:
            self._require_column(value_column)

        grid = self.fishnet(cell_size, include_empty=include_empty) if shape == "fishnet" else self.hexbin(cell_size, include_empty=include_empty)
        centroid_index = self.spatial_index(mode="centroid", cell_size=cell_size) if self._rows else None
        centroids = self._centroids()
        rows: list[Record] = []

        for cell_row in grid.to_records():
            cell_geometry = cell_row[self.geometry_column]
            cell_bounds = geometry_bounds(cell_geometry)
            candidate_indexes = centroid_index.query(cell_bounds) if centroid_index is not None else []
            matched_indexes = [
                index
                for index in candidate_indexes
                if geometry_within({"type": "Point", "coordinates": centroids[index]}, cell_geometry)
            ]
            matched_rows = [self._rows[index] for index in matched_indexes]

            resolved = dict(cell_row)
            resolved[f"count_{hotspot_suffix}"] = len(matched_rows)
            resolved[f"aggregation_{hotspot_suffix}"] = aggregation
            if include_diagnostics:
                resolved[f"candidate_count_{hotspot_suffix}"] = len(candidate_indexes)
                resolved[f"pruning_ratio_{hotspot_suffix}"] = 1.0 - (len(candidate_indexes) / len(self._rows) if self._rows else 0.0)
            if value_column is None:
                resolved[f"value_{hotspot_suffix}"] = float(len(matched_rows))
            else:
                values = [float(row[value_column]) for row in matched_rows if row.get(value_column) is not None]
                if not values:
                    resolved[f"{value_column}_{aggregation}_{hotspot_suffix}"] = None
                    resolved[f"value_{hotspot_suffix}"] = None
                elif aggregation == "sum":
                    resolved[f"{value_column}_sum_{hotspot_suffix}"] = sum(values)
                    resolved[f"value_{hotspot_suffix}"] = sum(values)
                elif aggregation == "mean":
                    resolved[f"{value_column}_mean_{hotspot_suffix}"] = sum(values) / len(values)
                    resolved[f"value_{hotspot_suffix}"] = sum(values) / len(values)
                elif aggregation == "min":
                    resolved[f"{value_column}_min_{hotspot_suffix}"] = min(values)
                    resolved[f"value_{hotspot_suffix}"] = min(values)
                elif aggregation == "max":
                    resolved[f"{value_column}_max_{hotspot_suffix}"] = max(values)
                    resolved[f"value_{hotspot_suffix}"] = max(values)
                else:
                    resolved[f"{value_column}_count_{hotspot_suffix}"] = len(values)
                    resolved[f"value_{hotspot_suffix}"] = float(len(values))
            rows.append(resolved)

        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    def network_build(
        self,
        id_column: str = "site_id",
        edge_id_prefix: str = "edge",
        node_id_prefix: str = "node",
        distance_method: str = "euclidean",
    ) -> "GeoPromptFrame":
        cache_key = ("network_build", id_column, edge_id_prefix, node_id_prefix, distance_method)
        cached_network = self._cache.get(cache_key)
        if cached_network is not None:
            return cached_network
        if distance_method not in {"euclidean", "haversine"}:
            raise ValueError("distance_method must be 'euclidean' or 'haversine'")
        if not self._rows:
            return GeoPromptFrame._from_internal_rows([], geometry_column=self.geometry_column, crs=self.crs)
        self._require_column(id_column)
        if any(geometry_type(row[self.geometry_column]) != "LineString" for row in self._rows):
            raise ValueError("network_build requires all geometries to be LineString")

        segment_records: list[dict[str, Any]] = []
        for row_index, row in enumerate(self._rows):
            vertices = list(row[self.geometry_column]["coordinates"])
            for segment_index in range(1, len(vertices)):
                start = _as_coordinate(vertices[segment_index - 1])
                end = _as_coordinate(vertices[segment_index])
                segment_records.append(
                    {
                        "source_row": row,
                        "source_index": row_index,
                        "source_id": str(row[id_column]),
                        "segment_index": segment_index - 1,
                        "start": start,
                        "end": end,
                        "bounds": (
                            min(start[0], end[0]),
                            min(start[1], end[1]),
                            max(start[0], end[0]),
                            max(start[1], end[1]),
                        ),
                    }
                )

        segment_index = SpatialIndex([segment["bounds"] for segment in segment_records])
        cut_points: list[set[Coordinate]] = [
            {segment["start"], segment["end"]}
            for segment in segment_records
        ]
        for index, segment in enumerate(segment_records):
            for other_index in segment_index.query(segment["bounds"]):
                if other_index <= index:
                    continue
                other = segment_records[other_index]
                for point in _segment_intersection_points(segment["start"], segment["end"], other["start"], other["end"]):
                    cut_points[index].add(point)
                    cut_points[other_index].add(point)

        edge_parts: list[dict[str, Any]] = []
        for segment, points in zip(segment_records, cut_points, strict=True):
            ordered_points = sorted(points, key=lambda point: _point_parameter(point, segment["start"], segment["end"]))
            for start_point, end_point in zip(ordered_points, ordered_points[1:]):
                if _same_coordinate(start_point, end_point):
                    continue
                edge_parts.append(
                    {
                        "source_id": segment["source_id"],
                        "source_segment_index": segment["segment_index"],
                        "start": start_point,
                        "end": end_point,
                    }
                )

        unique_nodes = sorted(
            {_coordinate_key(edge["start"]): edge["start"] for edge in edge_parts} | {_coordinate_key(edge["end"]): edge["end"] for edge in edge_parts}
        )
        node_lookup = {
            node_key: f"{node_id_prefix}-{index:05d}"
            for index, node_key in enumerate(unique_nodes)
        }

        rows: list[Record] = []
        for edge_index, edge in enumerate(edge_parts):
            start_key = _coordinate_key(edge["start"])
            end_key = _coordinate_key(edge["end"])
            start_node_id = node_lookup[start_key]
            end_node_id = node_lookup[end_key]
            line_geometry: Geometry = {"type": "LineString", "coordinates": (edge["start"], edge["end"])}
            rows.append(
                {
                    "edge_id": f"{edge_id_prefix}-{edge_index:05d}",
                    "source_id": edge["source_id"],
                    "source_segment_index": edge["source_segment_index"],
                    "from_node_id": start_node_id,
                    "to_node_id": end_node_id,
                    "from_node": edge["start"],
                    "to_node": edge["end"],
                    "edge_length": geometry_length(line_geometry) if distance_method == "euclidean" else coordinate_distance(edge["start"], edge["end"], method=distance_method),
                    self.geometry_column: line_geometry,
                }
            )

        rows.sort(key=lambda row: (str(row["source_id"]), int(row["source_segment_index"]), str(row["from_node_id"]), str(row["to_node_id"])))
        network_frame = GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)
        self._cache[cache_key] = network_frame
        return network_frame

    def service_area(
        self,
        origins: str | Coordinate | Sequence[str | Coordinate],
        max_cost: float,
        from_node_id_column: str = "from_node_id",
        to_node_id_column: str = "to_node_id",
        from_node_column: str = "from_node",
        to_node_column: str = "to_node",
        cost_column: str = "edge_length",
        directed: bool = False,
        include_partial_edges: bool = False,
        include_diagnostics: bool = False,
        service_suffix: str = "service",
    ) -> "GeoPromptFrame":
        if max_cost < 0:
            raise ValueError("max_cost must be zero or greater")
        for column in (from_node_id_column, to_node_id_column, from_node_column, to_node_column, cost_column):
            self._require_column(column)
        if not self._rows:
            return GeoPromptFrame._from_internal_rows([], geometry_column=self.geometry_column, crs=self.crs)

        if isinstance(origins, str) or _is_coordinate_value(origins):
            origin_values = [origins]
        else:
            origin_values = list(origins)  # type: ignore[arg-type]

        origin_node_ids = [
            self._resolve_network_node(origin, from_node_id_column, to_node_id_column, from_node_column, to_node_column)
            for origin in origin_values
        ]
        adjacency = self._network_graph(from_node_id_column, to_node_id_column, cost_column, directed=directed)
        distances = _dijkstra_distances(adjacency, origin_node_ids)

        rows: list[Record] = []
        partial_edge_count = 0
        for row in self._rows:
            from_node_id = str(row[from_node_id_column])
            to_node_id = str(row[to_node_id_column])
            from_cost = distances.get(from_node_id)
            to_cost = distances.get(to_node_id)
            edge_cost = float(row[cost_column])

            intervals = _reachable_edge_intervals(
                from_cost=from_cost,
                to_cost=to_cost,
                edge_cost=edge_cost,
                max_cost=max_cost,
                directed=directed,
            )
            if not intervals:
                continue

            interval_rows = intervals if include_partial_edges else [intervals[0]]
            for interval_index, (coverage_start, coverage_end) in enumerate(interval_rows, start=1):
                if not include_partial_edges and (coverage_start > 1e-9 or coverage_end < 1.0 - 1e-9):
                    continue
                clipped_geometry = row[self.geometry_column]
                if coverage_start > 1e-9 or coverage_end < 1.0 - 1e-9:
                    clipped_geometry = _linestring_subgeometry(row[self.geometry_column], coverage_start, coverage_end)
                    if clipped_geometry is None:
                        continue
                    partial_edge_count += 1

                resolved = dict(row)
                resolved[self.geometry_column] = clipped_geometry
                resolved[f"origin_nodes_{service_suffix}"] = list(origin_node_ids)
                resolved[f"max_cost_{service_suffix}"] = max_cost
                resolved[f"cost_from_node_{service_suffix}"] = from_cost
                resolved[f"cost_to_node_{service_suffix}"] = to_cost
                resolved[f"cost_min_{service_suffix}"] = min(value for value in (from_cost, to_cost) if value is not None)
                resolved[f"segment_index_{service_suffix}"] = interval_index
                resolved[f"segment_count_{service_suffix}"] = len(interval_rows)
                resolved[f"coverage_start_{service_suffix}"] = coverage_start
                resolved[f"coverage_end_{service_suffix}"] = coverage_end
                resolved[f"coverage_ratio_{service_suffix}"] = coverage_end - coverage_start
                resolved[f"partial_{service_suffix}"] = coverage_start > 1e-9 or coverage_end < 1.0 - 1e-9
                if include_diagnostics:
                    resolved[f"origin_count_{service_suffix}"] = len(origin_node_ids)
                    resolved[f"reached_node_count_{service_suffix}"] = len(distances)
                    resolved[f"network_node_count_{service_suffix}"] = len(adjacency)
                    resolved[f"input_edge_count_{service_suffix}"] = len(self._rows)
                rows.append(resolved)

        if include_diagnostics:
            for row in rows:
                row[f"reachable_segment_count_{service_suffix}"] = len(rows)
                row[f"partial_edge_count_{service_suffix}"] = partial_edge_count

        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    def shortest_path(
        self,
        origin: str | Coordinate,
        destination: str | Coordinate,
        edge_id_column: str = "edge_id",
        from_node_id_column: str = "from_node_id",
        to_node_id_column: str = "to_node_id",
        from_node_column: str = "from_node",
        to_node_column: str = "to_node",
        cost_column: str = "edge_length",
        directed: bool = False,
        include_diagnostics: bool = False,
        path_suffix: str = "path",
    ) -> "GeoPromptFrame":
        for column in (edge_id_column, from_node_id_column, to_node_id_column, from_node_column, to_node_column, cost_column):
            self._require_column(column)
        if not self._rows:
            return GeoPromptFrame._from_internal_rows([], geometry_column=self.geometry_column, crs=self.crs)

        origin_node_id = self._resolve_network_node(origin, from_node_id_column, to_node_id_column, from_node_column, to_node_column)
        destination_node_id = self._resolve_network_node(destination, from_node_id_column, to_node_id_column, from_node_column, to_node_column)

        adjacency = self._network_graph(from_node_id_column, to_node_id_column, cost_column, directed=directed)
        distances: dict[str, float] = {origin_node_id: 0.0}
        previous: dict[str, tuple[str, int]] = {}
        queue: list[tuple[float, str]] = [(0.0, origin_node_id)]
        visited: set[str] = set()
        relaxation_count = 0

        while queue:
            current_cost, current_node = heappop(queue)
            if current_node in visited:
                continue
            visited.add(current_node)
            if current_node == destination_node_id:
                break
            for next_node, edge_cost, edge_index in adjacency.get(current_node, []):
                path_cost = current_cost + edge_cost
                if path_cost < distances.get(next_node, float("inf")):
                    distances[next_node] = path_cost
                    previous[next_node] = (current_node, edge_index)
                    heappush(queue, (path_cost, next_node))
                    relaxation_count += 1

        if destination_node_id not in distances:
            return GeoPromptFrame._from_internal_rows([], geometry_column=self.geometry_column, crs=self.crs)

        path_edge_indexes: list[int] = []
        node_sequence: list[str] = [destination_node_id]
        current_node = destination_node_id
        while current_node != origin_node_id:
            previous_node, edge_index = previous[current_node]
            path_edge_indexes.append(edge_index)
            node_sequence.append(previous_node)
            current_node = previous_node

        path_edge_indexes.reverse()
        node_sequence.reverse()
        total_cost = distances[destination_node_id]
        rows: list[Record] = []
        for step_index, edge_index in enumerate(path_edge_indexes, start=1):
            resolved = dict(self._rows[edge_index])
            resolved[f"step_{path_suffix}"] = step_index
            resolved[f"origin_node_{path_suffix}"] = origin_node_id
            resolved[f"destination_node_{path_suffix}"] = destination_node_id
            resolved[f"total_cost_{path_suffix}"] = total_cost
            resolved[f"edge_count_{path_suffix}"] = len(path_edge_indexes)
            resolved[f"node_sequence_{path_suffix}"] = list(node_sequence)
            if include_diagnostics:
                resolved[f"visited_node_count_{path_suffix}"] = len(visited)
                resolved[f"relaxation_count_{path_suffix}"] = relaxation_count
                resolved[f"network_node_count_{path_suffix}"] = len(adjacency)
            rows.append(resolved)

        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    def location_allocate(
        self,
        facilities: "GeoPromptFrame",
        demands: "GeoPromptFrame",
        facility_id_column: str = "site_id",
        demand_id_column: str = "site_id",
        demand_weight_column: str | None = None,
        facility_capacity_column: str | None = None,
        aggregations: dict[str, AggregationName] | None = None,
        how: SpatialJoinMode = "left",
        max_cost: float | None = None,
        facility_node_column: str | None = None,
        demand_node_column: str | None = None,
        from_node_id_column: str = "from_node_id",
        to_node_id_column: str = "to_node_id",
        from_node_column: str = "from_node",
        to_node_column: str = "to_node",
        cost_column: str = "edge_length",
        directed: bool = False,
        include_diagnostics: bool = False,
        allocation_suffix: str = "allocate",
    ) -> "GeoPromptFrame":
        if how not in {"inner", "left"}:
            raise ValueError("how must be 'inner' or 'left'")
        if max_cost is not None and max_cost < 0:
            raise ValueError("max_cost must be zero or greater")
        for column in (from_node_id_column, to_node_id_column, from_node_column, to_node_column, cost_column):
            self._require_column(column)
        if self.crs and facilities.crs and self.crs != facilities.crs:
            raise ValueError("frames must share the same CRS before location allocation")
        if self.crs and demands.crs and self.crs != demands.crs:
            raise ValueError("frames must share the same CRS before location allocation")

        facilities._require_column(facility_id_column)
        demands._require_column(demand_id_column)
        if demand_weight_column is not None:
            demands._require_column(demand_weight_column)
        if facility_capacity_column is not None:
            facilities._require_column(facility_capacity_column)
        if facility_node_column is not None:
            facilities._require_column(facility_node_column)
        if demand_node_column is not None:
            demands._require_column(demand_node_column)
        if not facilities._rows:
            return GeoPromptFrame._from_internal_rows([], geometry_column=facilities.geometry_column, crs=facilities.crs or demands.crs)

        adjacency = self._network_graph(from_node_id_column, to_node_id_column, cost_column, directed=directed)

        def resolve_row_node(row: Record, geometry_column: str, node_column: str | None) -> str:
            if node_column is None:
                return self._resolve_network_node(
                    geometry_centroid(row[geometry_column]),
                    from_node_id_column,
                    to_node_id_column,
                    from_node_column,
                    to_node_column,
                )
            node_value = row[node_column]
            if isinstance(node_value, str):
                return self._resolve_network_node(
                    node_value,
                    from_node_id_column,
                    to_node_id_column,
                    from_node_column,
                    to_node_column,
                )
            if isinstance(node_value, dict):
                geometry = normalize_geometry(node_value)
                if geometry_type(geometry) == "Point":
                    return self._resolve_network_node(
                        _as_coordinate(geometry["coordinates"]),
                        from_node_id_column,
                        to_node_id_column,
                        from_node_column,
                        to_node_column,
                    )
                return self._resolve_network_node(
                    geometry_centroid(geometry),
                    from_node_id_column,
                    to_node_id_column,
                    from_node_column,
                    to_node_column,
                )
            if _is_coordinate_value(node_value):
                return self._resolve_network_node(
                    _as_coordinate(node_value),
                    from_node_id_column,
                    to_node_id_column,
                    from_node_column,
                    to_node_column,
                )
            raise TypeError("network node references must be node ids, point geometries, or coordinate pairs")

        facility_rows = list(facilities._rows)
        demand_rows = list(demands._rows)
        facility_node_ids = [
            resolve_row_node(row, facilities.geometry_column, facility_node_column)
            for row in facility_rows
        ]
        demand_node_ids = [
            resolve_row_node(row, demands.geometry_column, demand_node_column)
            for row in demand_rows
        ]
        demand_weights = [
            float(row[demand_weight_column]) if demand_weight_column is not None else 1.0
            for row in demand_rows
        ]
        for weight in demand_weights:
            if weight < 0:
                raise ValueError("demand weights must be zero or greater")

        facility_capacities = [
            float(row[facility_capacity_column]) if facility_capacity_column is not None else float("inf")
            for row in facility_rows
        ]
        for capacity in facility_capacities:
            if capacity < 0:
                raise ValueError("facility capacities must be zero or greater")
        remaining_capacities = list(facility_capacities)

        unique_demand_nodes = {node_id for node_id in demand_node_ids}
        demand_candidates: dict[int, list[tuple[float, int]]] = {index: [] for index in range(len(demand_rows))}
        candidate_route_count = 0

        for facility_index, facility_node_id in enumerate(facility_node_ids):
            distances = _dijkstra_distances(adjacency, [facility_node_id], stop_nodes=unique_demand_nodes)
            for demand_index, demand_node_id in enumerate(demand_node_ids):
                distance_value = distances.get(demand_node_id)
                if distance_value is None:
                    continue
                if max_cost is not None and distance_value > max_cost:
                    continue
                demand_candidates[demand_index].append((distance_value, facility_index))
                candidate_route_count += 1

        for demand_index, candidates in demand_candidates.items():
            candidates.sort(
                key=lambda item: (
                    item[0],
                    str(facility_rows[item[1]][facility_id_column]),
                    item[1],
                )
            )

        demand_order = sorted(
            range(len(demand_rows)),
            key=lambda index: (
                demand_candidates[index][0][0] if demand_candidates[index] else float("inf"),
                str(demand_rows[index][demand_id_column]),
            ),
        )

        assigned_matches: dict[int, list[tuple[Record, float, float, str]]] = {
            index: [] for index in range(len(facility_rows))
        }
        unallocated_rows: list[Record] = []
        for demand_index in demand_order:
            demand_row = demand_rows[demand_index]
            demand_weight = demand_weights[demand_index]
            demand_id = str(demand_row[demand_id_column])
            selected_facility_index: int | None = None
            selected_cost: float | None = None
            for distance_value, facility_index in demand_candidates[demand_index]:
                if remaining_capacities[facility_index] + 1e-9 < demand_weight:
                    continue
                selected_facility_index = facility_index
                selected_cost = distance_value
                break

            if selected_facility_index is None or selected_cost is None:
                unallocated_rows.append(demand_row)
                continue

            if facility_capacity_column is not None:
                remaining_capacities[selected_facility_index] -= demand_weight
            assigned_matches[selected_facility_index].append(
                (demand_row, selected_cost, demand_weight, demand_id)
            )

        rows: list[Record] = []
        unallocated_demand_ids = [str(row[demand_id_column]) for row in unallocated_rows]
        total_allocated = sum(len(matches) for matches in assigned_matches.values())
        for facility_index, facility_row in enumerate(facility_rows):
            matches = assigned_matches[facility_index]
            if not matches and how == "inner":
                continue

            costs = [cost for _row, cost, _weight, _id in matches]
            weights = [weight for _row, _cost, weight, _id in matches]
            allocated_rows = [row for row, _cost, _weight, _id in matches]
            resolved = dict(facility_row)
            resolved[f"{demand_id_column}s_{allocation_suffix}"] = [demand_id for _row, _cost, _weight, demand_id in matches]
            resolved[f"count_{allocation_suffix}"] = len(matches)
            resolved[f"cost_min_{allocation_suffix}"] = min(costs) if costs else None
            resolved[f"cost_max_{allocation_suffix}"] = max(costs) if costs else None
            resolved[f"cost_mean_{allocation_suffix}"] = sum(costs) / len(costs) if costs else None
            resolved[f"allocated_weight_{allocation_suffix}"] = sum(weights)
            resolved[f"facility_node_{allocation_suffix}"] = facility_node_ids[facility_index]
            resolved[f"{demand_id_column}s_unallocated_{allocation_suffix}"] = list(unallocated_demand_ids)
            resolved[f"count_unallocated_{allocation_suffix}"] = len(unallocated_demand_ids)
            if facility_capacity_column is not None:
                resolved[f"capacity_used_{allocation_suffix}"] = facility_capacities[facility_index] - remaining_capacities[facility_index]
                resolved[f"capacity_remaining_{allocation_suffix}"] = remaining_capacities[facility_index]
            else:
                resolved[f"capacity_used_{allocation_suffix}"] = None
                resolved[f"capacity_remaining_{allocation_suffix}"] = None
            resolved.update(self._aggregate_rows(allocated_rows, aggregations=aggregations, suffix=allocation_suffix))
            if include_diagnostics:
                resolved[f"facility_count_{allocation_suffix}"] = len(facility_rows)
                resolved[f"demand_count_{allocation_suffix}"] = len(demand_rows)
                resolved[f"allocated_count_{allocation_suffix}"] = total_allocated
                resolved[f"candidate_route_count_{allocation_suffix}"] = candidate_route_count
                resolved[f"facility_node_count_{allocation_suffix}"] = len(set(facility_node_ids))
                resolved[f"demand_node_count_{allocation_suffix}"] = len(unique_demand_nodes)
                resolved[f"network_node_count_{allocation_suffix}"] = len(adjacency)
            rows.append(resolved)

        return GeoPromptFrame._from_internal_rows(rows, geometry_column=facilities.geometry_column, crs=facilities.crs or demands.crs or self.crs)

    def _resolve_network_node(
        self,
        node: str | Coordinate,
        from_node_id_column: str,
        to_node_id_column: str,
        from_node_column: str,
        to_node_column: str,
    ) -> str:
        if isinstance(node, str):
            node_ids = {str(row[from_node_id_column]) for row in self._rows} | {str(row[to_node_id_column]) for row in self._rows}
            if node not in node_ids:
                raise KeyError(f"network node '{node}' was not found")
            return node

        target_coordinate = _as_coordinate(normalize_geometry(node)["coordinates"])
        node_coordinates: dict[str, Coordinate] = {}
        for row in self._rows:
            node_coordinates[str(row[from_node_id_column])] = _as_coordinate(row[from_node_column])
            node_coordinates[str(row[to_node_id_column])] = _as_coordinate(row[to_node_column])
        return min(
            node_coordinates,
            key=lambda node_id: (
                coordinate_distance(target_coordinate, node_coordinates[node_id], method="euclidean"),
                node_id,
            ),
        )

    def _network_graph(
        self,
        from_node_id_column: str,
        to_node_id_column: str,
        cost_column: str,
        directed: bool,
    ) -> dict[str, list[tuple[str, float, int]]]:
        cache_key = ("network_graph", from_node_id_column, to_node_id_column, cost_column, directed)
        cached_graph = self._cache.get(cache_key)
        if cached_graph is not None:
            return cached_graph

        adjacency: dict[str, list[tuple[str, float, int]]] = {}
        for index, row in enumerate(self._rows):
            from_node_id = str(row[from_node_id_column])
            to_node_id = str(row[to_node_id_column])
            edge_cost = float(row[cost_column])
            adjacency.setdefault(from_node_id, []).append((to_node_id, edge_cost, index))
            if not directed:
                adjacency.setdefault(to_node_id, []).append((from_node_id, edge_cost, index))
        self._cache[cache_key] = adjacency
        return adjacency

    def trajectory_match(
        self,
        observations: "GeoPromptFrame",
        track_id_column: str = "track_id",
        sequence_column: str = "sequence",
        observation_id_column: str = "site_id",
        edge_id_column: str = "edge_id",
        from_node_id_column: str = "from_node_id",
        to_node_id_column: str = "to_node_id",
        cost_column: str = "edge_length",
        candidate_k: int = 3,
        max_distance: float | None = None,
        transition_weight: float = 1.25,
        transition_mode: TrajectoryTransitionMode = "hmm",
        gap_penalty: float = 7.5,
        allow_gaps: bool = True,
        distance_method: str = "euclidean",
        include_diagnostics: bool = False,
        match_suffix: str = "match",
    ) -> "GeoPromptFrame":
        if candidate_k <= 0:
            raise ValueError("candidate_k must be greater than zero")
        if max_distance is not None and max_distance < 0:
            raise ValueError("max_distance must be zero or greater")
        if transition_weight < 0:
            raise ValueError("transition_weight must be zero or greater")
        if transition_mode not in {"network_cost", "hmm"}:
            raise ValueError("transition_mode must be 'network_cost' or 'hmm'")
        if gap_penalty < 0:
            raise ValueError("gap_penalty must be zero or greater")
        if self.crs and observations.crs and self.crs != observations.crs:
            raise ValueError("frames must share the same CRS before trajectory matching")
        for column in (edge_id_column, from_node_id_column, to_node_id_column, cost_column):
            self._require_column(column)
        for column in (track_id_column, sequence_column, observation_id_column):
            observations._require_column(column)
        if any(geometry_type(row[self.geometry_column]) != "LineString" for row in self._rows):
            raise ValueError("trajectory_match requires LineString geometries on the network frame")
        if any(geometry_type(row[observations.geometry_column]) != "Point" for row in observations._rows):
            raise ValueError("trajectory_match requires Point geometries on the observations frame")

        edge_rows = list(self._rows)
        observation_rows = list(observations._rows)
        edge_index = self.spatial_index(mode="geometry") if edge_rows else SpatialIndex([])
        adjacency = self._network_graph(from_node_id_column, to_node_id_column, cost_column, directed=False)
        edge_columns = [column for column in self.columns if column != self.geometry_column]
        node_distance_cache: dict[str, dict[str, float]] = {}
        transition_cache: dict[tuple[int, int, float, float], float] = {}

        grouped_tracks: dict[str, list[Record]] = {}
        for row in observation_rows:
            grouped_tracks.setdefault(str(row[track_id_column]), []).append(row)

        rows: list[Record] = []
        for track_id, track_rows in sorted(grouped_tracks.items(), key=lambda item: item[0]):
            ordered_track_rows = sorted(
                track_rows,
                key=lambda row: (row[sequence_column], str(row[observation_id_column])),
            )
            candidate_sets: list[list[dict[str, Any]]] = []
            for row in ordered_track_rows:
                point = _as_coordinate(row[observations.geometry_column]["coordinates"])
                if max_distance is not None:
                    candidate_indexes = edge_index.query(
                        (
                            point[0] - max_distance,
                            point[1] - max_distance,
                            point[0] + max_distance,
                            point[1] + max_distance,
                        )
                    )
                else:
                    candidate_indexes = list(range(len(edge_rows)))

                candidates: list[dict[str, Any]] = []
                for edge_index_value in candidate_indexes:
                    edge_row = edge_rows[edge_index_value]
                    offset_distance, along_distance = _point_to_polyline_distance_details(
                        point,
                        tuple(_as_coordinate(value) for value in edge_row[self.geometry_column]["coordinates"]),
                        method=distance_method,
                    )
                    if max_distance is not None and offset_distance > max_distance:
                        continue
                    candidates.append(
                        {
                            "edge_index": edge_index_value,
                            "offset_distance": offset_distance,
                            "along_distance": along_distance,
                            "edge_id": str(edge_row[edge_id_column]),
                        }
                    )
                candidates.sort(key=lambda item: (float(item["offset_distance"]), str(item["edge_id"])))
                candidate_sets.append(candidates[:candidate_k])

            previous_scores: list[dict[str, Any]] | None = None
            track_states: list[list[dict[str, Any]]] = []
            previous_point: tuple[float, float] | None = None
            for row, candidates in zip(ordered_track_rows, candidate_sets, strict=True):
                current_scores: list[dict[str, Any]] = []
                point = _as_coordinate(row[observations.geometry_column]["coordinates"])
                observed_step_distance = coordinate_distance(previous_point, point, method=distance_method) if previous_point is not None else 0.0
                state_candidates = list(candidates)
                if allow_gaps:
                    state_candidates.append(
                        {
                            "edge_index": None,
                            "offset_distance": gap_penalty,
                            "along_distance": None,
                            "edge_id": None,
                            "gap_state": True,
                        }
                    )
                if not state_candidates:
                    track_states.append([])
                    previous_scores = None
                    previous_point = point
                    continue
                for candidate in state_candidates:
                    gap_state = bool(candidate.get("gap_state", False))
                    best_score = candidate["offset_distance"]
                    best_previous_state_index: int | None = None
                    best_transition_cost = 0.0
                    best_transition_penalty = 0.0
                    best_transition_mismatch = 0.0
                    if previous_scores is not None:
                        best_score = float("inf")
                        for previous_state_index, previous in enumerate(previous_scores):
                            if gap_state or previous.get("gap_state", False):
                                transition_cost = 0.0
                                transition_penalty = _gap_transition_penalty(
                                    previous_gap_state=bool(previous.get("gap_state", False)),
                                    current_gap_state=gap_state,
                                    gap_penalty=gap_penalty,
                                )
                                transition_mismatch = observed_step_distance if transition_penalty > 0.0 else 0.0
                            else:
                                transition_cost = _edge_transition_cost(
                                    previous["edge_index"],
                                    candidate["edge_index"],
                                    float(previous["along_distance"]),
                                    float(candidate["along_distance"]),
                                    edge_rows,
                                    adjacency,
                                    from_node_id_column,
                                    to_node_id_column,
                                    cost_column,
                                    node_distance_cache,
                                    transition_cache,
                                )
                                transition_mismatch = abs(transition_cost - observed_step_distance)
                                if transition_mode == "hmm":
                                    transition_penalty = (0.5 * transition_cost) + transition_mismatch
                                else:
                                    transition_penalty = transition_cost
                            total_score = previous["score"] + candidate["offset_distance"] + (transition_weight * transition_penalty)
                            if total_score < best_score:
                                best_score = total_score
                                best_previous_state_index = previous_state_index
                                best_transition_cost = transition_cost
                                best_transition_penalty = transition_penalty
                                best_transition_mismatch = transition_mismatch
                    current_scores.append(
                        {
                            **candidate,
                            "gap_state": gap_state,
                            "score": best_score,
                            "previous_state_index": best_previous_state_index,
                            "transition_cost": best_transition_cost,
                            "transition_penalty": best_transition_penalty,
                            "transition_mismatch": best_transition_mismatch,
                            "observed_step_distance": observed_step_distance,
                        }
                    )
                track_states.append(current_scores)
                previous_scores = current_scores
                previous_point = point

            chosen_state_indexes: list[int | None] = [None] * len(ordered_track_rows)
            next_state_index: int | None = None
            for observation_index in range(len(ordered_track_rows) - 1, -1, -1):
                states = track_states[observation_index]
                if not states:
                    next_state_index = None
                    continue
                if next_state_index is None or next_state_index >= len(states):
                    best_state_index = min(
                        range(len(states)),
                        key=lambda state_index: (
                            float(states[state_index]["score"]),
                            int(bool(states[state_index].get("gap_state", False))),
                            str(states[state_index].get("edge_id")),
                        ),
                    )
                else:
                    best_state_index = next_state_index
                chosen_state_indexes[observation_index] = best_state_index
                next_state_index = states[best_state_index]["previous_state_index"]

            continuity_states: list[str] = []
            segment_indexes: list[int | None] = []
            current_segment_index = 0
            previous_was_gap = True
            for row_index, state_index in enumerate(chosen_state_indexes):
                states = track_states[row_index]
                if state_index is None or not states:
                    continuity_states.append("unmatched")
                    segment_indexes.append(None)
                    previous_was_gap = True
                    continue
                selected_state = states[state_index]
                if selected_state.get("gap_state", False):
                    continuity_states.append("gap")
                    segment_indexes.append(None)
                    previous_was_gap = True
                    continue
                if current_segment_index == 0:
                    current_segment_index = 1
                    continuity_states.append("start")
                elif previous_was_gap:
                    current_segment_index += 1
                    continuity_states.append("resume")
                else:
                    continuity_states.append("continuation")
                segment_indexes.append(current_segment_index)
                previous_was_gap = False

            for row_index, row in enumerate(ordered_track_rows):
                states = track_states[row_index]
                resolved = dict(row)
                resolved[f"track_{match_suffix}"] = track_id
                resolved[f"candidate_count_{match_suffix}"] = sum(1 for state in states if not state.get("gap_state", False))
                resolved[f"continuity_state_{match_suffix}"] = continuity_states[row_index]
                resolved[f"segment_index_{match_suffix}"] = segment_indexes[row_index]
                if not states or chosen_state_indexes[row_index] is None:
                    resolved[f"matched_{match_suffix}"] = False
                    resolved[f"{edge_id_column}_{match_suffix}"] = None
                    resolved[f"distance_{match_suffix}"] = None
                    resolved[f"along_distance_{match_suffix}"] = None
                    resolved[f"transition_cost_{match_suffix}"] = None
                    if include_diagnostics:
                        resolved[f"gap_state_{match_suffix}"] = False
                    rows.append(resolved)
                    continue

                selected_state = states[chosen_state_indexes[row_index]]
                if selected_state.get("gap_state", False):
                    resolved[f"matched_{match_suffix}"] = False
                    resolved[f"{edge_id_column}_{match_suffix}"] = None
                    resolved[f"distance_{match_suffix}"] = None
                    resolved[f"along_distance_{match_suffix}"] = None
                    resolved[f"transition_cost_{match_suffix}"] = None
                    if include_diagnostics:
                        resolved[f"candidate_{edge_id_column}s_{match_suffix}"] = [state["edge_id"] for state in states if not state.get("gap_state", False)]
                        resolved[f"score_{match_suffix}"] = selected_state["score"]
                        resolved[f"candidate_k_{match_suffix}"] = candidate_k
                        resolved[f"gap_state_{match_suffix}"] = True
                        resolved[f"transition_penalty_{match_suffix}"] = selected_state["transition_penalty"]
                        resolved[f"transition_mismatch_{match_suffix}"] = selected_state["transition_mismatch"]
                        resolved[f"observed_step_distance_{match_suffix}"] = selected_state["observed_step_distance"]
                        resolved[f"transition_mode_{match_suffix}"] = transition_mode
                    rows.append(resolved)
                    continue

                matched_edge = edge_rows[selected_state["edge_index"]]
                for column in edge_columns:
                    target_name = column if column not in resolved else f"{column}_{match_suffix}"
                    resolved[target_name] = matched_edge[column]
                resolved[f"matched_{match_suffix}"] = True
                resolved[f"{edge_id_column}_{match_suffix}"] = str(matched_edge[edge_id_column])
                resolved[f"distance_{match_suffix}"] = selected_state["offset_distance"]
                resolved[f"along_distance_{match_suffix}"] = selected_state["along_distance"]
                resolved[f"transition_cost_{match_suffix}"] = selected_state["transition_cost"]
                if include_diagnostics:
                    resolved[f"candidate_{edge_id_column}s_{match_suffix}"] = [state["edge_id"] for state in states if not state.get("gap_state", False)]
                    resolved[f"score_{match_suffix}"] = selected_state["score"]
                    resolved[f"candidate_k_{match_suffix}"] = candidate_k
                    resolved[f"gap_state_{match_suffix}"] = False
                    resolved[f"transition_penalty_{match_suffix}"] = selected_state["transition_penalty"]
                    resolved[f"transition_mismatch_{match_suffix}"] = selected_state["transition_mismatch"]
                    resolved[f"observed_step_distance_{match_suffix}"] = selected_state["observed_step_distance"]
                    resolved[f"transition_mode_{match_suffix}"] = transition_mode
                rows.append(resolved)

        rows.sort(key=lambda row: (str(row[track_id_column]), row[sequence_column], str(row[observation_id_column])))
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=observations.geometry_column, crs=observations.crs or self.crs)

    def summarize_trajectory_segments(
        self,
        track_id_column: str = "track_id",
        sequence_column: str = "sequence",
        observation_id_column: str = "site_id",
        edge_id_column: str = "edge_id",
        match_suffix: str = "match",
    ) -> "GeoPromptFrame":
        self._require_column(track_id_column)
        self._require_column(sequence_column)
        self._require_column(observation_id_column)
        self._require_column(f"matched_{match_suffix}")
        self._require_column(f"continuity_state_{match_suffix}")
        self._require_column(f"segment_index_{match_suffix}")
        self._require_column(f"{edge_id_column}_{match_suffix}")

        grouped_rows: dict[tuple[str, int], list[Record]] = {}
        for row in self._rows:
            if not bool(row.get(f"matched_{match_suffix}")):
                continue
            segment_index = row.get(f"segment_index_{match_suffix}")
            if segment_index is None:
                continue
            grouped_rows.setdefault((str(row[track_id_column]), int(segment_index)), []).append(row)

        rows: list[Record] = []
        for (track_id, segment_index), segment_rows in sorted(grouped_rows.items(), key=lambda item: (item[0][0], item[0][1])):
            ordered_rows = sorted(segment_rows, key=lambda row: (row[sequence_column], str(row[observation_id_column])))
            observation_ids = [str(row[observation_id_column]) for row in ordered_rows]
            path_edge_ids = _consecutive_distinct_values(str(row[f"{edge_id_column}_{match_suffix}"]) for row in ordered_rows if row.get(f"{edge_id_column}_{match_suffix}") is not None)
            coordinates = [
                list(_as_coordinate(row[self.geometry_column]["coordinates"]))
                for row in ordered_rows
            ]
            summary_geometry: Geometry
            if len(coordinates) == 1:
                summary_geometry = {"type": "Point", "coordinates": coordinates[0]}
            else:
                summary_geometry = {"type": "LineString", "coordinates": coordinates}
            transition_costs = [
                float(row[f"transition_cost_{match_suffix}"])
                for row in ordered_rows
                if row.get(f"transition_cost_{match_suffix}") is not None
            ]
            distances = [
                float(row[f"distance_{match_suffix}"])
                for row in ordered_rows
                if row.get(f"distance_{match_suffix}") is not None
            ]
            sequence_span = int(ordered_rows[-1][sequence_column]) - int(ordered_rows[0][sequence_column]) + 1
            rows.append(
                {
                    track_id_column: track_id,
                    f"segment_index_{match_suffix}": segment_index,
                    f"observation_ids_{match_suffix}": observation_ids,
                    f"edge_ids_{match_suffix}": path_edge_ids,
                    f"observation_count_{match_suffix}": len(ordered_rows),
                    f"edge_count_{match_suffix}": len(path_edge_ids),
                    f"start_sequence_{match_suffix}": ordered_rows[0][sequence_column],
                    f"end_sequence_{match_suffix}": ordered_rows[-1][sequence_column],
                    f"sequence_span_{match_suffix}": sequence_span,
                    f"continuity_start_{match_suffix}": ordered_rows[0].get(f"continuity_state_{match_suffix}"),
                    f"continuity_end_{match_suffix}": ordered_rows[-1].get(f"continuity_state_{match_suffix}"),
                    f"gap_before_{match_suffix}": ordered_rows[0].get(f"continuity_state_{match_suffix}") == "resume",
                    f"mean_distance_{match_suffix}": (sum(distances) / len(distances)) if distances else None,
                    f"max_distance_{match_suffix}": max(distances) if distances else None,
                    f"transition_count_{match_suffix}": len(transition_costs),
                    f"mean_transition_cost_{match_suffix}": (sum(transition_costs) / len(transition_costs)) if transition_costs else 0.0,
                    f"total_transition_cost_{match_suffix}": sum(transition_costs),
                    f"observation_density_{match_suffix}": (len(ordered_rows) / sequence_span) if sequence_span > 0 else None,
                    self.geometry_column: summary_geometry,
                }
            )

        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    def score_trajectory_segments(
        self,
        track_id_column: str = "track_id",
        match_suffix: str = "match",
        score_suffix: str = "trajectory",
        distance_threshold: float = 0.05,
        transition_cost_threshold: float = 1.0,
        density_threshold: float = 0.75,
    ) -> "GeoPromptFrame":
        self._require_column(track_id_column)
        self._require_column(f"segment_index_{match_suffix}")
        self._require_column(f"observation_count_{match_suffix}")
        self._require_column(f"edge_count_{match_suffix}")
        self._require_column(f"mean_distance_{match_suffix}")
        self._require_column(f"max_distance_{match_suffix}")
        self._require_column(f"mean_transition_cost_{match_suffix}")
        self._require_column(f"observation_density_{match_suffix}")
        if distance_threshold <= 0.0:
            raise ValueError("distance_threshold must be greater than zero")
        if transition_cost_threshold <= 0.0:
            raise ValueError("transition_cost_threshold must be greater than zero")
        if not 0.0 < density_threshold <= 1.0:
            raise ValueError("density_threshold must be between zero and one")

        rows: list[Record] = []
        for row in self._rows:
            mean_distance = float(row[f"mean_distance_{match_suffix}"] or 0.0)
            max_distance = float(row[f"max_distance_{match_suffix}"] or 0.0)
            mean_transition_cost = float(row[f"mean_transition_cost_{match_suffix}"] or 0.0)
            observation_density = float(row[f"observation_density_{match_suffix}"] or 0.0)
            observation_count = int(row[f"observation_count_{match_suffix}"])
            edge_count = int(row[f"edge_count_{match_suffix}"])
            anomaly_flags: list[str] = []
            if bool(row.get(f"gap_before_{match_suffix}")):
                anomaly_flags.append("resumed_after_gap")
            if observation_count <= 1:
                anomaly_flags.append("single_observation_segment")
            if mean_distance > distance_threshold:
                anomaly_flags.append("high_mean_offset_distance")
            if max_distance > (distance_threshold * 1.5):
                anomaly_flags.append("high_max_offset_distance")
            if mean_transition_cost > transition_cost_threshold:
                anomaly_flags.append("high_transition_cost")
            if observation_density < density_threshold:
                anomaly_flags.append("sparse_observation_density")
            if edge_count > max(1, observation_count):
                anomaly_flags.append("excess_edge_changes")

            distance_penalty = min(1.0, mean_distance / distance_threshold)
            transition_penalty = min(1.0, mean_transition_cost / transition_cost_threshold)
            density_penalty = max(0.0, 1.0 - observation_density)
            gap_penalty = 0.2 if bool(row.get(f"gap_before_{match_suffix}")) else 0.0
            single_penalty = 0.2 if observation_count <= 1 else 0.0
            confidence_score = max(
                0.0,
                min(
                    1.0,
                    1.0 - ((0.35 * distance_penalty) + (0.35 * transition_penalty) + (0.1 * density_penalty) + gap_penalty + single_penalty),
                ),
            )
            anomaly_level = _trajectory_anomaly_level(confidence_score, len(anomaly_flags))
            resolved = dict(row)
            resolved[f"confidence_score_{score_suffix}"] = confidence_score
            resolved[f"anomaly_flags_{score_suffix}"] = anomaly_flags
            resolved[f"anomaly_count_{score_suffix}"] = len(anomaly_flags)
            resolved[f"anomaly_level_{score_suffix}"] = anomaly_level
            resolved[f"review_segment_{score_suffix}"] = anomaly_level in {"moderate", "high"}
            rows.append(resolved)

        rows.sort(
            key=lambda row: (
                int(row[f"review_segment_{score_suffix}"]),
                int(row[f"anomaly_count_{score_suffix}"]),
                -float(row[f"confidence_score_{score_suffix}"]),
                str(row[track_id_column]),
                int(row[f"segment_index_{match_suffix}"]),
            ),
            reverse=True,
        )
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    def change_detection(
        self,
        other: "GeoPromptFrame",
        id_column: str = "site_id",
        other_id_column: str | None = None,
        attribute_columns: Sequence[str] | None = None,
        max_distance: float | None = None,
        min_similarity: float = 0.35,
        geometry_tolerance: float = 1e-9,
        include_diagnostics: bool = False,
        change_suffix: str = "change",
    ) -> "GeoPromptFrame":
        resolved_other_id_column = other_id_column or id_column
        self._require_column(id_column)
        other._require_column(resolved_other_id_column)
        if max_distance is not None and max_distance < 0:
            raise ValueError("max_distance must be zero or greater")
        if not 0.0 <= min_similarity <= 1.0:
            raise ValueError("min_similarity must be between zero and one")
        if geometry_tolerance < 0:
            raise ValueError("geometry_tolerance must be zero or greater")
        if self.crs and other.crs and self.crs != other.crs:
            raise ValueError("frames must share the same CRS before change detection")

        left_rows = list(self._rows)
        right_rows = list(other._rows)
        right_index = other.spatial_index(mode="geometry") if right_rows else SpatialIndex([])
        left_centroids = self._centroids()
        right_centroids = other._centroids()
        shared_attribute_columns = list(attribute_columns) if attribute_columns is not None else sorted(
            (set(self.columns) & set(other.columns)) - {self.geometry_column, other.geometry_column, id_column, resolved_other_id_column}
        )

        pair_scores: list[dict[str, Any]] = []
        left_candidates: dict[int, list[dict[str, Any]]] = {index: [] for index in range(len(left_rows))}
        right_candidates: dict[int, list[dict[str, Any]]] = {index: [] for index in range(len(right_rows))}

        for left_index, left_row in enumerate(left_rows):
            left_geometry = left_row[self.geometry_column]
            left_centroid = left_centroids[left_index]
            if max_distance is None:
                candidate_indexes = list(range(len(right_rows)))
            else:
                candidate_indexes = right_index.query(_expand_bounds(geometry_bounds(left_geometry), max_distance))
            for right_index_value in candidate_indexes:
                right_row = right_rows[right_index_value]
                right_geometry = right_row[other.geometry_column]
                centroid_distance = coordinate_distance(left_centroid, right_centroids[right_index_value], method="euclidean")
                intersects = geometry_intersects(left_geometry, right_geometry)
                if max_distance is not None and centroid_distance > max_distance and not intersects:
                    continue
                attribute_match_count = sum(1 for column in shared_attribute_columns if left_row.get(column) == right_row.get(column))
                attribute_similarity = (attribute_match_count / len(shared_attribute_columns)) if shared_attribute_columns else 1.0
                left_size = _geometry_size_metric(left_geometry)
                right_size = _geometry_size_metric(right_geometry)
                size_ratio = _size_ratio(left_size, right_size)
                overlap_size = _geometry_overlap_size(left_geometry, right_geometry)
                left_area_share = _coverage_share(overlap_size, left_size, intersects)
                right_area_share = _coverage_share(overlap_size, right_size, intersects)
                area_share_score = (left_area_share + right_area_share) / 2.0
                distance_score = 1.0 if centroid_distance <= geometry_tolerance else 1.0 / (1.0 + centroid_distance)
                id_score = 1.0 if str(left_row[id_column]) == str(right_row[resolved_other_id_column]) else 0.0
                type_factor = 1.0 if geometry_type(left_geometry) == geometry_type(right_geometry) else 0.5
                similarity_score = type_factor * (
                    (0.25 * area_share_score)
                    + (0.15 * (1.0 if intersects else 0.0))
                    + (0.2 * distance_score)
                    + (0.15 * size_ratio)
                    + (0.15 * attribute_similarity)
                    + (0.15 * id_score)
                )
                if similarity_score < min_similarity:
                    continue
                pair_record = {
                    "left_index": left_index,
                    "right_index": right_index_value,
                    "similarity_score": similarity_score,
                    "centroid_distance": centroid_distance,
                    "attribute_match_count": attribute_match_count,
                    "attribute_similarity": attribute_similarity,
                    "intersects": intersects,
                    "size_ratio": size_ratio,
                    "overlap_size": overlap_size,
                    "left_area_share": left_area_share,
                    "right_area_share": right_area_share,
                    "area_share_score": area_share_score,
                }
                pair_scores.append(pair_record)
                left_candidates[left_index].append(pair_record)
                right_candidates[right_index_value].append(pair_record)

        for candidate_bucket in left_candidates.values():
            candidate_bucket.sort(key=lambda item: (-float(item["similarity_score"]), float(item["centroid_distance"]), str(right_rows[item["right_index"]][resolved_other_id_column])))
        for candidate_bucket in right_candidates.values():
            candidate_bucket.sort(key=lambda item: (-float(item["similarity_score"]), float(item["centroid_distance"]), str(left_rows[item["left_index"]][id_column])))

        left_matches = {
            left_index: _primary_change_matches(candidate_bucket)
            for left_index, candidate_bucket in left_candidates.items()
        }
        right_matches = {
            right_index_value: _primary_change_matches(candidate_bucket, key_name="left_index")
            for right_index_value, candidate_bucket in right_candidates.items()
        }

        rows: list[Record] = []
        matched_right_indexes: set[int] = set()
        for left_index, left_row in enumerate(left_rows):
            matched_pairs = left_matches[left_index]
            if not matched_pairs:
                resolved = dict(left_row)
                resolved[f"left_ids_{change_suffix}"] = [str(left_row[id_column])]
                resolved[f"right_ids_{change_suffix}"] = []
                resolved[f"change_class_{change_suffix}"] = "removed"
                resolved[f"event_side_{change_suffix}"] = "left"
                resolved[f"similarity_score_{change_suffix}"] = None
                resolved[f"centroid_distance_{change_suffix}"] = None
                resolved[f"attribute_change_count_{change_suffix}"] = None
                resolved[f"attribute_changes_{change_suffix}"] = None
                resolved[f"area_share_score_{change_suffix}"] = None
                resolved[f"match_area_shares_{change_suffix}"] = []
                if include_diagnostics:
                    resolved[f"candidate_count_{change_suffix}"] = len(left_candidates[left_index])
                rows.append(resolved)
                continue

            matched_right_indexes.update(pair["right_index"] for pair in matched_pairs)
            matched_right_ids = [str(right_rows[pair["right_index"]][resolved_other_id_column]) for pair in matched_pairs]
            best_pair = matched_pairs[0]
            matched_right_rows = [right_rows[pair["right_index"]] for pair in matched_pairs]
            attribute_changes = _attribute_change_summary([left_row], matched_right_rows, shared_attribute_columns)
            area_share_details = [
                {
                    "left_id": str(left_row[id_column]),
                    "right_id": str(right_rows[pair["right_index"]][resolved_other_id_column]),
                    "left_share": pair["left_area_share"],
                    "right_share": pair["right_area_share"],
                    "similarity_score": pair["similarity_score"],
                }
                for pair in matched_pairs
            ]
            if len(matched_pairs) > 1:
                change_class: ChangeClass = "split"
                attribute_change_count = len(attribute_changes)
                geometry_changed = None
            else:
                right_row = right_rows[best_pair["right_index"]]
                attribute_change_count = len(attribute_changes)
                geometry_changed = left_row[self.geometry_column] != right_row[other.geometry_column]
                if not geometry_changed and attribute_change_count == 0:
                    change_class = "unchanged"
                elif attribute_change_count == 0 and best_pair["centroid_distance"] > geometry_tolerance:
                    change_class = "moved"
                else:
                    change_class = "modified"

            resolved = dict(left_row)
            resolved[f"left_ids_{change_suffix}"] = [str(left_row[id_column])]
            resolved[f"right_ids_{change_suffix}"] = matched_right_ids
            resolved[f"change_class_{change_suffix}"] = change_class
            resolved[f"event_side_{change_suffix}"] = "left"
            resolved[f"similarity_score_{change_suffix}"] = best_pair["similarity_score"]
            resolved[f"centroid_distance_{change_suffix}"] = best_pair["centroid_distance"]
            resolved[f"attribute_change_count_{change_suffix}"] = attribute_change_count
            resolved[f"attribute_changes_{change_suffix}"] = attribute_changes
            resolved[f"geometry_changed_{change_suffix}"] = geometry_changed
            resolved[f"area_share_score_{change_suffix}"] = sum(pair["area_share_score"] for pair in matched_pairs) / len(matched_pairs)
            resolved[f"match_area_shares_{change_suffix}"] = area_share_details
            if include_diagnostics:
                resolved[f"candidate_count_{change_suffix}"] = len(left_candidates[left_index])
                resolved[f"attribute_similarity_{change_suffix}"] = best_pair["attribute_similarity"]
                resolved[f"size_ratio_{change_suffix}"] = best_pair["size_ratio"]
            rows.append(resolved)

        for right_index_value, right_row in enumerate(right_rows):
            matched_left_pairs = right_matches[right_index_value]
            if not matched_left_pairs:
                resolved = {key: value for key, value in right_row.items()}
                resolved[self.geometry_column] = right_row[other.geometry_column]
                resolved[f"left_ids_{change_suffix}"] = []
                resolved[f"right_ids_{change_suffix}"] = [str(right_row[resolved_other_id_column])]
                resolved[f"change_class_{change_suffix}"] = "added"
                resolved[f"event_side_{change_suffix}"] = "right"
                resolved[f"similarity_score_{change_suffix}"] = None
                resolved[f"centroid_distance_{change_suffix}"] = None
                resolved[f"attribute_change_count_{change_suffix}"] = None
                resolved[f"attribute_changes_{change_suffix}"] = None
                resolved[f"area_share_score_{change_suffix}"] = None
                resolved[f"match_area_shares_{change_suffix}"] = []
                if include_diagnostics:
                    resolved[f"candidate_count_{change_suffix}"] = len(right_candidates[right_index_value])
                rows.append(resolved)
                continue
            if len(matched_left_pairs) <= 1:
                continue
            resolved = {key: value for key, value in right_row.items()}
            resolved[self.geometry_column] = right_row[other.geometry_column]
            matched_left_rows = [left_rows[pair["left_index"]] for pair in matched_left_pairs]
            attribute_changes = _attribute_change_summary(matched_left_rows, [right_row], shared_attribute_columns)
            resolved[f"left_ids_{change_suffix}"] = [str(left_rows[pair["left_index"]][id_column]) for pair in matched_left_pairs]
            resolved[f"right_ids_{change_suffix}"] = [str(right_row[resolved_other_id_column])]
            resolved[f"change_class_{change_suffix}"] = "merge"
            resolved[f"event_side_{change_suffix}"] = "right"
            resolved[f"similarity_score_{change_suffix}"] = matched_left_pairs[0]["similarity_score"]
            resolved[f"centroid_distance_{change_suffix}"] = matched_left_pairs[0]["centroid_distance"]
            resolved[f"attribute_change_count_{change_suffix}"] = len(attribute_changes)
            resolved[f"attribute_changes_{change_suffix}"] = attribute_changes
            resolved[f"area_share_score_{change_suffix}"] = sum(pair["area_share_score"] for pair in matched_left_pairs) / len(matched_left_pairs)
            resolved[f"match_area_shares_{change_suffix}"] = [
                {
                    "left_id": str(left_rows[pair["left_index"]][id_column]),
                    "right_id": str(right_row[resolved_other_id_column]),
                    "left_share": pair["left_area_share"],
                    "right_share": pair["right_area_share"],
                    "similarity_score": pair["similarity_score"],
                }
                for pair in matched_left_pairs
            ]
            if include_diagnostics:
                resolved[f"candidate_count_{change_suffix}"] = len(right_candidates[right_index_value])
            rows.append(resolved)

        _annotate_change_event_groups(rows, change_suffix)

        rows.sort(
            key=lambda row: (
                str(row.get(f"change_class_{change_suffix}")),
                tuple(row.get(f"left_ids_{change_suffix}", [])),
                tuple(row.get(f"right_ids_{change_suffix}", [])),
            )
        )
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs or other.crs)

    def extract_change_events(
        self,
        change_suffix: str = "change",
    ) -> "GeoPromptFrame":
        self._require_column(f"event_group_id_{change_suffix}")
        self._require_column(f"event_summary_{change_suffix}")
        self._require_column(f"change_class_{change_suffix}")
        self._require_column(f"event_side_{change_suffix}")

        grouped_rows: dict[str, list[Record]] = {}
        for row in self._rows:
            grouped_rows.setdefault(str(row[f"event_group_id_{change_suffix}"]), []).append(row)

        rows: list[Record] = []
        for event_group_id, event_rows in sorted(grouped_rows.items(), key=lambda item: item[0]):
            ordered_rows = sorted(
                event_rows,
                key=lambda row: (
                    tuple(row.get(f"left_ids_{change_suffix}", [])),
                    tuple(row.get(f"right_ids_{change_suffix}", [])),
                    str(row.get(f"event_side_{change_suffix}")),
                ),
            )
            summary = dict(ordered_rows[0][f"event_summary_{change_suffix}"])
            rows.append(
                {
                    f"event_group_id_{change_suffix}": event_group_id,
                    f"change_class_{change_suffix}": ordered_rows[0].get(f"change_class_{change_suffix}"),
                    f"event_side_{change_suffix}": ordered_rows[0].get(f"event_side_{change_suffix}"),
                    f"left_ids_{change_suffix}": list(summary.get("left_ids", [])),
                    f"right_ids_{change_suffix}": list(summary.get("right_ids", [])),
                    f"event_row_count_{change_suffix}": ordered_rows[0].get(f"event_row_count_{change_suffix}", len(ordered_rows)),
                    f"event_feature_count_{change_suffix}": ordered_rows[0].get(f"event_feature_count_{change_suffix}"),
                    f"member_geometry_types_{change_suffix}": _distinct_values(geometry_type(row[self.geometry_column]) for row in ordered_rows),
                    f"event_summary_{change_suffix}": summary,
                    self.geometry_column: _mean_centroid_geometry(ordered_rows, self.geometry_column),
                }
            )

        rows.sort(
            key=lambda row: (
                str(row[f"change_class_{change_suffix}"]),
                tuple(row.get(f"left_ids_{change_suffix}", [])),
                tuple(row.get(f"right_ids_{change_suffix}", [])),
            )
        )
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    def compare_change_events(
        self,
        other: "GeoPromptFrame",
        change_suffix: str = "change",
        diff_suffix: str = "eventdiff",
        match_mode: str = "exact",
        min_similarity: float = 0.6,
    ) -> "GeoPromptFrame":
        required_columns = (
            f"change_class_{change_suffix}",
            f"left_ids_{change_suffix}",
            f"right_ids_{change_suffix}",
            f"event_summary_{change_suffix}",
        )
        for column in required_columns:
            self._require_column(column)
            other._require_column(column)
        if self.crs and other.crs and self.crs != other.crs:
            raise ValueError("frames must share the same CRS before change event comparison")

        if match_mode not in {"exact", "equivalent"}:
            raise ValueError("match_mode must be 'exact' or 'equivalent'")
        if not 0.0 <= min_similarity <= 1.0:
            raise ValueError("min_similarity must be between zero and one")

        matched_pairs: list[tuple[tuple[str, tuple[str, ...], tuple[str, ...]], Record | None, Record | None, float | None]]
        if match_mode == "exact":
            left_events = {
                _change_event_signature(row, change_suffix): row
                for row in self._rows
            }
            right_events = {
                _change_event_signature(row, change_suffix): row
                for row in other._rows
            }
            matched_pairs = [
                (
                    signature,
                    left_events.get(signature),
                    right_events.get(signature),
                    1.0 if signature in left_events and signature in right_events else None,
                )
                for signature in sorted(set(left_events) | set(right_events))
            ]
        else:
            matched_pairs = _match_equivalent_change_events(
                self._rows,
                other._rows,
                change_suffix=change_suffix,
                geometry_column=self.geometry_column,
                min_similarity=min_similarity,
            )

        rows: list[Record] = []
        for signature, baseline_row, current_row, match_similarity in matched_pairs:
            if baseline_row is None:
                event_status = "emerged"
            elif current_row is None:
                event_status = "resolved"
            else:
                event_status = "persisted"

            baseline_summary = dict(baseline_row[f"event_summary_{change_suffix}"]) if baseline_row is not None else {}
            current_summary = dict(current_row[f"event_summary_{change_suffix}"]) if current_row is not None else {}
            baseline_attribute_columns = list(baseline_summary.get("attribute_columns", []))
            current_attribute_columns = list(current_summary.get("attribute_columns", []))
            geometry = current_row[self.geometry_column] if current_row is not None else baseline_row[self.geometry_column]
            resolved: Record = {
                f"event_status_{diff_suffix}": event_status,
                f"change_class_{change_suffix}": signature[0],
                f"left_ids_{change_suffix}": list(signature[1]),
                f"right_ids_{change_suffix}": list(signature[2]),
                f"event_signature_{diff_suffix}": _format_change_event_signature(signature),
                f"match_mode_{diff_suffix}": match_mode,
                f"event_similarity_{diff_suffix}": match_similarity,
                f"baseline_event_group_id_{diff_suffix}": baseline_row.get(f"event_group_id_{change_suffix}") if baseline_row is not None else None,
                f"current_event_group_id_{diff_suffix}": current_row.get(f"event_group_id_{change_suffix}") if current_row is not None else None,
                f"baseline_row_count_{diff_suffix}": baseline_summary.get("row_count"),
                f"current_row_count_{diff_suffix}": current_summary.get("row_count"),
                f"row_count_delta_{diff_suffix}": _numeric_delta(current_summary.get("row_count"), baseline_summary.get("row_count")),
                f"baseline_feature_count_{diff_suffix}": baseline_summary.get("feature_count"),
                f"current_feature_count_{diff_suffix}": current_summary.get("feature_count"),
                f"feature_count_delta_{diff_suffix}": _numeric_delta(current_summary.get("feature_count"), baseline_summary.get("feature_count")),
                f"baseline_mean_similarity_score_{diff_suffix}": baseline_summary.get("mean_similarity_score"),
                f"current_mean_similarity_score_{diff_suffix}": current_summary.get("mean_similarity_score"),
                f"mean_similarity_score_delta_{diff_suffix}": _numeric_delta(current_summary.get("mean_similarity_score"), baseline_summary.get("mean_similarity_score")),
                f"baseline_attribute_columns_{diff_suffix}": baseline_attribute_columns,
                f"current_attribute_columns_{diff_suffix}": current_attribute_columns,
                f"added_attribute_columns_{diff_suffix}": [column for column in current_attribute_columns if column not in baseline_attribute_columns],
                f"removed_attribute_columns_{diff_suffix}": [column for column in baseline_attribute_columns if column not in current_attribute_columns],
                f"baseline_event_summary_{change_suffix}": baseline_summary or None,
                f"current_event_summary_{change_suffix}": current_summary or None,
                self.geometry_column: geometry,
            }
            rows.append(resolved)

        rows.sort(
            key=lambda row: (
                _change_event_status_rank(str(row[f"event_status_{diff_suffix}"])),
                str(row[f"change_class_{change_suffix}"]),
                tuple(row[f"left_ids_{change_suffix}"]),
                tuple(row[f"right_ids_{change_suffix}"]),
            )
        )
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs or other.crs)

    def corridor_reach(
        self,
        corridors: "GeoPromptFrame",
        max_distance: float,
        corridor_id_column: str = "site_id",
        aggregations: dict[str, AggregationName] | None = None,
        how: SpatialJoinMode = "left",
        distance_method: str = "euclidean",
        distance_mode: CorridorDistanceMode = "direct",
        score_mode: CorridorScoreMode = "distance",
        weight_column: str | None = None,
        preferred_bearing: float | None = None,
        path_anchor: CorridorPathAnchor = "start",
        scale: float = 1.0,
        power: float = 2.0,
        reach_suffix: str = "reach",
    ) -> "GeoPromptFrame":
        if max_distance < 0:
            raise ValueError("max_distance must be zero or greater")
        if how not in {"inner", "left"}:
            raise ValueError("how must be 'inner' or 'left'")
        if distance_method not in {"euclidean", "haversine"}:
            raise ValueError("distance_method must be 'euclidean' or 'haversine'")
        if distance_mode not in {"direct", "network"}:
            raise ValueError("distance_mode must be 'direct' or 'network'")
        if score_mode not in {"distance", "strength", "alignment", "combined"}:
            raise ValueError("score_mode must be 'distance', 'strength', 'alignment', or 'combined'")
        if path_anchor not in {"start", "end", "nearest"}:
            raise ValueError("path_anchor must be 'start', 'end', or 'nearest'")
        if scale <= 0:
            raise ValueError("scale must be greater than zero")
        if power <= 0:
            raise ValueError("power must be greater than zero")
        if self.crs and corridors.crs and self.crs != corridors.crs:
            raise ValueError("frames must share the same CRS before corridor reach analysis")

        corridors._require_column(corridor_id_column)
        if weight_column is not None:
            corridors._require_column(weight_column)
        corridor_rows = list(corridors._rows)

        rows: list[Record] = []
        for left_row in self._rows:
            left_centroid = geometry_centroid(left_row[self.geometry_column])
            matched_corridors: list[Record] = []
            matched_distances: list[float] = []
            corridor_scores: list[Record] = []
            for corridor_row in corridor_rows:
                corridor_geometry = corridor_row[corridors.geometry_column]
                corridor_vertices = list(corridor_geometry.get("coordinates", []))  # type: ignore[union-attr]
                if not corridor_vertices:
                    continue
                min_dist, along_distance = _point_to_polyline_distance_details(left_centroid, corridor_vertices, method=distance_method)
                corridor_length_value = _polyline_length(corridor_vertices, method=distance_method)
                anchor_distance = _resolve_anchor_distance(along_distance, corridor_length_value, path_anchor)
                if distance_mode == "network":
                    min_dist = min_dist + anchor_distance
                if min_dist <= max_distance:
                    matched_corridors.append(corridor_row)
                    matched_distances.append(min_dist)

                    alignment_score = None
                    if preferred_bearing is not None and len(corridor_vertices) >= 2:
                        alignment_score = (directional_alignment(corridor_vertices[0], corridor_vertices[-1], preferred_bearing) + 1.0) / 2.0
                    weight_value = float(corridor_row[weight_column]) if weight_column is not None else 1.0
                    distance_score = prompt_decay(distance_value=min_dist, scale=scale, power=power)
                    if score_mode == "distance":
                        corridor_score = weight_value * distance_score
                    elif score_mode == "strength":
                        corridor_score = corridor_strength(weight=weight_value, corridor_length=corridor_length_value, distance_value=min_dist, scale=scale, power=power)
                    elif score_mode == "alignment":
                        corridor_score = weight_value * distance_score * (alignment_score if alignment_score is not None else 1.0)
                    else:
                        corridor_score = corridor_strength(weight=weight_value, corridor_length=corridor_length_value, distance_value=min_dist, scale=scale, power=power) * (alignment_score if alignment_score is not None else 1.0)

                    corridor_scores.append(
                        {
                            "corridor_id": str(corridor_row[corridor_id_column]),
                            "distance": min_dist,
                            "along_distance": along_distance,
                            "anchor_distance": anchor_distance,
                            "corridor_length": corridor_length_value,
                            "alignment_score": alignment_score,
                            "score": corridor_score,
                        }
                    )

            if not matched_corridors and how == "inner":
                continue

            corridor_scores.sort(key=lambda item: (-float(item["score"]), float(item["distance"]), str(item["corridor_id"])))

            resolved_row = dict(left_row)
            resolved_row[f"{corridor_id_column}s_{reach_suffix}"] = [
                str(row[corridor_id_column]) for row in matched_corridors
            ]
            resolved_row[f"count_{reach_suffix}"] = len(matched_corridors)
            resolved_row[f"distance_min_{reach_suffix}"] = min(matched_distances) if matched_distances else None
            resolved_row[f"distance_max_{reach_suffix}"] = max(matched_distances) if matched_distances else None
            resolved_row[f"distance_mean_{reach_suffix}"] = (
                sum(matched_distances) / len(matched_distances) if matched_distances else None
            )
            resolved_row[f"distance_limit_{reach_suffix}"] = max_distance
            resolved_row[f"distance_method_{reach_suffix}"] = distance_method
            resolved_row[f"distance_mode_{reach_suffix}"] = distance_mode
            resolved_row[f"path_anchor_{reach_suffix}"] = path_anchor
            resolved_row[f"score_mode_{reach_suffix}"] = score_mode
            resolved_row[f"corridor_scores_{reach_suffix}"] = corridor_scores
            resolved_row[f"best_corridor_{reach_suffix}"] = corridor_scores[0]["corridor_id"] if corridor_scores else None
            resolved_row[f"best_score_{reach_suffix}"] = corridor_scores[0]["score"] if corridor_scores else None

            total_corridor_length = sum(
                _polyline_length(list(row[corridors.geometry_column].get("coordinates", [])), method=distance_method) if row[corridors.geometry_column].get("type") == "LineString" else geometry_length(row[corridors.geometry_column])
                for row in matched_corridors
            )
            resolved_row[f"corridor_length_total_{reach_suffix}"] = total_corridor_length

            resolved_row.update(
                self._aggregate_rows(matched_corridors, aggregations=aggregations, suffix=reach_suffix)
            )
            rows.append(resolved_row)

        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs or corridors.crs)

    def zone_fit_score(
        self,
        zones: "GeoPromptFrame",
        zone_id_column: str = "region_id",
        weight_column: str | None = None,
        max_distance: float | None = None,
        distance_method: str = "euclidean",
        score_weights: dict[str, float] | None = None,
        preferred_bearing: float | None = None,
        group_by: str | None = None,
        group_aggregation: ZoneGroupAggregation = "max",
        top_n: int | None = None,
        score_callback: Any | None = None,
        score_suffix: str = "fit",
    ) -> "GeoPromptFrame":
        if max_distance is not None and max_distance < 0:
            raise ValueError("max_distance must be zero or greater")
        if self.crs and zones.crs and self.crs != zones.crs:
            raise ValueError("frames must share the same CRS before zone fit scoring")
        if group_aggregation not in {"max", "mean", "sum"}:
            raise ValueError("group_aggregation must be 'max', 'mean', or 'sum'")
        if top_n is not None and top_n <= 0:
            raise ValueError("top_n must be greater than zero")

        zones._require_column(zone_id_column)
        if group_by is not None:
            zones._require_column(group_by)
        component_weights = _resolve_zone_fit_weights(score_weights)
        zone_rows = list(zones._rows)
        zone_centroids = zones._centroids()
        zone_areas = [geometry_area(row[zones.geometry_column]) for row in zone_rows]

        rows: list[Record] = []
        for left_row in self._rows:
            left_centroid = geometry_centroid(left_row[self.geometry_column])
            left_area = geometry_area(left_row[self.geometry_column])

            best_score = -1.0
            best_zone_id: str | None = None
            zone_scores: list[Record] = []

            for zone_row, zone_centroid, zone_area in zip(zone_rows, zone_centroids, zone_areas, strict=True):
                dist = coordinate_distance(left_centroid, zone_centroid, method=distance_method)
                if max_distance is not None and dist > max_distance:
                    continue

                containment = 1.0 if geometry_within(left_row[self.geometry_column], zone_row[zones.geometry_column]) else 0.0
                overlap = 1.0 if geometry_intersects(left_row[self.geometry_column], zone_row[zones.geometry_column]) else 0.0
                size_ratio = area_similarity(
                    origin_area=left_area,
                    destination_area=zone_area,
                    distance_value=dist,
                    scale=1.0,
                    power=1.0,
                )
                access_score = prompt_decay(distance_value=dist, scale=max_distance or 1.0, power=1.0)
                alignment_score = None
                if preferred_bearing is not None:
                    alignment_score = (directional_alignment(left_centroid, zone_centroid, preferred_bearing) + 1.0) / 2.0

                component_scores = {
                    "containment": containment,
                    "overlap": overlap,
                    "size": size_ratio,
                    "access": access_score,
                    "alignment": alignment_score if alignment_score is not None else 0.0,
                }

                weight = float(left_row.get(weight_column, 1.0)) if weight_column else 1.0
                weighted_total = sum(component_scores[name] * component_weights[name] for name in component_weights)
                total_weight = sum(component_weights.values())
                score = weight * (weighted_total / total_weight)
                if score_callback is not None:
                    score = float(score_callback(left_row, zone_row, dict(component_scores), score))

                zone_scores.append({
                    "zone_id": str(zone_row[zone_id_column]),
                    "group": str(zone_row[group_by]) if group_by is not None else None,
                    "score": score,
                    "distance": dist,
                    "containment": containment,
                    "overlap": overlap,
                    "size_ratio": size_ratio,
                    "access_score": access_score,
                    "alignment_score": alignment_score,
                })
                if score > best_score:
                    best_score = score
                    best_zone_id = str(zone_row[zone_id_column])

            zone_scores.sort(key=lambda item: (-float(item["score"]), float(item["distance"]), str(item["zone_id"])))
            if top_n is not None:
                zone_scores = zone_scores[:top_n]

            resolved_row = dict(left_row)
            resolved_row[f"best_zone_{score_suffix}"] = best_zone_id
            resolved_row[f"best_score_{score_suffix}"] = best_score if best_zone_id is not None else None
            resolved_row[f"zone_count_{score_suffix}"] = len(zone_scores)
            resolved_row[f"score_weights_{score_suffix}"] = dict(component_weights)
            resolved_row[f"zone_scores_{score_suffix}"] = zone_scores
            if group_by is not None:
                grouped_scores: dict[str, dict[str, Any]] = {}
                for zone_score in zone_scores:
                    group_value = str(zone_score["group"])
                    bucket = grouped_scores.setdefault(group_value, {"group": group_value, "zone_ids": [], "scores": []})
                    bucket["zone_ids"].append(zone_score["zone_id"])
                    bucket["scores"].append(zone_score["score"])
                group_rankings = []
                for group_score in grouped_scores.values():
                    if group_aggregation == "max":
                        score_value = max(group_score["scores"])
                    elif group_aggregation == "mean":
                        score_value = sum(group_score["scores"]) / len(group_score["scores"])
                    else:
                        score_value = sum(group_score["scores"])
                    group_rankings.append(
                        {
                            "group": group_score["group"],
                            "score": score_value,
                            "zone_ids": group_score["zone_ids"],
                            "zone_count": len(group_score["zone_ids"]),
                        }
                    )
                group_rankings.sort(key=lambda item: (-float(item["score"]), str(item["group"])))
                resolved_row[f"group_scores_{score_suffix}"] = group_rankings
                resolved_row[f"best_group_{score_suffix}"] = group_rankings[0]["group"] if group_rankings else None
            rows.append(resolved_row)

        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs or zones.crs)

    def centroid_cluster(
        self,
        k: int,
        id_column: str = "site_id",
        distance_method: str = "euclidean",
        max_iterations: int = 50,
    ) -> "GeoPromptFrame":
        if k <= 0:
            raise ValueError("k must be greater than zero")
        if k > len(self._rows):
            raise ValueError("k must not exceed frame length")
        if max_iterations <= 0:
            raise ValueError("max_iterations must be greater than zero")

        centroids_list = self._centroids()
        sorted_indices = sorted(range(len(self._rows)), key=lambda index: _cluster_sort_key(self._rows[index], index, id_column))
        seed_positions = [int(step * len(sorted_indices) / k) for step in range(k)]
        seed_indices = [sorted_indices[min(position, len(sorted_indices) - 1)] for position in seed_positions]
        cluster_centers = [centroids_list[i] for i in seed_indices]

        assignments = [0] * len(centroids_list)

        for _ in range(max_iterations):
            changed = False
            for point_index, point in enumerate(centroids_list):
                best_cluster = assignments[point_index]
                best_dist = float("inf")
                for cluster_index, center in enumerate(cluster_centers):
                    dist = coordinate_distance(point, center, method=distance_method)
                    if dist < best_dist - 1e-12 or (abs(dist - best_dist) <= 1e-12 and cluster_index < best_cluster):
                        best_dist = dist
                        best_cluster = cluster_index
                if assignments[point_index] != best_cluster:
                    assignments[point_index] = best_cluster
                    changed = True

            if not changed:
                break

            new_centers: list[Coordinate] = []
            for cluster_index in range(k):
                members = [centroids_list[i] for i, a in enumerate(assignments) if a == cluster_index]
                if members:
                    cx = sum(p[0] for p in members) / len(members)
                    cy = sum(p[1] for p in members) / len(members)
                    new_centers.append((cx, cy))
                else:
                    new_centers.append(cluster_centers[cluster_index])
            cluster_centers = new_centers

        cluster_member_indices = {
            cluster_index: [index for index, assignment in enumerate(assignments) if assignment == cluster_index]
            for cluster_index in range(k)
        }
        point_distances = [
            coordinate_distance(centroid_point, cluster_centers[assignments[index]], method=distance_method)
            for index, centroid_point in enumerate(centroids_list)
        ]
        cluster_sse = {
            cluster_index: sum(point_distances[index] ** 2 for index in members)
            for cluster_index, members in cluster_member_indices.items()
        }
        cluster_mean_distance = {
            cluster_index: (sum(point_distances[index] for index in members) / len(members)) if members else 0.0
            for cluster_index, members in cluster_member_indices.items()
        }
        silhouette_scores = _cluster_silhouette_scores(centroids_list, assignments, distance_method=distance_method)
        overall_sse = sum(cluster_sse.values())
        overall_silhouette = sum(silhouette_scores) / len(silhouette_scores) if silhouette_scores else 0.0

        rows: list[Record] = []
        for index, (row, cluster_id, centroid_point) in enumerate(zip(self._rows, assignments, centroids_list, strict=True)):
            resolved = dict(row)
            resolved["cluster_id"] = cluster_id
            resolved["cluster_center"] = cluster_centers[cluster_id]
            resolved["cluster_distance"] = point_distances[index]
            resolved["cluster_size"] = len(cluster_member_indices[cluster_id])
            resolved["cluster_mean_distance"] = cluster_mean_distance[cluster_id]
            resolved["cluster_sse"] = cluster_sse[cluster_id]
            resolved["cluster_silhouette"] = silhouette_scores[index]
            resolved["cluster_sse_total"] = overall_sse
            resolved["cluster_silhouette_mean"] = overall_silhouette
            rows.append(resolved)

        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    def envelopes(self) -> "GeoPromptFrame":
        rows: list[Record] = []
        for row in self._rows:
            new_row = dict(row)
            new_row[self.geometry_column] = geometry_envelope(row[self.geometry_column])
            rows.append(new_row)
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    def convex_hulls(self) -> "GeoPromptFrame":
        rows: list[Record] = []
        for row in self._rows:
            new_row = dict(row)
            new_row[self.geometry_column] = geometry_convex_hull(row[self.geometry_column])
            rows.append(new_row)
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    def gravity_table(
        self,
        origin_weight: str,
        destination_weight: str,
        id_column: str = "site_id",
        friction: float = 2.0,
        distance_method: str = "euclidean",
    ) -> list[Record]:
        self._require_column(origin_weight)
        self._require_column(destination_weight)
        self._require_column(id_column)

        interactions: list[Record] = []
        for origin in self._rows:
            for destination in self._rows:
                if origin is destination:
                    continue
                distance_value = geometry_distance(
                    origin[self.geometry_column],
                    destination[self.geometry_column],
                    method=distance_method,
                )
                interactions.append({
                    "origin": origin[id_column],
                    "destination": destination[id_column],
                    "distance": distance_value,
                    "gravity": gravity_model(
                        origin_weight=float(origin[origin_weight]),
                        destination_weight=float(destination[destination_weight]),
                        distance_value=distance_value,
                        friction=friction,
                    ),
                    "distance_method": distance_method,
                })
        return interactions

    def accessibility_scores(
        self,
        targets: "GeoPromptFrame",
        weight_column: str,
        friction: float = 2.0,
        id_column: str = "site_id",
        distance_method: str = "euclidean",
    ) -> list[float]:
        targets._require_column(weight_column)
        target_centroids = targets._centroids()
        target_weights = [float(row[weight_column]) for row in targets._rows]
        origin_centroids = self._centroids()

        scores: list[float] = []
        for origin_centroid in origin_centroids:
            distances = [
                coordinate_distance(origin_centroid, tc, method=distance_method)
                for tc in target_centroids
            ]
            scores.append(accessibility_index(target_weights, distances, friction=friction))
        return scores

    def cluster_diagnostics(
        self,
        k_values: Sequence[int],
        id_column: str = "site_id",
        distance_method: str = "euclidean",
        max_iterations: int = 50,
    ) -> list[Record]:
        if not k_values:
            raise ValueError("k_values must contain at least one cluster count")

        unique_k_values = sorted(set(int(value) for value in k_values))
        diagnostics: list[Record] = []
        previous_sse: float | None = None
        for k_value in unique_k_values:
            clustered = self.centroid_cluster(
                k=k_value,
                id_column=id_column,
                distance_method=distance_method,
                max_iterations=max_iterations,
            )
            records = clustered.to_records()
            cluster_sizes = sorted({int(record["cluster_size"]) for record in records}, reverse=True)
            total_sse = float(records[0]["cluster_sse_total"]) if records else 0.0
            silhouette_mean = float(records[0]["cluster_silhouette_mean"]) if records else 0.0
            diagnostics.append(
                {
                    "k": k_value,
                    "cluster_count": len({int(record["cluster_id"]) for record in records}),
                    "cluster_sizes": cluster_sizes,
                    "sse_total": total_sse,
                    "sse_improvement": (previous_sse - total_sse) if previous_sse is not None else None,
                    "silhouette_mean": silhouette_mean,
                }
            )
            previous_sse = total_sse

        recommended_by_silhouette = max(diagnostics, key=lambda item: (float(item["silhouette_mean"]), -int(item["k"])))
        recommended_by_sse = min(diagnostics, key=lambda item: (float(item["sse_total"]), int(item["k"])))
        for item in diagnostics:
            item["recommended_silhouette"] = int(item["k"]) == int(recommended_by_silhouette["k"])
            item["recommended_sse"] = int(item["k"]) == int(recommended_by_sse["k"])
        return diagnostics

    def recommend_cluster_count(
        self,
        k_values: Sequence[int],
        metric: ClusterRecommendMetric = "silhouette",
        id_column: str = "site_id",
        distance_method: str = "euclidean",
        max_iterations: int = 50,
    ) -> Record:
        diagnostics = self.cluster_diagnostics(
            k_values=k_values,
            id_column=id_column,
            distance_method=distance_method,
            max_iterations=max_iterations,
        )
        if metric == "silhouette":
            return next(item for item in diagnostics if item["recommended_silhouette"])
        if metric == "sse":
            return next(item for item in diagnostics if item["recommended_sse"])
        raise ValueError("metric must be 'silhouette' or 'sse'")

    def summarize_clusters(
        self,
        cluster_column: str = "cluster_id",
        group_by: str | None = None,
        aggregations: dict[str, AggregationName] | None = None,
    ) -> "GeoPromptFrame":
        self._require_column(cluster_column)
        if group_by is not None:
            self._require_column(group_by)

        grouped_rows: dict[int, list[Record]] = {}
        for row in self._rows:
            grouped_rows.setdefault(int(row[cluster_column]), []).append(row)

        rows: list[Record] = []
        for cluster_id, cluster_rows in grouped_rows.items():
            centroid_x = sum(float(row["cluster_center"][0]) for row in cluster_rows if "cluster_center" in row) / len(cluster_rows)
            centroid_y = sum(float(row["cluster_center"][1]) for row in cluster_rows if "cluster_center" in row) / len(cluster_rows)
            summary_row: Record = {
                cluster_column: cluster_id,
                "cluster_member_count": len(cluster_rows),
                "cluster_site_ids": [str(row.get("site_id", row.get("region_id", ""))) for row in cluster_rows],
                "cluster_center_summary": (centroid_x, centroid_y),
                "cluster_sse_total": sum(float(row.get("cluster_sse", 0.0)) for row in cluster_rows),
                "cluster_mean_distance_summary": sum(float(row.get("cluster_distance", 0.0)) for row in cluster_rows) / len(cluster_rows),
                self.geometry_column: {"type": "Point", "coordinates": (centroid_x, centroid_y)},
            }
            if group_by is not None:
                group_counts: dict[str, int] = {}
                for row in cluster_rows:
                    group_counts[str(row[group_by])] = group_counts.get(str(row[group_by]), 0) + 1
                summary_row[f"{group_by}_counts"] = group_counts
                summary_row[f"dominant_{group_by}"] = max(group_counts.items(), key=lambda item: (int(item[1]), str(item[0])))[0] if group_counts else None
            summary_row.update(self._aggregate_rows(cluster_rows, aggregations=aggregations, suffix="cluster"))
            rows.append(summary_row)
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    def overlay_group_comparison(
        self,
        other: "GeoPromptFrame",
        group_by: str,
        right_id_column: str = "region_id",
        normalize_by: OverlayNormalizeMode = "both",
        comparison_suffix: str = "overlay_compare",
    ) -> "GeoPromptFrame":
        summary = self.overlay_summary(
            other,
            right_id_column=right_id_column,
            group_by=group_by,
            normalize_by=normalize_by,
            how="left",
            summary_suffix=comparison_suffix,
        )

        rows: list[Record] = []
        for row in summary.to_records():
            groups = list(row.get(f"groups_{comparison_suffix}", []))
            groups.sort(key=lambda item: (-float(item["area_overlap"]), -float(item["length_overlap"]), str(item["group"])))
            top_group = groups[0] if len(groups) >= 1 else None
            second_group = groups[1] if len(groups) >= 2 else None
            resolved = dict(row)
            resolved[f"top_group_{comparison_suffix}"] = top_group["group"] if top_group else None
            resolved[f"runner_up_group_{comparison_suffix}"] = second_group["group"] if second_group else None
            resolved[f"area_gap_{comparison_suffix}"] = (top_group["area_overlap"] - second_group["area_overlap"]) if top_group and second_group else None
            resolved[f"length_gap_{comparison_suffix}"] = (top_group["length_overlap"] - second_group["length_overlap"]) if top_group and second_group else None
            resolved[f"comparison_strength_{comparison_suffix}"] = (
                (top_group["area_overlap"] + top_group["length_overlap"]) - (second_group["area_overlap"] + second_group["length_overlap"])
            ) if top_group and second_group else None
            rows.append(resolved)
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs or other.crs)

    def corridor_diagnostics(
        self,
        corridors: "GeoPromptFrame",
        max_distance: float,
        corridor_id_column: str = "site_id",
        distance_method: str = "euclidean",
        distance_mode: CorridorDistanceMode = "network",
        score_mode: CorridorScoreMode = "combined",
        path_anchor: CorridorPathAnchor = "start",
        weight_column: str | None = None,
        preferred_bearing: float | None = None,
        scale: float = 1.0,
        power: float = 2.0,
    ) -> "GeoPromptFrame":
        reach = self.corridor_reach(
            corridors,
            max_distance=max_distance,
            corridor_id_column=corridor_id_column,
            distance_method=distance_method,
            distance_mode=distance_mode,
            score_mode=score_mode,
            weight_column=weight_column,
            preferred_bearing=preferred_bearing,
            path_anchor=path_anchor,
            scale=scale,
            power=power,
            how="left",
            reach_suffix="diagnostics",
        )
        corridor_scores_by_id: dict[str, list[Record]] = {}
        for row in reach.to_records():
            for item in row.get("corridor_scores_diagnostics", []):
                corridor_scores_by_id.setdefault(str(item["corridor_id"]), []).append(item)

        rows: list[Record] = []
        for corridor_row in corridors.to_records():
            corridor_id = str(corridor_row[corridor_id_column])
            items = corridor_scores_by_id.get(corridor_id, [])
            diagnostic_row = dict(corridor_row)
            diagnostic_row["served_feature_count"] = len(items)
            diagnostic_row["best_match_count"] = sum(1 for row in reach.to_records() if row.get("best_corridor_diagnostics") == corridor_id)
            diagnostic_row["score_sum"] = sum(float(item["score"]) for item in items)
            diagnostic_row["score_mean"] = (sum(float(item["score"]) for item in items) / len(items)) if items else None
            diagnostic_row["distance_mean"] = (sum(float(item["distance"]) for item in items) / len(items)) if items else None
            diagnostic_row["anchor_distance_mean"] = (sum(float(item["anchor_distance"]) for item in items) / len(items)) if items else None
            diagnostic_row["path_anchor"] = path_anchor
            diagnostic_row["distance_mode"] = distance_mode
            diagnostic_row["score_mode"] = score_mode
            rows.append(diagnostic_row)
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=corridors.geometry_column, crs=self.crs or corridors.crs)


def _resolve_zone_fit_weights(score_weights: dict[str, float] | None) -> dict[str, float]:
    default_weights = {
        "containment": 0.4,
        "overlap": 0.3,
        "size": 0.3,
        "access": 0.0,
        "alignment": 0.0,
    }
    if score_weights is None:
        return default_weights

    resolved = dict(default_weights)
    for name, value in score_weights.items():
        if name not in resolved:
            raise ValueError(f"unsupported zone fit weight: {name}")
        if value < 0:
            raise ValueError("zone fit weights must be zero or greater")
        resolved[name] = float(value)

    if sum(resolved.values()) <= 0:
        raise ValueError("at least one zone fit weight must be greater than zero")
    return resolved


def _cluster_sort_key(row: Record, index: int, id_column: str) -> tuple[str, int]:
    if id_column in row:
        return (str(row[id_column]), index)
    return (str(index), index)


def _cluster_silhouette_scores(
    centroids: Sequence[Coordinate],
    assignments: Sequence[int],
    distance_method: str,
) -> list[float]:
    unique_clusters = sorted(set(assignments))
    if len(unique_clusters) <= 1:
        return [0.0 for _ in centroids]

    members_by_cluster = {
        cluster_id: [index for index, assignment in enumerate(assignments) if assignment == cluster_id]
        for cluster_id in unique_clusters
    }
    scores: list[float] = []
    for index, point in enumerate(centroids):
        own_cluster = assignments[index]
        own_members = [member for member in members_by_cluster[own_cluster] if member != index]
        if own_members:
            intra_distance = sum(
                coordinate_distance(point, centroids[member], method=distance_method)
                for member in own_members
            ) / len(own_members)
        else:
            intra_distance = 0.0

        nearest_other_distance = min(
            sum(coordinate_distance(point, centroids[member], method=distance_method) for member in members_by_cluster[cluster_id]) / len(members_by_cluster[cluster_id])
            for cluster_id in unique_clusters
            if cluster_id != own_cluster and members_by_cluster[cluster_id]
        )
        denominator = max(intra_distance, nearest_other_distance)
        if denominator == 0.0:
            scores.append(0.0)
        else:
            scores.append((nearest_other_distance - intra_distance) / denominator)
    return scores


def _polyline_length(vertices: Sequence[Coordinate], method: str = "euclidean") -> float:
    if len(vertices) < 2:
        return 0.0
    return sum(coordinate_distance(vertices[index - 1], vertices[index], method=method) for index in range(1, len(vertices)))


def _point_to_polyline_distance_details(point: Coordinate, vertices: Sequence[Coordinate], method: str = "euclidean") -> tuple[float, float]:
    if not vertices:
        return (float("inf"), float("inf"))
    if len(vertices) == 1:
        return (coordinate_distance(point, vertices[0], method=method), 0.0)

    if method == "haversine":
        projected_point, projected_vertices = _project_to_local_tangent_plane(point, vertices)
        return _point_to_polyline_distance_details(projected_point, projected_vertices, method="euclidean")

    best_offset = float("inf")
    best_along = float("inf")
    cumulative_length = 0.0
    for index in range(1, len(vertices)):
        segment_start = vertices[index - 1]
        segment_end = vertices[index]
        offset_distance, projection, t_value = _point_to_segment_projection(point, segment_start, segment_end)
        segment_length = coordinate_distance(segment_start, segment_end, method="euclidean")
        along_distance = cumulative_length + (segment_length * t_value)
        if offset_distance < best_offset:
            best_offset = offset_distance
            best_along = along_distance
        cumulative_length += segment_length
    return (best_offset, best_along)


def _point_to_segment_projection(point: Coordinate, seg_start: Coordinate, seg_end: Coordinate) -> tuple[float, Coordinate, float]:
    sx, sy = seg_start
    ex, ey = seg_end
    px, py = point
    dx, dy = ex - sx, ey - sy
    length_sq = dx * dx + dy * dy
    if length_sq == 0.0:
        return (coordinate_distance(point, seg_start, method="euclidean"), seg_start, 0.0)
    t_value = max(0.0, min(1.0, ((px - sx) * dx + (py - sy) * dy) / length_sq))
    projection = (sx + (t_value * dx), sy + (t_value * dy))
    return (coordinate_distance(point, projection, method="euclidean"), projection, t_value)


def _project_to_local_tangent_plane(point: Coordinate, vertices: Sequence[Coordinate]) -> tuple[Coordinate, list[Coordinate]]:
    all_coordinates = [point, *vertices]
    reference_lat = math.radians(sum(coordinate[1] for coordinate in all_coordinates) / len(all_coordinates))

    def project(coordinate: Coordinate) -> Coordinate:
        lon_radians = math.radians(coordinate[0])
        lat_radians = math.radians(coordinate[1])
        x_value = 6371.0088 * lon_radians * math.cos(reference_lat)
        y_value = 6371.0088 * lat_radians
        return (x_value, y_value)

    return (project(point), [project(vertex) for vertex in vertices])


def _resolve_anchor_distance(along_distance: float, total_length: float, path_anchor: CorridorPathAnchor) -> float:
    if path_anchor == "start":
        return along_distance
    if path_anchor == "end":
        return max(0.0, total_length - along_distance)
    return 0.0


def _rectangle_polygon(min_x: float, min_y: float, max_x: float, max_y: float) -> Geometry:
    return {
        "type": "Polygon",
        "coordinates": (
            (min_x, min_y),
            (max_x, min_y),
            (max_x, max_y),
            (min_x, max_y),
            (min_x, min_y),
        ),
    }


def _hexagon_polygon(center_x: float, center_y: float, size: float) -> Geometry:
    vertices = []
    for angle_degrees in (90, 150, 210, 270, 330, 30):
        angle_radians = math.radians(angle_degrees)
        vertices.append((center_x + (size * math.cos(angle_radians)), center_y + (size * math.sin(angle_radians))))
    vertices.append(vertices[0])
    return {"type": "Polygon", "coordinates": tuple(vertices)}


def _as_coordinate(value: Any) -> Coordinate:
    return (float(value[0]), float(value[1]))


def _coordinate_key(point: Coordinate) -> str:
    return f"{point[0]:.12f},{point[1]:.12f}"


def _same_coordinate(left: Coordinate, right: Coordinate, tolerance: float = 1e-9) -> bool:
    return abs(left[0] - right[0]) <= tolerance and abs(left[1] - right[1]) <= tolerance


def _build_snap_coordinate_lookup(
    coordinates: Sequence[Coordinate],
    coordinate_index: SpatialIndex,
    tolerance: float,
) -> dict[str, Coordinate]:
    sorted_coordinates = sorted(coordinates)
    visited: set[str] = set()
    lookup: dict[str, Coordinate] = {}

    for coordinate in sorted_coordinates:
        coordinate_key = _coordinate_key(coordinate)
        if coordinate_key in visited:
            continue
        component: dict[str, Coordinate] = {}
        stack = [coordinate]
        visited.add(coordinate_key)
        while stack:
            current = stack.pop()
            current_key = _coordinate_key(current)
            component[current_key] = current
            candidate_indexes = coordinate_index.query(
                (
                    current[0] - tolerance,
                    current[1] - tolerance,
                    current[0] + tolerance,
                    current[1] + tolerance,
                )
            )
            for candidate_index in candidate_indexes:
                candidate = coordinates[candidate_index]
                candidate_key = _coordinate_key(candidate)
                if candidate_key in visited:
                    continue
                if coordinate_distance(current, candidate, method="euclidean") > tolerance:
                    continue
                visited.add(candidate_key)
                stack.append(candidate)
        anchor = min(component.values())
        for component_key in component:
            lookup[component_key] = anchor
    return lookup


def _snap_geometry(
    geometry: Geometry,
    snap_lookup: dict[str, Coordinate],
) -> tuple[Geometry, int, bool]:
    geometry_kind = geometry_type(geometry)
    if geometry_kind == "Point":
        coordinate = _as_coordinate(geometry["coordinates"])
        snapped = snap_lookup.get(_coordinate_key(coordinate), coordinate)
        changed = 0 if _same_coordinate(snapped, coordinate) else 1
        return {"type": "Point", "coordinates": snapped}, changed, False

    coordinates = [_as_coordinate(value) for value in geometry["coordinates"]]
    if geometry_kind == "Polygon":
        coordinates = coordinates[:-1]
    snapped_coordinates = [snap_lookup.get(_coordinate_key(coordinate), coordinate) for coordinate in coordinates]
    changed_vertex_count = sum(
        0 if _same_coordinate(original, snapped) else 1
        for original, snapped in zip(coordinates, snapped_coordinates, strict=True)
    )
    deduped_coordinates: list[Coordinate] = []
    for coordinate in snapped_coordinates:
        if deduped_coordinates and _same_coordinate(deduped_coordinates[-1], coordinate):
            continue
        deduped_coordinates.append(coordinate)

    if geometry_kind == "LineString":
        if len(deduped_coordinates) < 2:
            return geometry, changed_vertex_count, True
        return {"type": "LineString", "coordinates": tuple(deduped_coordinates)}, changed_vertex_count, False

    while len(deduped_coordinates) > 1 and _same_coordinate(deduped_coordinates[0], deduped_coordinates[-1]):
        deduped_coordinates.pop()
    if len(deduped_coordinates) < 3:
        return geometry, changed_vertex_count, True
    polygon_ring = tuple(deduped_coordinates + [deduped_coordinates[0]])
    return {"type": "Polygon", "coordinates": polygon_ring}, changed_vertex_count, False


def _build_linestring_info(geometry: Geometry) -> dict[str, Any]:
    coordinates = tuple(_as_coordinate(value) for value in geometry["coordinates"])
    cumulative_lengths = [0.0]
    for start, end in zip(coordinates, coordinates[1:]):
        cumulative_lengths.append(cumulative_lengths[-1] + coordinate_distance(start, end, method="euclidean"))
    return {
        "coordinates": coordinates,
        "cumulative_lengths": tuple(cumulative_lengths),
        "total_length": cumulative_lengths[-1],
    }


def _locate_point_fraction_on_linestring(line_info: dict[str, Any], point: Coordinate) -> float:
    coordinates: Sequence[Coordinate] = line_info["coordinates"]
    cumulative_lengths: Sequence[float] = line_info["cumulative_lengths"]
    total_length = float(line_info["total_length"])
    if total_length <= 0.0:
        return 0.0
    for segment_index, (start, end) in enumerate(zip(coordinates, coordinates[1:])):
        if not _point_on_segment(point, start, end):
            continue
        segment_length = coordinate_distance(start, end, method="euclidean")
        if segment_length <= 0.0:
            return cumulative_lengths[segment_index] / total_length
        distance_to_point = coordinate_distance(start, point, method="euclidean")
        return (cumulative_lengths[segment_index] + distance_to_point) / total_length
    raise ValueError("point does not lie on the input linestring")


def _line_segment_records(rows: Sequence[Record], geometry_column: str) -> list[dict[str, Any]]:
    segment_records: list[dict[str, Any]] = []
    for row_index, row in enumerate(rows):
        coordinates = tuple(_as_coordinate(value) for value in row[geometry_column]["coordinates"])
        for segment_index, (start, end) in enumerate(zip(coordinates, coordinates[1:])):
            segment_records.append(
                {
                    "source_index": row_index,
                    "segment_index": segment_index,
                    "start": start,
                    "end": end,
                    "bounds": (
                        min(start[0], end[0]),
                        min(start[1], end[1]),
                        max(start[0], end[0]),
                        max(start[1], end[1]),
                    ),
                }
            )
    return segment_records


def _register_cut_point(points: dict[str, Coordinate], point: Coordinate) -> bool:
    point_key = _coordinate_key(point)
    if point_key in points:
        return False
    points[point_key] = point
    return True


def _clean_geometry(
    original_geometry: Geometry,
    working_geometry: Geometry,
    min_segment_length: float,
) -> tuple[Geometry, dict[str, Any]]:
    geometry_kind = geometry_type(working_geometry)
    input_vertex_count = len(geometry_vertices(original_geometry))
    if geometry_kind == "Point":
        changed = not _same_coordinate(_as_coordinate(original_geometry["coordinates"]), _as_coordinate(working_geometry["coordinates"]))
        return working_geometry, {
            "changed": changed,
            "removed_vertex_count": 0,
            "removed_short_segment_count": 0,
            "input_vertex_count": 1,
            "output_vertex_count": 1,
            "collapsed": False,
        }

    coordinates = [_as_coordinate(value) for value in working_geometry["coordinates"]]
    is_polygon = geometry_kind == "Polygon"
    if is_polygon:
        coordinates = coordinates[:-1]
        input_vertex_count -= 1

    deduped_coordinates: list[Coordinate] = []
    for coordinate in coordinates:
        if deduped_coordinates and _same_coordinate(deduped_coordinates[-1], coordinate):
            continue
        deduped_coordinates.append(coordinate)

    cleaned_coordinates = [deduped_coordinates[0]] if deduped_coordinates else []
    removed_short_segment_count = 0
    for coordinate in deduped_coordinates[1:]:
        if coordinate_distance(cleaned_coordinates[-1], coordinate, method="euclidean") < min_segment_length:
            removed_short_segment_count += 1
            continue
        cleaned_coordinates.append(coordinate)

    collapsed = False
    if geometry_kind == "LineString":
        if len(cleaned_coordinates) < 2:
            collapsed = True
            cleaned_geometry = original_geometry
            output_vertex_count = len(geometry_vertices(original_geometry))
        else:
            cleaned_geometry = {"type": "LineString", "coordinates": tuple(cleaned_coordinates)}
            output_vertex_count = len(cleaned_coordinates)
    else:
        while len(cleaned_coordinates) > 1 and _same_coordinate(cleaned_coordinates[0], cleaned_coordinates[-1]):
            cleaned_coordinates.pop()
        if len(cleaned_coordinates) < 3:
            collapsed = True
            cleaned_geometry = original_geometry
            output_vertex_count = len(geometry_vertices(original_geometry)) - 1
        else:
            cleaned_geometry = {"type": "Polygon", "coordinates": tuple(cleaned_coordinates + [cleaned_coordinates[0]])}
            output_vertex_count = len(cleaned_coordinates)

    return cleaned_geometry, {
        "changed": collapsed or cleaned_geometry != original_geometry,
        "removed_vertex_count": max(0, input_vertex_count - output_vertex_count),
        "removed_short_segment_count": removed_short_segment_count,
        "input_vertex_count": input_vertex_count,
        "output_vertex_count": output_vertex_count,
        "collapsed": collapsed,
    }


def _is_coordinate_value(value: Any) -> bool:
    return (
        isinstance(value, Sequence)
        and not isinstance(value, (str, bytes, dict))
        and len(value) == 2
        and all(isinstance(item, (int, float)) for item in value)
    )


def _point_parameter(point: Coordinate, start: Coordinate, end: Coordinate) -> float:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length_sq = dx * dx + dy * dy
    if length_sq == 0.0:
        return 0.0
    return ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / length_sq


def _segment_intersection_points(first_start: Coordinate, first_end: Coordinate, second_start: Coordinate, second_end: Coordinate) -> list[Coordinate]:
    points: dict[str, Coordinate] = {}
    denominator = ((first_start[0] - first_end[0]) * (second_start[1] - second_end[1])) - ((first_start[1] - first_end[1]) * (second_start[0] - second_end[0]))
    if abs(denominator) <= 1e-12:
        for point in (first_start, first_end, second_start, second_end):
            if _point_on_segment(point, first_start, first_end) and _point_on_segment(point, second_start, second_end):
                points[_coordinate_key(point)] = point
        return list(points.values())

    first_det = (first_start[0] * first_end[1]) - (first_start[1] * first_end[0])
    second_det = (second_start[0] * second_end[1]) - (second_start[1] * second_end[0])
    x_value = ((first_det * (second_start[0] - second_end[0])) - ((first_start[0] - first_end[0]) * second_det)) / denominator
    y_value = ((first_det * (second_start[1] - second_end[1])) - ((first_start[1] - first_end[1]) * second_det)) / denominator
    intersection = (float(x_value), float(y_value))
    if _point_on_segment(intersection, first_start, first_end) and _point_on_segment(intersection, second_start, second_end):
        points[_coordinate_key(intersection)] = intersection
    return list(points.values())


def _point_on_segment(point: Coordinate, start: Coordinate, end: Coordinate, tolerance: float = 1e-9) -> bool:
    cross = ((point[1] - start[1]) * (end[0] - start[0])) - ((point[0] - start[0]) * (end[1] - start[1]))
    if abs(cross) > tolerance:
        return False
    return (
        min(start[0], end[0]) - tolerance <= point[0] <= max(start[0], end[0]) + tolerance
        and min(start[1], end[1]) - tolerance <= point[1] <= max(start[1], end[1]) + tolerance
    )


def _expand_bounds(bounds: tuple[float, float, float, float], distance: float) -> tuple[float, float, float, float]:
    return (
        bounds[0] - distance,
        bounds[1] - distance,
        bounds[2] + distance,
        bounds[3] + distance,
    )


def _geometry_size_metric(geometry: Geometry) -> float:
    geometry_kind = geometry_type(geometry)
    if geometry_kind == "Polygon":
        return geometry_area(geometry)
    if geometry_kind == "LineString":
        return geometry_length(geometry)
    return 1.0


def _size_ratio(left: float, right: float) -> float:
    if left <= 0.0 and right <= 0.0:
        return 1.0
    if left <= 0.0 or right <= 0.0:
        return 0.0
    return min(left, right) / max(left, right)


def _coverage_share(overlap_size: float, geometry_size: float, intersects: bool) -> float:
    if geometry_size <= 0.0:
        return 1.0 if intersects else 0.0
    return max(0.0, min(1.0, overlap_size / geometry_size))


def _geometry_overlap_size(left_geometry: Geometry, right_geometry: Geometry) -> float:
    if not geometry_intersects(left_geometry, right_geometry):
        return 0.0
    try:
        intersections = overlay_intersections([left_geometry], [right_geometry])
    except RuntimeError:
        intersections = []
    if intersections:
        return sum(_geometry_size_metric(geometry) for _left_index, _right_index, geometries in intersections for geometry in geometries)

    left_bounds = geometry_bounds(left_geometry)
    right_bounds = geometry_bounds(right_geometry)
    overlap_width = max(0.0, min(left_bounds[2], right_bounds[2]) - max(left_bounds[0], right_bounds[0]))
    overlap_height = max(0.0, min(left_bounds[3], right_bounds[3]) - max(left_bounds[1], right_bounds[1]))
    geometry_kind = geometry_type(left_geometry)
    if geometry_kind == "Polygon" and geometry_type(right_geometry) == "Polygon":
        return overlap_width * overlap_height
    if geometry_kind == "LineString" and geometry_type(right_geometry) == "LineString":
        return max(overlap_width, overlap_height)
    return 1.0


def _autocorrelation_statistics(
    values: Sequence[float],
    neighbor_indexes: Sequence[Sequence[int]],
    neighbor_weights: Sequence[Sequence[float]],
) -> dict[str, Any]:
    row_count = len(values)
    mean_value = (sum(values) / row_count) if row_count else 0.0
    centered_values = [value - mean_value for value in values]
    variance_sum = sum(value * value for value in centered_values)
    m2 = (variance_sum / row_count) if row_count else 0.0

    weighted_cross_sum = 0.0
    weighted_difference_sum = 0.0
    total_weight = 0.0
    local_moran_values: list[float | None] = []
    local_geary_values: list[float | None] = []
    for origin_index, (indexes, weights) in enumerate(zip(neighbor_indexes, neighbor_weights, strict=True)):
        local_cross_sum = 0.0
        local_difference_sum = 0.0
        for neighbor_index, weight in zip(indexes, weights, strict=True):
            weighted_cross_sum += weight * centered_values[origin_index] * centered_values[neighbor_index]
            weighted_difference_sum += weight * (values[origin_index] - values[neighbor_index]) ** 2
            total_weight += weight
            local_cross_sum += weight * centered_values[neighbor_index]
            local_difference_sum += weight * (values[origin_index] - values[neighbor_index]) ** 2
        if m2 > 0.0:
            local_moran_values.append((centered_values[origin_index] / m2) * local_cross_sum)
            local_geary_values.append(local_difference_sum / m2)
        else:
            local_moran_values.append(None)
            local_geary_values.append(None)

    global_moran = None
    global_geary = None
    if row_count > 0 and variance_sum > 0.0 and total_weight > 0.0:
        global_moran = (row_count / total_weight) * (weighted_cross_sum / variance_sum)
        global_geary = ((row_count - 1) / (2.0 * total_weight)) * (weighted_difference_sum / variance_sum) if row_count > 1 else None
    return {
        "mean_value": mean_value,
        "centered_values": centered_values,
        "variance_sum": variance_sum,
        "m2": m2,
        "total_weight": total_weight,
        "global_moran": global_moran,
        "global_geary": global_geary,
        "local_moran_values": local_moran_values,
        "local_geary_values": local_geary_values,
    }


def _local_cluster_label(
    centered_value: float,
    lag_centered_value: float | None,
    local_moran: float | None,
    local_p_value: float | None,
    significance_level: float,
) -> str | None:
    if local_moran is None or lag_centered_value is None:
        return None
    if local_p_value is not None and local_p_value > significance_level:
        return "not_significant"
    if centered_value > 0.0 and lag_centered_value > 0.0:
        return "high-high"
    if centered_value < 0.0 and lag_centered_value < 0.0:
        return "low-low"
    if centered_value > 0.0 and lag_centered_value < 0.0:
        return "high-low"
    if centered_value < 0.0 and lag_centered_value > 0.0:
        return "low-high"
    return "mixed"


def _local_cluster_code(cluster_label: str | None) -> str | None:
    if cluster_label is None:
        return None
    return {
        "high-high": "HH",
        "low-low": "LL",
        "high-low": "HL",
        "low-high": "LH",
        "not_significant": "NS",
        "mixed": "MX",
    }.get(cluster_label, cluster_label.upper())


def _local_cluster_family(cluster_label: str | None) -> str | None:
    if cluster_label == "high-high":
        return "hotspot"
    if cluster_label == "low-low":
        return "coldspot"
    if cluster_label in {"high-low", "low-high"}:
        return "outlier"
    if cluster_label == "not_significant":
        return "not_significant"
    if cluster_label is None:
        return None
    return "mixed"


def _autocorr_report_label(family: str) -> str:
    return {
        "hotspot": "hotspot cluster",
        "coldspot": "coldspot cluster",
        "outlier": "spatial outlier cluster",
        "mixed": "mixed local pattern",
        "not_significant": "not significant",
    }.get(family, family.replace("_", " "))


def _autocorr_report_priority(family: str, intensity_score: float) -> str:
    if family in {"hotspot", "coldspot"} and intensity_score >= 0.2:
        return "primary"
    if family == "outlier" or intensity_score >= 0.05:
        return "secondary"
    return "background"


def _primary_change_matches(candidate_pairs: Sequence[dict[str, Any]], key_name: str = "right_index") -> list[dict[str, Any]]:
    if not candidate_pairs:
        return []
    best_score = float(candidate_pairs[0]["similarity_score"])
    threshold = max(best_score - 0.1, best_score * 0.9)
    matches = [pair for pair in candidate_pairs if float(pair["similarity_score"]) >= threshold]
    return sorted(matches, key=lambda item: (-float(item["similarity_score"]), float(item["centroid_distance"]), int(item[key_name])))


def _attribute_change_summary(
    left_rows: Sequence[Record],
    right_rows: Sequence[Record],
    attribute_columns: Sequence[str],
) -> dict[str, Any]:
    summaries: dict[str, Any] = {}
    single_left = len(left_rows) == 1
    single_right = len(right_rows) == 1
    for column in attribute_columns:
        left_values = _distinct_values(row.get(column) for row in left_rows)
        right_values = _distinct_values(row.get(column) for row in right_rows)
        if left_values == right_values:
            continue
        if single_left and single_right:
            summaries[column] = {"left": left_values[0], "right": right_values[0]}
        else:
            summaries[column] = {"left_values": left_values, "right_values": right_values}
    return summaries


def _distinct_values(values: Iterable[Any]) -> list[Any]:
    distinct: list[Any] = []
    for value in values:
        if value not in distinct:
            distinct.append(value)
    return distinct


def _consecutive_distinct_values(values: Iterable[Any]) -> list[Any]:
    distinct: list[Any] = []
    previous = object()
    for value in values:
        if value != previous:
            distinct.append(value)
            previous = value
    return distinct


def _mean_centroid_geometry(rows: Sequence[Record], geometry_column: str) -> Geometry:
    centroids = [geometry_centroid(row[geometry_column]) for row in rows]
    mean_x = sum(centroid[0] for centroid in centroids) / len(centroids)
    mean_y = sum(centroid[1] for centroid in centroids) / len(centroids)
    return {"type": "Point", "coordinates": [mean_x, mean_y]}


def _trajectory_anomaly_level(confidence_score: float, anomaly_count: int) -> str:
    if confidence_score < 0.35 or anomaly_count >= 3:
        return "high"
    if confidence_score < 0.7 or anomaly_count >= 1:
        return "moderate"
    return "low"


def _annotate_change_event_groups(rows: list[Record], change_suffix: str) -> None:
    grouped_rows: dict[tuple[Any, ...], list[Record]] = {}
    for row in rows:
        group_key = (
            row.get(f"change_class_{change_suffix}"),
            row.get(f"event_side_{change_suffix}"),
            tuple(row.get(f"left_ids_{change_suffix}", [])),
            tuple(row.get(f"right_ids_{change_suffix}", [])),
        )
        grouped_rows.setdefault(group_key, []).append(row)

    for group_index, (group_key, grouped) in enumerate(sorted(grouped_rows.items(), key=lambda item: item[0]), start=1):
        left_ids = sorted({value for row in grouped for value in row.get(f"left_ids_{change_suffix}", [])})
        right_ids = sorted({value for row in grouped for value in row.get(f"right_ids_{change_suffix}", [])})
        attribute_columns = sorted(
            {
                column
                for row in grouped
                for column in (row.get(f"attribute_changes_{change_suffix}") or {}).keys()
            }
        )
        similarity_scores = [
            float(row[f"similarity_score_{change_suffix}"])
            for row in grouped
            if row.get(f"similarity_score_{change_suffix}") is not None
        ]
        area_share_scores = [
            float(row[f"area_share_score_{change_suffix}"])
            for row in grouped
            if row.get(f"area_share_score_{change_suffix}") is not None
        ]
        summary = {
            "change_class": group_key[0],
            "event_side": group_key[1],
            "left_ids": left_ids,
            "right_ids": right_ids,
            "left_count": len(left_ids),
            "right_count": len(right_ids),
            "row_count": len(grouped),
            "feature_count": len(left_ids) + len(right_ids),
            "attribute_columns": attribute_columns,
            "mean_similarity_score": (sum(similarity_scores) / len(similarity_scores)) if similarity_scores else None,
            "mean_area_share_score": (sum(area_share_scores) / len(area_share_scores)) if area_share_scores else None,
        }
        event_group_id = f"event-{group_index:05d}"
        for row in grouped:
            row[f"event_group_id_{change_suffix}"] = event_group_id
            row[f"event_row_count_{change_suffix}"] = len(grouped)
            row[f"event_feature_count_{change_suffix}"] = len(left_ids) + len(right_ids)
            row[f"event_summary_{change_suffix}"] = summary


def _change_event_signature(row: Record, change_suffix: str) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    return (
        str(row[f"change_class_{change_suffix}"]),
        tuple(str(value) for value in row.get(f"left_ids_{change_suffix}", [])),
        tuple(str(value) for value in row.get(f"right_ids_{change_suffix}", [])),
    )


def _format_change_event_signature(signature: tuple[str, tuple[str, ...], tuple[str, ...]]) -> str:
    change_class, left_ids, right_ids = signature
    left_part = ",".join(left_ids) if left_ids else "none"
    right_part = ",".join(right_ids) if right_ids else "none"
    return f"{change_class}|{left_part}|{right_part}"


def _numeric_delta(current: Any, baseline: Any) -> float | None:
    if current is None or baseline is None:
        return None
    return float(current) - float(baseline)


def _change_event_status_rank(event_status: str) -> int:
    return {
        "emerged": 0,
        "resolved": 1,
        "persisted": 2,
    }.get(event_status, 3)


def _match_equivalent_change_events(
    baseline_rows: Sequence[Record],
    current_rows: Sequence[Record],
    change_suffix: str,
    geometry_column: str,
    min_similarity: float,
) -> list[tuple[tuple[str, tuple[str, ...], tuple[str, ...]], Record | None, Record | None, float | None]]:
    candidate_pairs: list[tuple[float, int, int]] = []
    for baseline_index, baseline_row in enumerate(baseline_rows):
        for current_index, current_row in enumerate(current_rows):
            similarity = _equivalent_change_event_similarity(
                baseline_row,
                current_row,
                change_suffix=change_suffix,
                geometry_column=geometry_column,
            )
            if similarity >= min_similarity:
                candidate_pairs.append((similarity, baseline_index, current_index))

    candidate_pairs.sort(key=lambda item: (-float(item[0]), item[1], item[2]))
    matched_baseline_indexes: set[int] = set()
    matched_current_indexes: set[int] = set()
    results: list[tuple[tuple[str, tuple[str, ...], tuple[str, ...]], Record | None, Record | None, float | None]] = []

    for similarity, baseline_index, current_index in candidate_pairs:
        if baseline_index in matched_baseline_indexes or current_index in matched_current_indexes:
            continue
        baseline_row = baseline_rows[baseline_index]
        current_row = current_rows[current_index]
        matched_baseline_indexes.add(baseline_index)
        matched_current_indexes.add(current_index)
        signature = _change_event_pair_signature(baseline_row, current_row, change_suffix)
        results.append((signature, baseline_row, current_row, similarity))

    for baseline_index, baseline_row in enumerate(baseline_rows):
        if baseline_index in matched_baseline_indexes:
            continue
        signature = _change_event_signature(baseline_row, change_suffix)
        results.append((signature, baseline_row, None, None))

    for current_index, current_row in enumerate(current_rows):
        if current_index in matched_current_indexes:
            continue
        signature = _change_event_signature(current_row, change_suffix)
        results.append((signature, None, current_row, None))

    return sorted(
        results,
        key=lambda item: (
            _change_event_status_rank("persisted" if item[1] is not None and item[2] is not None else ("resolved" if item[1] is not None else "emerged")),
            str(item[0][0]),
            item[0][1],
            item[0][2],
        ),
    )


def _equivalent_change_event_similarity(
    baseline_row: Record,
    current_row: Record,
    change_suffix: str,
    geometry_column: str,
) -> float:
    baseline_summary = dict(baseline_row.get(f"event_summary_{change_suffix}") or {})
    current_summary = dict(current_row.get(f"event_summary_{change_suffix}") or {})
    if str(baseline_row.get(f"change_class_{change_suffix}")) != str(current_row.get(f"change_class_{change_suffix}")):
        return 0.0

    left_similarity = _set_similarity(
        baseline_row.get(f"left_ids_{change_suffix}", []),
        current_row.get(f"left_ids_{change_suffix}", []),
    )
    right_similarity = _set_similarity(
        baseline_row.get(f"right_ids_{change_suffix}", []),
        current_row.get(f"right_ids_{change_suffix}", []),
    )
    feature_count_similarity = _count_similarity(
        baseline_summary.get("feature_count"),
        current_summary.get("feature_count"),
    )
    row_count_similarity = _count_similarity(
        baseline_summary.get("row_count"),
        current_summary.get("row_count"),
    )
    attribute_similarity = _set_similarity(
        baseline_summary.get("attribute_columns", []),
        current_summary.get("attribute_columns", []),
    )
    geometry_similarity = _geometry_similarity(
        baseline_row.get(geometry_column),
        current_row.get(geometry_column),
    )
    side_similarity = 1.0 if str(baseline_row.get(f"event_side_{change_suffix}")) == str(current_row.get(f"event_side_{change_suffix}")) else 0.0
    return (
        (0.1 * side_similarity)
        + (0.2 * left_similarity)
        + (0.2 * right_similarity)
        + (0.15 * feature_count_similarity)
        + (0.1 * row_count_similarity)
        + (0.1 * attribute_similarity)
        + (0.15 * geometry_similarity)
    )


def _set_similarity(left_values: Iterable[Any], right_values: Iterable[Any]) -> float:
    left_set = {str(value) for value in left_values}
    right_set = {str(value) for value in right_values}
    if not left_set and not right_set:
        return 1.0
    union = left_set | right_set
    if not union:
        return 0.0
    return len(left_set & right_set) / len(union)


def _count_similarity(left_value: Any, right_value: Any) -> float:
    if left_value is None or right_value is None:
        return 0.0
    left_count = float(left_value)
    right_count = float(right_value)
    if left_count <= 0.0 and right_count <= 0.0:
        return 1.0
    denominator = max(left_count, right_count)
    if denominator <= 0.0:
        return 0.0
    return min(left_count, right_count) / denominator


def _geometry_similarity(left_geometry: Any, right_geometry: Any) -> float:
    if not isinstance(left_geometry, dict) or not isinstance(right_geometry, dict):
        return 0.0
    distance_value = geometry_distance(left_geometry, right_geometry)
    return 1.0 / (1.0 + float(distance_value))


def _change_event_pair_signature(
    baseline_row: Record,
    current_row: Record,
    change_suffix: str,
) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    return (
        str(current_row.get(f"change_class_{change_suffix}") or baseline_row.get(f"change_class_{change_suffix}")),
        tuple(str(value) for value in (current_row.get(f"left_ids_{change_suffix}") or baseline_row.get(f"left_ids_{change_suffix}") or [])),
        tuple(str(value) for value in (current_row.get(f"right_ids_{change_suffix}") or baseline_row.get(f"right_ids_{change_suffix}") or [])),
    )


def _gap_transition_penalty(previous_gap_state: bool, current_gap_state: bool, gap_penalty: float) -> float:
    if previous_gap_state and current_gap_state:
        return gap_penalty * 0.25
    if previous_gap_state or current_gap_state:
        return gap_penalty
    return 0.0


def _edge_transition_cost(
    previous_edge_index: int,
    current_edge_index: int,
    previous_along_distance: float,
    current_along_distance: float,
    edge_rows: Sequence[Record],
    adjacency: dict[str, list[tuple[str, float, int]]],
    from_node_id_column: str,
    to_node_id_column: str,
    cost_column: str,
    node_distance_cache: dict[str, dict[str, float]],
    transition_cache: dict[tuple[int, int, float, float], float],
) -> float:
    cache_key = (
        previous_edge_index,
        current_edge_index,
        round(previous_along_distance, 6),
        round(current_along_distance, 6),
    )
    if cache_key in transition_cache:
        return transition_cache[cache_key]

    previous_row = edge_rows[previous_edge_index]
    current_row = edge_rows[current_edge_index]
    previous_from_node = str(previous_row[from_node_id_column])
    previous_to_node = str(previous_row[to_node_id_column])
    current_from_node = str(current_row[from_node_id_column])
    current_to_node = str(current_row[to_node_id_column])
    previous_edge_cost = max(float(previous_row.get(cost_column, 0.0)), 0.0)
    current_edge_cost = max(float(current_row.get(cost_column, 0.0)), 0.0)

    if previous_edge_index == current_edge_index:
        best_cost = abs(current_along_distance - previous_along_distance)
        transition_cache[cache_key] = best_cost
        return best_cost

    previous_nodes = [
        (previous_from_node, max(0.0, previous_along_distance)),
        (previous_to_node, max(0.0, previous_edge_cost - previous_along_distance)),
    ]
    current_nodes = [
        (current_from_node, max(0.0, current_along_distance)),
        (current_to_node, max(0.0, current_edge_cost - current_along_distance)),
    ]
    target_nodes = {node_id for node_id, _node_cost in current_nodes}

    best_cost = float("inf")
    for node_id, source_edge_cost in previous_nodes:
        if node_id not in node_distance_cache:
            node_distance_cache[node_id] = _dijkstra_distances(adjacency, [node_id], stop_nodes=target_nodes)
        distances = node_distance_cache[node_id]
        for target_node, target_edge_cost in current_nodes:
            best_cost = min(best_cost, source_edge_cost + distances.get(target_node, float("inf")) + target_edge_cost)

    if best_cost == float("inf"):
        best_cost = max(previous_edge_cost, current_edge_cost, 0.0)
    transition_cache[cache_key] = best_cost
    return best_cost


def _dijkstra_distances(
    adjacency: dict[str, list[tuple[str, float, int]]],
    origin_node_ids: Sequence[str],
    stop_node: str | None = None,
    stop_nodes: set[str] | None = None,
) -> dict[str, float]:
    distances: dict[str, float] = {node_id: 0.0 for node_id in origin_node_ids}
    queue: list[tuple[float, str]] = [(0.0, node_id) for node_id in origin_node_ids]
    visited: set[str] = set()
    remaining_stop_nodes = set(stop_nodes) if stop_nodes is not None else None

    while queue:
        current_cost, current_node = heappop(queue)
        if current_node in visited:
            continue
        visited.add(current_node)
        if stop_node is not None and current_node == stop_node:
            break
        if remaining_stop_nodes is not None and current_node in remaining_stop_nodes:
            remaining_stop_nodes.remove(current_node)
            if not remaining_stop_nodes:
                break
        for next_node, edge_cost, _edge_index in adjacency.get(current_node, []):
            path_cost = current_cost + edge_cost
            if path_cost < distances.get(next_node, float("inf")):
                distances[next_node] = path_cost
                heappush(queue, (path_cost, next_node))
    return distances


def _reachable_edge_intervals(
    from_cost: float | None,
    to_cost: float | None,
    edge_cost: float,
    max_cost: float,
    directed: bool,
) -> list[tuple[float, float]]:
    intervals: list[tuple[float, float]] = []
    if edge_cost <= 0.0:
        if from_cost is not None and from_cost <= max_cost:
            return [(0.0, 1.0)]
        if not directed and to_cost is not None and to_cost <= max_cost:
            return [(0.0, 1.0)]
        return []

    if from_cost is not None and from_cost <= max_cost:
        intervals.append((0.0, min(1.0, (max_cost - from_cost) / edge_cost)))
    if not directed and to_cost is not None and to_cost <= max_cost:
        intervals.append((max(0.0, 1.0 - ((max_cost - to_cost) / edge_cost)), 1.0))
    if not intervals:
        return []

    merged: list[tuple[float, float]] = []
    for start_value, end_value in sorted(intervals):
        if end_value <= start_value + 1e-9:
            continue
        if not merged or start_value > merged[-1][1] + 1e-9:
            merged.append((start_value, end_value))
            continue
        merged[-1] = (merged[-1][0], max(merged[-1][1], end_value))
    return merged


def _linestring_subgeometry(geometry: Geometry, start_fraction: float, end_fraction: float) -> Geometry | None:
    coordinates = [_as_coordinate(value) for value in geometry["coordinates"]]
    if len(coordinates) < 2:
        return None

    clamped_start = max(0.0, min(1.0, float(start_fraction)))
    clamped_end = max(0.0, min(1.0, float(end_fraction)))
    if clamped_end <= clamped_start + 1e-9:
        return None

    cumulative_lengths = [0.0]
    for start_point, end_point in zip(coordinates, coordinates[1:]):
        cumulative_lengths.append(
            cumulative_lengths[-1] + coordinate_distance(start_point, end_point, method="euclidean")
        )
    total_length = cumulative_lengths[-1]
    if total_length <= 0.0:
        return None

    start_distance = total_length * clamped_start
    end_distance = total_length * clamped_end
    clipped_coordinates = [_interpolate_linestring_coordinate(coordinates, cumulative_lengths, start_distance)]
    for vertex_index in range(1, len(coordinates) - 1):
        vertex_distance = cumulative_lengths[vertex_index]
        if start_distance < vertex_distance < end_distance:
            clipped_coordinates.append(coordinates[vertex_index])
    clipped_coordinates.append(_interpolate_linestring_coordinate(coordinates, cumulative_lengths, end_distance))

    deduped_coordinates: list[Coordinate] = []
    for coordinate in clipped_coordinates:
        if deduped_coordinates and _same_coordinate(deduped_coordinates[-1], coordinate):
            continue
        deduped_coordinates.append(coordinate)
    if len(deduped_coordinates) < 2:
        return None
    return {"type": "LineString", "coordinates": tuple(deduped_coordinates)}


def _interpolate_linestring_coordinate(
    coordinates: Sequence[Coordinate],
    cumulative_lengths: Sequence[float],
    target_distance: float,
) -> Coordinate:
    if target_distance <= 0.0:
        return coordinates[0]
    if target_distance >= cumulative_lengths[-1]:
        return coordinates[-1]

    for index in range(1, len(coordinates)):
        segment_start_distance = cumulative_lengths[index - 1]
        segment_end_distance = cumulative_lengths[index]
        if target_distance > segment_end_distance + 1e-9:
            continue
        segment_length = segment_end_distance - segment_start_distance
        if segment_length <= 0.0:
            return coordinates[index]
        ratio = (target_distance - segment_start_distance) / segment_length
        start_point = coordinates[index - 1]
        end_point = coordinates[index]
        return (
            start_point[0] + ((end_point[0] - start_point[0]) * ratio),
            start_point[1] + ((end_point[1] - start_point[1]) * ratio),
        )
    return coordinates[-1]


def _point_to_segment_distance(point: Coordinate, seg_start: Any, seg_end: Any, method: str = "euclidean") -> float:
    sx, sy = float(seg_start[0]), float(seg_start[1])
    ex, ey = float(seg_end[0]), float(seg_end[1])
    px, py = point
    if method == "haversine":
        return _point_to_segment_distance_haversine((px, py), (sx, sy), (ex, ey))

    dx, dy = ex - sx, ey - sy
    length_sq = dx * dx + dy * dy
    if length_sq == 0:
        return coordinate_distance(point, (sx, sy), method=method)
    t = max(0.0, min(1.0, ((px - sx) * dx + (py - sy) * dy) / length_sq))
    proj_x = sx + t * dx
    proj_y = sy + t * dy
    return coordinate_distance(point, (proj_x, proj_y), method=method)


def _point_to_segment_distance_haversine(point: Coordinate, seg_start: Coordinate, seg_end: Coordinate) -> float:
    reference_lat = math.radians((point[1] + seg_start[1] + seg_end[1]) / 3.0)

    def project(coordinate: Coordinate) -> Coordinate:
        lon_radians = math.radians(coordinate[0])
        lat_radians = math.radians(coordinate[1])
        x_value = 6371.0088 * lon_radians * math.cos(reference_lat)
        y_value = 6371.0088 * lat_radians
        return (x_value, y_value)

    return _point_to_segment_distance(project(point), project(seg_start), project(seg_end), method="euclidean")


__all__ = ["Bounds", "GeoPromptFrame"]