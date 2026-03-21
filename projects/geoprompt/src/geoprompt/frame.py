from __future__ import annotations

import importlib
import math
import random
import warnings
from dataclasses import dataclass
from heapq import heappop, heappush, nsmallest
from typing import Any, Iterable, Literal, Sequence

from .equations import accessibility_index, area_similarity, coordinate_distance, corridor_strength, directional_alignment, gravity_model, prompt_decay, prompt_influence, prompt_interaction
from .geometry import Geometry, geometry_area, geometry_bounds, geometry_centroid, geometry_contains, geometry_convex_hull, geometry_distance, geometry_envelope, geometry_intersects, geometry_intersects_bounds, geometry_length, geometry_type, geometry_vertices, geometry_within, geometry_within_bounds, normalize_geometry, transform_geometry
from .overlay import buffer_geometries, clip_geometries, dissolve_geometries, geometry_from_shapely, overlay_intersections, overlay_union_faces, polygon_split_faces
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
        right_geometries = [row[other.geometry_column] for row in other_rows]
        right_ids = [str(row[right_id_column]) for row in other_rows]
        right_areas = [geometry_area(geometry) for geometry in right_geometries]
        right_lengths = [geometry_length(geometry) for geometry in right_geometries]
        right_groups = [str(row[group_by]) for row in other_rows] if group_by is not None else []
        left_geometries = [row[self.geometry_column] for row in self._rows]
        left_areas = [geometry_area(geometry) for geometry in left_geometries]
        left_lengths = [geometry_length(geometry) for geometry in left_geometries]
        grouped: dict[int, list[tuple[int, list[Geometry]]]] = {}
        for left_index, right_index, geometries in overlay_intersections(
            left_geometries,
            right_geometries,
        ):
            grouped.setdefault(left_index, []).append((right_index, geometries))

        rows: list[Record] = []
        for left_index, left_row in enumerate(self._rows):
            matches = grouped.get(left_index, [])
            if not matches and how == "inner":
                continue

            matched_right_indexes: list[int] = []
            overlap_area = 0.0
            overlap_length = 0.0
            intersection_count = 0
            right_area_total = 0.0
            right_length_total = 0.0
            grouped_matches: dict[str, dict[str, Any]] | None = {} if group_by is not None else None
            for right_index, geometries in matches:
                matched_right_indexes.append(right_index)
                right_area_total += right_areas[right_index]
                right_length_total += right_lengths[right_index]
                pair_area = 0.0
                pair_length = 0.0
                for geometry in geometries:
                    pair_area += geometry_area(geometry)
                    pair_length += geometry_length(geometry)
                overlap_area += pair_area
                overlap_length += pair_length
                intersection_count += len(geometries)
                if grouped_matches is not None:
                    group_value = right_groups[right_index]
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
                    bucket["area_overlap"] += pair_area
                    bucket["length_overlap"] += pair_length
                    bucket[f"{right_id_column}s"].append(right_ids[right_index])
                    bucket["right_area_total"] += right_areas[right_index]
                    bucket["right_length_total"] += right_lengths[right_index]

            matched_rows = [other_rows[right_index] for right_index in matched_right_indexes]
            left_area = left_areas[left_index]
            left_length = left_lengths[left_index]

            resolved_row = dict(left_row)
            resolved_row[f"{right_id_column}s_{summary_suffix}"] = [right_ids[right_index] for right_index in matched_right_indexes]
            resolved_row[f"count_{summary_suffix}"] = len(matched_rows)
            resolved_row[f"intersection_count_{summary_suffix}"] = intersection_count
            resolved_row[f"area_overlap_{summary_suffix}"] = overlap_area
            resolved_row[f"length_overlap_{summary_suffix}"] = overlap_length
            resolved_row[f"area_share_{summary_suffix}"] = (overlap_area / left_area) if left_area > 0 and normalize_by in {"left", "both"} else None
            resolved_row[f"length_share_{summary_suffix}"] = (overlap_length / left_length) if left_length > 0 and normalize_by in {"left", "both"} else None
            resolved_row[f"area_share_right_{summary_suffix}"] = (overlap_area / right_area_total) if right_area_total > 0 and normalize_by in {"right", "both"} else None
            resolved_row[f"length_share_right_{summary_suffix}"] = (overlap_length / right_length_total) if right_length_total > 0 and normalize_by in {"right", "both"} else None
            if grouped_matches is not None:
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
        left_geometries = [row[self.geometry_column] for row in left_rows]
        right_geometries = [row[other.geometry_column] for row in right_rows]
        left_bounds = [geometry_bounds(geometry) for geometry in left_geometries]
        right_bounds = [geometry_bounds(geometry) for geometry in right_geometries]
        left_types = [geometry_type(geometry) for geometry in left_geometries]
        right_types = [geometry_type(geometry) for geometry in right_geometries]
        left_sizes = [_geometry_size_metric(geometry) for geometry in left_geometries]
        right_sizes = [_geometry_size_metric(geometry) for geometry in right_geometries]
        left_ids = [str(row[id_column]) for row in left_rows]
        right_ids = [str(row[resolved_other_id_column]) for row in right_rows]
        shared_attribute_columns = list(attribute_columns) if attribute_columns is not None else sorted(
            (set(self.columns) & set(other.columns)) - {self.geometry_column, other.geometry_column, id_column, resolved_other_id_column}
        )

        pair_scores: list[dict[str, Any]] = []
        left_candidates: dict[int, list[dict[str, Any]]] = {index: [] for index in range(len(left_rows))}
        right_candidates: dict[int, list[dict[str, Any]]] = {index: [] for index in range(len(right_rows))}

        for left_index, left_row in enumerate(left_rows):
            left_geometry = left_geometries[left_index]
            left_centroid = left_centroids[left_index]
            if max_distance is None:
                candidate_indexes = list(range(len(right_rows)))
            else:
                candidate_indexes = right_index.query(_expand_bounds(left_bounds[left_index], max_distance))
            for right_index_value in candidate_indexes:
                right_row = right_rows[right_index_value]
                right_geometry = right_geometries[right_index_value]
                centroid_distance = coordinate_distance(left_centroid, right_centroids[right_index_value], method="euclidean")
                bounds_intersect = _bounds_intersect(left_bounds[left_index], right_bounds[right_index_value])
                intersects = geometry_intersects(left_geometry, right_geometry) if bounds_intersect else False
                if max_distance is not None and centroid_distance > max_distance and not intersects:
                    continue
                attribute_match_count = sum(1 for column in shared_attribute_columns if left_row.get(column) == right_row.get(column))
                attribute_similarity = (attribute_match_count / len(shared_attribute_columns)) if shared_attribute_columns else 1.0
                left_size = left_sizes[left_index]
                right_size = right_sizes[right_index_value]
                size_ratio = _size_ratio(left_size, right_size)
                overlap_size = _geometry_overlap_size(left_geometry, right_geometry) if bounds_intersect else 0.0
                left_area_share = _coverage_share(overlap_size, left_size, intersects)
                right_area_share = _coverage_share(overlap_size, right_size, intersects)
                area_share_score = (left_area_share + right_area_share) / 2.0
                distance_score = 1.0 if centroid_distance <= geometry_tolerance else 1.0 / (1.0 + centroid_distance)
                id_score = 1.0 if left_ids[left_index] == right_ids[right_index_value] else 0.0
                type_factor = 1.0 if left_types[left_index] == right_types[right_index_value] else 0.5
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
            left_exact = {
                _change_event_signature(row, change_suffix): row
                for row in self._rows
            }
            right_exact = {
                _change_event_signature(row, change_suffix): row
                for row in other._rows
            }
            exact_signatures = sorted(set(left_exact) & set(right_exact))
            matched_pairs = [
                (signature, left_exact[signature], right_exact[signature], 1.0)
                for signature in exact_signatures
            ]
            unmatched_left = [row for signature, row in left_exact.items() if signature not in right_exact]
            unmatched_right = [row for signature, row in right_exact.items() if signature not in left_exact]
            matched_pairs.extend(
                _match_equivalent_change_events(
                    unmatched_left,
                    unmatched_right,
                    change_suffix=change_suffix,
                    geometry_column=self.geometry_column,
                    min_similarity=min_similarity,
                )
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
        for row in summary._rows:
            groups = list(row.get(f"groups_{comparison_suffix}", []))
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

    # ------------------------------------------------------------------
    # Tool 1: raster_sample
    # ------------------------------------------------------------------
    def raster_sample(
        self,
        points: "GeoPromptFrame",
        value_column: str,
        k: int = 1,
        distance_method: str = "euclidean",
        sample_suffix: str = "sample",
    ) -> "GeoPromptFrame":
        self._require_column(value_column)
        if k <= 0:
            raise ValueError("k must be greater than zero")
        if self.crs and points.crs and self.crs != points.crs:
            raise ValueError("frames must share the same CRS")
        source_centroids = self._centroids()
        target_centroids = points._centroids()
        rows: list[Record] = []
        for target_index, target_row in enumerate(points._rows):
            distances = [
                (src_index, coordinate_distance(target_centroids[target_index], source_centroids[src_index], method=distance_method))
                for src_index in range(len(self._rows))
            ]
            distances.sort(key=lambda item: item[1])
            nearest = distances[:k]
            if k == 1 and nearest:
                sampled_value = self._rows[nearest[0][0]][value_column]
                sampled_distance = nearest[0][1]
            elif nearest:
                weight_sum = sum(1.0 / max(d, 1e-12) for _, d in nearest)
                sampled_value = sum(
                    float(self._rows[idx][value_column]) / max(d, 1e-12)
                    for idx, d in nearest
                ) / weight_sum
                sampled_distance = nearest[0][1]
            else:
                sampled_value = None
                sampled_distance = None
            resolved = dict(target_row)
            resolved[f"{value_column}_{sample_suffix}"] = sampled_value
            resolved[f"distance_{sample_suffix}"] = sampled_distance
            resolved[f"k_{sample_suffix}"] = k
            rows.append(resolved)
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=points.geometry_column, crs=points.crs or self.crs)

    # ------------------------------------------------------------------
    # Tool 2: zonal_stats
    # ------------------------------------------------------------------
    def zonal_stats(
        self,
        zones: "GeoPromptFrame",
        value_column: str,
        zone_id_column: str = "zone_id",
        aggregations: Sequence[AggregationName] = ("count", "sum", "mean", "min", "max"),
        zonal_suffix: str = "zonal",
    ) -> "GeoPromptFrame":
        self._require_column(value_column)
        zones._require_column(zone_id_column)
        if self.crs and zones.crs and self.crs != zones.crs:
            raise ValueError("frames must share the same CRS")
        point_centroids = self._centroids()
        rows: list[Record] = []
        for zone_row in zones._rows:
            zone_geometry = zone_row[zones.geometry_column]
            matched_values: list[float] = []
            for pt_index, pt_row in enumerate(self._rows):
                pt_geom = {"type": "Point", "coordinates": point_centroids[pt_index]}
                if geometry_within(pt_geom, zone_geometry):
                    val = pt_row.get(value_column)
                    if val is not None:
                        matched_values.append(float(val))
            resolved = dict(zone_row)
            resolved[f"point_count_{zonal_suffix}"] = len(matched_values)
            for agg in aggregations:
                if agg == "count":
                    resolved[f"{value_column}_count_{zonal_suffix}"] = len(matched_values)
                elif not matched_values:
                    resolved[f"{value_column}_{agg}_{zonal_suffix}"] = None
                elif agg == "sum":
                    resolved[f"{value_column}_sum_{zonal_suffix}"] = sum(matched_values)
                elif agg == "mean":
                    resolved[f"{value_column}_mean_{zonal_suffix}"] = sum(matched_values) / len(matched_values)
                elif agg == "min":
                    resolved[f"{value_column}_min_{zonal_suffix}"] = min(matched_values)
                elif agg == "max":
                    resolved[f"{value_column}_max_{zonal_suffix}"] = max(matched_values)
            rows.append(resolved)
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=zones.geometry_column, crs=zones.crs or self.crs)

    # ------------------------------------------------------------------
    # Tool 3: reclassify
    # ------------------------------------------------------------------
    def reclassify(
        self,
        value_column: str,
        breaks: dict[str, Any] | list[tuple[float, float, str]] | None = None,
        mapping: dict[Any, Any] | None = None,
        output_column: str | None = None,
        default_class: str = "unclassified",
    ) -> "GeoPromptFrame":
        self._require_column(value_column)
        if breaks is None and mapping is None:
            raise ValueError("either breaks or mapping must be provided")
        out_col = output_column or f"{value_column}_class"
        rows: list[Record] = []
        for row in self._rows:
            resolved = dict(row)
            val = row.get(value_column)
            if mapping is not None:
                resolved[out_col] = mapping.get(val, default_class)
            elif breaks is not None:
                if isinstance(breaks, dict):
                    resolved[out_col] = breaks.get(str(val), default_class)
                else:
                    classified = default_class
                    if val is not None:
                        numeric_val = float(val)
                        for low, high, label in breaks:
                            if low <= numeric_val < high:
                                classified = label
                                break
                    resolved[out_col] = classified
            rows.append(resolved)
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    # ------------------------------------------------------------------
    # Tool 4: resample
    # ------------------------------------------------------------------
    def resample(
        self,
        method: Literal["every_nth", "spatial_thin", "random"] = "every_nth",
        n: int = 2,
        min_distance: float | None = None,
        sample_size: int | None = None,
        random_seed: int = 0,
        distance_method: str = "euclidean",
    ) -> "GeoPromptFrame":
        if not self._rows:
            return GeoPromptFrame._from_internal_rows([], geometry_column=self.geometry_column, crs=self.crs)
        if method == "every_nth":
            if n <= 0:
                raise ValueError("n must be greater than zero")
            rows = [self._rows[i] for i in range(0, len(self._rows), n)]
        elif method == "random":
            count = sample_size if sample_size is not None else max(1, len(self._rows) // 2)
            count = min(count, len(self._rows))
            rng = random.Random(random_seed)
            indexes = rng.sample(range(len(self._rows)), count)
            rows = [self._rows[i] for i in sorted(indexes)]
        elif method == "spatial_thin":
            if min_distance is None or min_distance <= 0:
                raise ValueError("min_distance must be greater than zero for spatial_thin")
            centroids = self._centroids()
            selected: list[int] = []
            for i in range(len(self._rows)):
                too_close = False
                for j in selected:
                    if coordinate_distance(centroids[i], centroids[j], method=distance_method) < min_distance:
                        too_close = True
                        break
                if not too_close:
                    selected.append(i)
            rows = [self._rows[i] for i in selected]
        else:
            raise ValueError("method must be 'every_nth', 'spatial_thin', or 'random'")
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    # ------------------------------------------------------------------
    # Tool 5: raster_clip (bounds-based clip)
    # ------------------------------------------------------------------
    def raster_clip(
        self,
        min_x: float,
        min_y: float,
        max_x: float,
        max_y: float,
    ) -> "GeoPromptFrame":
        clip_bounds = (min_x, min_y, max_x, max_y)
        rows: list[Record] = []
        for row in self._rows:
            geom = row[self.geometry_column]
            geom_bounds = geometry_bounds(geom)
            if _bounds_intersect(geom_bounds, clip_bounds):
                rows.append(row)
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    # ------------------------------------------------------------------
    # Tool 6: mosaic
    # ------------------------------------------------------------------
    def mosaic(
        self,
        *others: "GeoPromptFrame",
        conflict_resolution: Literal["first", "last", "mean"] = "first",
        id_column: str = "site_id",
        mosaic_suffix: str = "mosaic",
    ) -> "GeoPromptFrame":
        all_rows: list[Record] = list(self._rows)
        for other in others:
            if self.crs and other.crs and self.crs != other.crs:
                raise ValueError("all frames must share the same CRS for mosaic")
            all_rows.extend(other._rows)
        if conflict_resolution == "first":
            seen_ids: set[str] = set()
            rows: list[Record] = []
            for row in all_rows:
                row_id = str(row.get(id_column, id(row)))
                if row_id not in seen_ids:
                    seen_ids.add(row_id)
                    resolved = dict(row)
                    resolved[f"source_{mosaic_suffix}"] = "keep"
                    rows.append(resolved)
        elif conflict_resolution == "last":
            seen_ids_map: dict[str, int] = {}
            for index, row in enumerate(all_rows):
                row_id = str(row.get(id_column, id(row)))
                seen_ids_map[row_id] = index
            rows = []
            for index in sorted(seen_ids_map.values()):
                resolved = dict(all_rows[index])
                resolved[f"source_{mosaic_suffix}"] = "keep"
                rows.append(resolved)
        else:
            rows = [dict(row) for row in all_rows]
            for row in rows:
                row[f"source_{mosaic_suffix}"] = "merged"
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    # ------------------------------------------------------------------
    # Tool 7: to_points
    # ------------------------------------------------------------------
    def to_points(self) -> "GeoPromptFrame":
        rows: list[Record] = []
        for row in self._rows:
            centroid = geometry_centroid(row[self.geometry_column])
            resolved = dict(row)
            resolved[self.geometry_column] = {"type": "Point", "coordinates": centroid}
            rows.append(resolved)
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    # ------------------------------------------------------------------
    # Tool 8: to_polygons
    # ------------------------------------------------------------------
    def to_polygons(self, buffer_distance: float = 0.001) -> "GeoPromptFrame":
        if buffer_distance <= 0:
            raise ValueError("buffer_distance must be greater than zero")
        rows: list[Record] = []
        for row in self._rows:
            geom = row[self.geometry_column]
            geom_type_value = geometry_type(geom)
            if geom_type_value == "Polygon":
                rows.append(dict(row))
            elif geom_type_value == "Point":
                cx, cy = geom["coordinates"]
                polygon = _rectangle_polygon(
                    cx - buffer_distance, cy - buffer_distance,
                    cx + buffer_distance, cy + buffer_distance,
                )
                resolved = dict(row)
                resolved[self.geometry_column] = polygon
                rows.append(resolved)
            elif geom_type_value == "LineString":
                coords = geometry_vertices(geom)
                min_x = min(c[0] for c in coords) - buffer_distance
                min_y = min(c[1] for c in coords) - buffer_distance
                max_x = max(c[0] for c in coords) + buffer_distance
                max_y = max(c[1] for c in coords) + buffer_distance
                polygon = _rectangle_polygon(min_x, min_y, max_x, max_y)
                resolved = dict(row)
                resolved[self.geometry_column] = polygon
                rows.append(resolved)
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    # ------------------------------------------------------------------
    # Tool 9: contours
    # ------------------------------------------------------------------
    def contours(
        self,
        value_column: str,
        intervals: Sequence[float] | None = None,
        interval_count: int = 5,
        grid_resolution: int = 20,
        distance_method: str = "euclidean",
        contour_suffix: str = "contour",
    ) -> "GeoPromptFrame":
        self._require_column(value_column)
        if not self._rows:
            return GeoPromptFrame._from_internal_rows([], geometry_column=self.geometry_column, crs=self.crs)
        centroids = self._centroids()
        values = [float(row[value_column]) for row in self._rows if row.get(value_column) is not None]
        if not values:
            return GeoPromptFrame._from_internal_rows([], geometry_column=self.geometry_column, crs=self.crs)
        b = self.bounds()
        if intervals is None:
            v_min, v_max = min(values), max(values)
            step = (v_max - v_min) / max(interval_count, 1)
            intervals = [v_min + step * i for i in range(1, interval_count)]
        dx = (b.max_x - b.min_x) / max(grid_resolution - 1, 1)
        dy = (b.max_y - b.min_y) / max(grid_resolution - 1, 1)
        grid: list[list[float]] = []
        for gy in range(grid_resolution):
            row_vals: list[float] = []
            py = b.min_y + gy * dy
            for gx in range(grid_resolution):
                px = b.min_x + gx * dx
                weight_sum = 0.0
                value_sum = 0.0
                for ci, centroid in enumerate(centroids):
                    d = coordinate_distance((px, py), centroid, method=distance_method)
                    w = 1.0 / max(d * d, 1e-12)
                    weight_sum += w
                    value_sum += w * float(self._rows[ci].get(value_column, 0) or 0)
                row_vals.append(value_sum / weight_sum if weight_sum > 0 else 0.0)
            grid.append(row_vals)
        rows: list[Record] = []
        contour_id = 0
        for level in intervals:
            segments: list[tuple[Coordinate, Coordinate]] = []
            for gy in range(grid_resolution - 1):
                for gx in range(grid_resolution - 1):
                    cell_values = [
                        grid[gy][gx], grid[gy][gx + 1],
                        grid[gy + 1][gx + 1], grid[gy + 1][gx],
                    ]
                    cell_coords = [
                        (b.min_x + gx * dx, b.min_y + gy * dy),
                        (b.min_x + (gx + 1) * dx, b.min_y + gy * dy),
                        (b.min_x + (gx + 1) * dx, b.min_y + (gy + 1) * dy),
                        (b.min_x + gx * dx, b.min_y + (gy + 1) * dy),
                    ]
                    edge_points = _marching_square_edges(cell_values, cell_coords, level)
                    for i in range(0, len(edge_points) - 1, 2):
                        segments.append((edge_points[i], edge_points[i + 1]))
            for seg_start, seg_end in segments:
                contour_id += 1
                rows.append({
                    f"contour_id_{contour_suffix}": f"contour-{contour_id:04d}",
                    f"level_{contour_suffix}": level,
                    self.geometry_column: {"type": "LineString", "coordinates": (seg_start, seg_end)},
                })
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    # ------------------------------------------------------------------
    # Tool 10: hillshade
    # ------------------------------------------------------------------
    def hillshade(
        self,
        elevation_column: str,
        azimuth: float = 315.0,
        altitude: float = 45.0,
        grid_resolution: int = 20,
        distance_method: str = "euclidean",
        hillshade_suffix: str = "hillshade",
    ) -> "GeoPromptFrame":
        self._require_column(elevation_column)
        if not self._rows:
            return GeoPromptFrame._from_internal_rows([], geometry_column=self.geometry_column, crs=self.crs)
        grid, b, dx, dy = self._idw_grid(elevation_column, grid_resolution, distance_method)
        azimuth_rad = math.radians(360.0 - azimuth + 90.0)
        altitude_rad = math.radians(altitude)
        rows: list[Record] = []
        cell_id = 0
        for gy in range(1, grid_resolution - 1):
            for gx in range(1, grid_resolution - 1):
                dzdx = (grid[gy][gx + 1] - grid[gy][gx - 1]) / (2.0 * max(dx, 1e-12))
                dzdy = (grid[gy + 1][gx] - grid[gy - 1][gx]) / (2.0 * max(dy, 1e-12))
                slope = math.atan(math.sqrt(dzdx * dzdx + dzdy * dzdy))
                aspect = math.atan2(-dzdy, dzdx)
                shade = max(0.0, math.cos(altitude_rad) * math.sin(slope) * math.cos(azimuth_rad - aspect) + math.sin(altitude_rad) * math.cos(slope))
                shade = min(1.0, shade)
                cx = b.min_x + gx * dx
                cy = b.min_y + gy * dy
                cell_id += 1
                rows.append({
                    f"cell_id_{hillshade_suffix}": f"hs-{cell_id:04d}",
                    f"value_{hillshade_suffix}": round(shade * 255.0),
                    f"shade_{hillshade_suffix}": shade,
                    self.geometry_column: {"type": "Point", "coordinates": (cx, cy)},
                })
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    # ------------------------------------------------------------------
    # Tool 11: slope_aspect
    # ------------------------------------------------------------------
    def slope_aspect(
        self,
        elevation_column: str,
        grid_resolution: int = 20,
        distance_method: str = "euclidean",
        slope_suffix: str = "terrain",
    ) -> "GeoPromptFrame":
        self._require_column(elevation_column)
        if not self._rows:
            return GeoPromptFrame._from_internal_rows([], geometry_column=self.geometry_column, crs=self.crs)
        grid, b, dx, dy = self._idw_grid(elevation_column, grid_resolution, distance_method)
        rows: list[Record] = []
        cell_id = 0
        for gy in range(1, grid_resolution - 1):
            for gx in range(1, grid_resolution - 1):
                dzdx = (grid[gy][gx + 1] - grid[gy][gx - 1]) / (2.0 * max(dx, 1e-12))
                dzdy = (grid[gy + 1][gx] - grid[gy - 1][gx]) / (2.0 * max(dy, 1e-12))
                slope_rad = math.atan(math.sqrt(dzdx * dzdx + dzdy * dzdy))
                slope_deg = math.degrees(slope_rad)
                aspect_rad = math.atan2(-dzdy, dzdx)
                aspect_deg = (math.degrees(aspect_rad) + 360.0) % 360.0
                cx = b.min_x + gx * dx
                cy = b.min_y + gy * dy
                cell_id += 1
                rows.append({
                    f"cell_id_{slope_suffix}": f"sa-{cell_id:04d}",
                    f"slope_degrees_{slope_suffix}": slope_deg,
                    f"slope_radians_{slope_suffix}": slope_rad,
                    f"aspect_degrees_{slope_suffix}": aspect_deg,
                    f"aspect_radians_{slope_suffix}": aspect_rad,
                    f"elevation_{slope_suffix}": grid[gy][gx],
                    self.geometry_column: {"type": "Point", "coordinates": (cx, cy)},
                })
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    # ------------------------------------------------------------------
    # Tool 12: idw_interpolation
    # ------------------------------------------------------------------
    def idw_interpolation(
        self,
        value_column: str,
        grid_resolution: int = 20,
        power: float = 2.0,
        distance_method: str = "euclidean",
        idw_suffix: str = "idw",
    ) -> "GeoPromptFrame":
        self._require_column(value_column)
        if power <= 0:
            raise ValueError("power must be greater than zero")
        if not self._rows:
            return GeoPromptFrame._from_internal_rows([], geometry_column=self.geometry_column, crs=self.crs)
        centroids = self._centroids()
        b = self.bounds()
        dx = (b.max_x - b.min_x) / max(grid_resolution - 1, 1)
        dy = (b.max_y - b.min_y) / max(grid_resolution - 1, 1)
        rows: list[Record] = []
        cell_id = 0
        for gy in range(grid_resolution):
            py = b.min_y + gy * dy
            for gx in range(grid_resolution):
                px = b.min_x + gx * dx
                weight_sum = 0.0
                value_sum = 0.0
                exact_match = None
                for ci, centroid in enumerate(centroids):
                    d = coordinate_distance((px, py), centroid, method=distance_method)
                    if d < 1e-12:
                        exact_match = float(self._rows[ci].get(value_column, 0) or 0)
                        break
                    w = 1.0 / (d ** power)
                    weight_sum += w
                    value_sum += w * float(self._rows[ci].get(value_column, 0) or 0)
                interpolated = exact_match if exact_match is not None else (value_sum / weight_sum if weight_sum > 0 else 0.0)
                cell_id += 1
                rows.append({
                    f"cell_id_{idw_suffix}": f"idw-{cell_id:04d}",
                    f"value_{idw_suffix}": interpolated,
                    f"grid_row_{idw_suffix}": gy,
                    f"grid_col_{idw_suffix}": gx,
                    self.geometry_column: {"type": "Point", "coordinates": (px, py)},
                })
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    # ------------------------------------------------------------------
    # Tool 13: kriging_surface (simple/ordinary kriging)
    # ------------------------------------------------------------------
    def kriging_surface(
        self,
        value_column: str,
        grid_resolution: int = 20,
        variogram_range: float | None = None,
        variogram_sill: float = 1.0,
        variogram_nugget: float = 0.0,
        variogram_model: str = "spherical",
        distance_method: str = "euclidean",
        kriging_suffix: str = "kriging",
    ) -> "GeoPromptFrame":
        self._require_column(value_column)
        if not self._rows:
            return GeoPromptFrame._from_internal_rows([], geometry_column=self.geometry_column, crs=self.crs)
        if variogram_sill <= 0.0:
            raise ValueError("variogram_sill must be greater than zero")
        if variogram_nugget < 0.0:
            raise ValueError("variogram_nugget must be zero or greater")
        if variogram_range is not None and variogram_range <= 0.0:
            raise ValueError("variogram_range must be greater than zero")
        normalized_variogram_model = variogram_model.replace("-", "_")
        if normalized_variogram_model not in {"spherical", "exponential", "gaussian", "hole_effect"}:
            raise ValueError("variogram_model must be 'spherical', 'exponential', 'gaussian', or 'hole_effect'")
        centroids = self._centroids()
        values = [float(row.get(value_column, 0) or 0) for row in self._rows]
        sample_count = len(centroids)
        b = self.bounds()
        extent = max(b.max_x - b.min_x, b.max_y - b.min_y, 1e-9)
        effective_range = variogram_range if variogram_range is not None else extent / 3.0
        sample_distances = _pairwise_distance_matrix(centroids, distance_method)
        kriging_matrix = [
            [
                _variogram_value(
                    normalized_variogram_model,
                    sample_distances[row_index][col_index],
                    effective_range,
                    variogram_sill,
                    variogram_nugget,
                )
                for col_index in range(sample_count)
            ]
            + [1.0]
            for row_index in range(sample_count)
        ]
        kriging_matrix.append([1.0] * sample_count + [0.0])
        inverse_matrix = _invert_matrix(kriging_matrix)
        if inverse_matrix is None:
            stabilized_matrix = [list(row) for row in kriging_matrix]
            diagonal_jitter = max(variogram_sill, 1.0) * 1e-9
            for index in range(sample_count):
                stabilized_matrix[index][index] += diagonal_jitter
            inverse_matrix = _invert_matrix(stabilized_matrix)
            if inverse_matrix is not None:
                kriging_matrix = stabilized_matrix
        dx = (b.max_x - b.min_x) / max(grid_resolution - 1, 1)
        dy = (b.max_y - b.min_y) / max(grid_resolution - 1, 1)
        rows: list[Record] = []
        cell_id = 0
        for gy in range(grid_resolution):
            py = b.min_y + gy * dy
            for gx in range(grid_resolution):
                px = b.min_x + gx * dx
                query_distances = [
                    coordinate_distance((px, py), centroid, method=distance_method)
                    for centroid in centroids
                ]
                exact_index = next(
                    (
                        index
                        for index, distance_value in enumerate(query_distances)
                        if distance_value <= 1e-12 and variogram_nugget <= 0.0
                    ),
                    None,
                )
                if exact_index is not None:
                    predicted = values[exact_index]
                    variance = 0.0
                else:
                    rhs = [
                        _variogram_value(
                            normalized_variogram_model,
                            distance_value,
                            effective_range,
                            variogram_sill,
                            variogram_nugget,
                            include_nugget_at_zero=variogram_nugget > 0.0,
                        )
                        for distance_value in query_distances
                    ] + [1.0]
                    solution = _matrix_vector_product(inverse_matrix, rhs) if inverse_matrix is not None else _solve_linear_system(kriging_matrix, rhs)
                    if solution is None:
                        weights = [max(0.0, variogram_sill - rhs[index]) for index in range(sample_count)]
                        weight_sum = sum(weights)
                        if weight_sum > 0.0:
                            predicted = sum(weight * value for weight, value in zip(weights, values, strict=True)) / weight_sum
                            variance = variogram_sill - sum(weight * weight for weight in weights) / (weight_sum * weight_sum) * variogram_sill
                        else:
                            predicted = sum(values) / len(values) if values else 0.0
                            variance = variogram_sill
                    else:
                        kriging_weights = solution[:sample_count]
                        lagrange_multiplier = float(solution[-1])
                        predicted = sum(weight * value for weight, value in zip(kriging_weights, values, strict=True))
                        variance = sum(weight * rhs[index] for index, weight in enumerate(kriging_weights)) + lagrange_multiplier
                cell_id += 1
                rows.append({
                    f"cell_id_{kriging_suffix}": f"krig-{cell_id:04d}",
                    f"value_{kriging_suffix}": predicted,
                    f"variance_{kriging_suffix}": max(0.0, variance),
                    f"method_{kriging_suffix}": "ordinary_kriging",
                    f"variogram_model_{kriging_suffix}": normalized_variogram_model,
                    f"grid_row_{kriging_suffix}": gy,
                    f"grid_col_{kriging_suffix}": gx,
                    self.geometry_column: {"type": "Point", "coordinates": (px, py)},
                })
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    # ------------------------------------------------------------------
    # Tool 14: thiessen_polygons (Voronoi)
    # ------------------------------------------------------------------
    def thiessen_polygons(
        self,
        id_column: str = "site_id",
        grid_resolution: int = 50,
        distance_method: str = "euclidean",
        voronoi_suffix: str = "voronoi",
    ) -> "GeoPromptFrame":
        if not self._rows:
            return GeoPromptFrame._from_internal_rows([], geometry_column=self.geometry_column, crs=self.crs)
        centroids = self._centroids()
        b = self.bounds()
        margin = max(b.max_x - b.min_x, b.max_y - b.min_y, 1e-9) * 0.1
        ext_min_x = b.min_x - margin
        ext_min_y = b.min_y - margin
        ext_max_x = b.max_x + margin
        ext_max_y = b.max_y + margin
        try:
            shapely_geometry = importlib.import_module("shapely.geometry")
            shapely_ops = importlib.import_module("shapely.ops")
            envelope = shapely_geometry.box(ext_min_x, ext_min_y, ext_max_x, ext_max_y)
            voronoi = shapely_ops.voronoi_diagram(
                shapely_geometry.MultiPoint(centroids),
                envelope=envelope,
                tolerance=0.0,
                edges=False,
            )
            candidate_cells = [
                geometry
                for geometry in getattr(voronoi, "geoms", [voronoi])
                if not geometry.is_empty and geometry.geom_type == "Polygon"
            ]
            rows: list[Record] = []
            assigned_cells: dict[str, Any] = {}
            for row, centroid in zip(self._rows, centroids, strict=True):
                centroid_key = _coordinate_key(centroid)
                if centroid_key not in assigned_cells:
                    point = shapely_geometry.Point(centroid)
                    matched_cell = next(
                        (
                            cell
                            for cell in candidate_cells
                            if cell.covers(point) or cell.buffer(1e-12).covers(point)
                        ),
                        None,
                    )
                    if matched_cell is None:
                        matched_cell = min(candidate_cells, key=lambda cell: float(cell.distance(point)))
                    assigned_cells[centroid_key] = matched_cell.intersection(envelope)
                geometries = geometry_from_shapely(assigned_cells[centroid_key])
                if not geometries:
                    continue
                polygon = geometries[0]
                area_value = geometry_area(polygon)
                resolved = dict(row)
                resolved[self.geometry_column] = polygon
                resolved[f"cell_count_{voronoi_suffix}"] = 1
                resolved[f"area_approx_{voronoi_suffix}"] = area_value
                resolved[f"area_{voronoi_suffix}"] = area_value
                resolved[f"method_{voronoi_suffix}"] = "shapely_exact"
                rows.append(resolved)
            if len(rows) == len(self._rows):
                return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)
        except ImportError:
            pass

        dx = (ext_max_x - ext_min_x) / max(grid_resolution - 1, 1)
        dy = (ext_max_y - ext_min_y) / max(grid_resolution - 1, 1)
        use_euclidean = distance_method == "euclidean"
        cell_owner: list[list[int]] = []
        for gy in range(grid_resolution):
            py = ext_min_y + gy * dy
            row_owners: list[int] = []
            for gx in range(grid_resolution):
                px = ext_min_x + gx * dx
                best_idx = 0
                best_dist = float("inf")
                for ci, centroid in enumerate(centroids):
                    if use_euclidean:
                        delta_x = px - centroid[0]
                        delta_y = py - centroid[1]
                        d = delta_x * delta_x + delta_y * delta_y
                    else:
                        d = coordinate_distance((px, py), centroid, method=distance_method)
                    if d < best_dist:
                        best_dist = d
                        best_idx = ci
                row_owners.append(best_idx)
            cell_owner.append(row_owners)
        owner_cells: dict[int, list[tuple[int, int]]] = {}
        for gy in range(grid_resolution):
            for gx in range(grid_resolution):
                owner_cells.setdefault(cell_owner[gy][gx], []).append((gx, gy))
        rows: list[Record] = []
        for owner_idx, cells in owner_cells.items():
            xs = [ext_min_x + gx * dx for gx, _ in cells]
            ys = [ext_min_y + gy * dy for _, gy in cells]
            poly_min_x, poly_max_x = min(xs), max(xs) + dx
            poly_min_y, poly_max_y = min(ys), max(ys) + dy
            polygon = _rectangle_polygon(poly_min_x, poly_min_y, poly_max_x, poly_max_y)
            resolved = dict(self._rows[owner_idx])
            resolved[self.geometry_column] = polygon
            resolved[f"cell_count_{voronoi_suffix}"] = len(cells)
            resolved[f"area_approx_{voronoi_suffix}"] = len(cells) * dx * dy
            resolved[f"area_{voronoi_suffix}"] = geometry_area(polygon)
            resolved[f"method_{voronoi_suffix}"] = "grid_approximation"
            rows.append(resolved)
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    # ------------------------------------------------------------------
    # Tool 15: spatial_weights_matrix
    # ------------------------------------------------------------------
    def spatial_weights_matrix(
        self,
        id_column: str = "site_id",
        mode: SpatialLagMode = "k_nearest",
        k: int = 4,
        max_distance: float | None = None,
        distance_method: str = "euclidean",
        weight_mode: SpatialLagWeightMode = "binary",
        include_self: bool = False,
    ) -> dict[str, Any]:
        self._require_column(id_column)
        centroids = self._centroids()
        ids = [str(row[id_column]) for row in self._rows]
        distance_matrix = _pairwise_distance_matrix(centroids, distance_method)
        weights: dict[str, dict[str, float]] = {}
        for i, origin_id in enumerate(ids):
            neighbors: dict[str, float] = {}
            candidates: list[tuple[int, float]] = []
            for j in range(len(self._rows)):
                if not include_self and i == j:
                    continue
                d = distance_matrix[i][j]
                if mode == "distance_band" and max_distance is not None and d > max_distance:
                    continue
                candidates.append((j, d))
            if mode == "k_nearest":
                candidates = nsmallest(k, candidates, key=lambda x: x[1])
            for j, d in candidates:
                if weight_mode == "binary":
                    neighbors[ids[j]] = 1.0
                else:
                    neighbors[ids[j]] = 1.0 / max(d, 1e-12)
            weights[origin_id] = neighbors
        return {
            "ids": ids,
            "weights": weights,
            "mode": mode,
            "k": k,
            "max_distance": max_distance,
            "weight_mode": weight_mode,
            "n": len(ids),
        }

    # ------------------------------------------------------------------
    # Tool 16: hotspot_getis_ord (Gi* statistic)
    # ------------------------------------------------------------------
    def hotspot_getis_ord(
        self,
        value_column: str,
        id_column: str = "site_id",
        mode: SpatialLagMode = "distance_band",
        k: int = 4,
        max_distance: float | None = None,
        distance_method: str = "euclidean",
        include_self: bool = True,
        getis_suffix: str = "getis",
    ) -> "GeoPromptFrame":
        self._require_column(value_column)
        self._require_column(id_column)
        if mode == "distance_band" and max_distance is None:
            raise ValueError("max_distance is required when mode='distance_band'")
        n = len(self._rows)
        if n == 0:
            return GeoPromptFrame._from_internal_rows([], geometry_column=self.geometry_column, crs=self.crs)
        centroids = self._centroids()
        distance_matrix = _pairwise_distance_matrix(centroids, distance_method)
        values = [float(row[value_column]) for row in self._rows]
        geometry_index = self.spatial_index(mode="geometry") if mode == "intersects" and self._rows else None
        mean_val = sum(values) / n
        s = math.sqrt(sum(v * v for v in values) / n - mean_val * mean_val) if n > 1 else 1.0
        if s < 1e-12:
            s = 1.0
        neighbor_indexes: list[list[int]] = []
        for i in range(n):
            candidates: list[tuple[int, float]] = []
            if mode == "intersects" and geometry_index is not None:
                candidate_indexes = geometry_index.query(geometry_bounds(self._rows[i][self.geometry_column]))
            else:
                candidate_indexes = list(range(n))
            for j in candidate_indexes:
                if i == j:
                    continue
                if mode == "intersects":
                    if not geometry_intersects(self._rows[i][self.geometry_column], self._rows[j][self.geometry_column]):
                        continue
                    distance_value = distance_matrix[i][j]
                else:
                    distance_value = distance_matrix[i][j]
                    if mode == "distance_band" and max_distance is not None and distance_value > max_distance:
                        continue
                candidates.append((j, distance_value))
            if mode == "k_nearest":
                candidates = nsmallest(
                    k,
                    candidates,
                    key=lambda item: (float(item[1]), _row_sort_key(self._rows[item[0]])),
                )
            else:
                candidates.sort(key=lambda item: (float(item[1]), _row_sort_key(self._rows[item[0]])))
            neighbor_indexes.append([index for index, _distance_value in candidates])

        reference_statistics = _reference_getis_ord_statistics(values, neighbor_indexes, include_self=include_self)
        rows: list[Record] = []
        for i in range(n):
            w_sum = 0.0
            wx_sum = 0.0
            w2_sum = 0.0
            candidates = list(neighbor_indexes[i])
            for j in candidates:
                w = 1.0
                w_sum += w
                wx_sum += w * values[j]
                w2_sum += w * w
            if reference_statistics is not None:
                z_score, p_value = reference_statistics[i]
            else:
                if include_self:
                    w_sum += 1.0
                    wx_sum += values[i]
                    w2_sum += 1.0
                if w_sum > 0 and n > 1:
                    numerator = wx_sum - mean_val * w_sum
                    denominator = s * math.sqrt((n * w2_sum - w_sum * w_sum) / max(n - 1, 1))
                    z_score = numerator / max(denominator, 1e-12)
                else:
                    z_score = 0.0
                p_value = 2.0 * (1.0 - _normal_cdf(abs(z_score)))
            resolved = dict(self._rows[i])
            resolved[f"gi_star_{getis_suffix}"] = z_score
            resolved[f"p_value_{getis_suffix}"] = p_value
            resolved[f"neighbor_count_{getis_suffix}"] = len(candidates) + (1 if include_self else 0)
            resolved[f"significant_{getis_suffix}"] = p_value <= 0.05
            resolved[f"implementation_{getis_suffix}"] = "pysal" if reference_statistics is not None else "analytic"
            if p_value <= 0.05 and z_score > 0.0:
                resolved[f"classification_{getis_suffix}"] = "hotspot"
            elif p_value <= 0.05 and z_score < 0.0:
                resolved[f"classification_{getis_suffix}"] = "coldspot"
            else:
                resolved[f"classification_{getis_suffix}"] = "not_significant"
            rows.append(resolved)
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    # ------------------------------------------------------------------
    # Tool 17: local_outlier_factor_spatial
    # ------------------------------------------------------------------
    def local_outlier_factor_spatial(
        self,
        value_column: str | None = None,
        id_column: str = "site_id",
        k: int = 4,
        distance_method: str = "euclidean",
        lof_suffix: str = "lof",
    ) -> "GeoPromptFrame":
        self._require_column(id_column)
        if k <= 0:
            raise ValueError("k must be greater than zero")
        n = len(self._rows)
        if n == 0:
            return GeoPromptFrame._from_internal_rows([], geometry_column=self.geometry_column, crs=self.crs)
        centroids = self._centroids()
        distance_matrix = _pairwise_distance_matrix(centroids, distance_method)
        k_actual = min(k, n - 1)
        if k_actual <= 0:
            rows = [dict(row) | {f"lof_{lof_suffix}": 1.0, f"outlier_{lof_suffix}": False} for row in self._rows]
            return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)
        knn: list[list[tuple[int, float]]] = []
        k_distances: list[float] = []
        for i in range(n):
            dists = []
            for j in range(n):
                if i == j:
                    continue
                d = distance_matrix[i][j]
                if value_column is not None:
                    vi = float(self._rows[i].get(value_column, 0) or 0)
                    vj = float(self._rows[j].get(value_column, 0) or 0)
                    d = math.sqrt(d * d + (vi - vj) * (vi - vj))
                dists.append((j, d))
            neighbors = nsmallest(k_actual, dists, key=lambda x: x[1])
            knn.append(neighbors)
            k_distances.append(neighbors[-1][1] if neighbors else 0.0)
        lrd: list[float] = []
        for i in range(n):
            reach_sum = sum(max(k_distances[j], d) for j, d in knn[i])
            lrd.append(len(knn[i]) / max(reach_sum, 1e-12))
        rows: list[Record] = []
        for i in range(n):
            if lrd[i] < 1e-12:
                lof_value = 1.0
            else:
                neighbor_lrd_sum = sum(lrd[j] for j, _ in knn[i])
                lof_value = (neighbor_lrd_sum / len(knn[i])) / lrd[i] if knn[i] else 1.0
            resolved = dict(self._rows[i])
            resolved[f"lof_{lof_suffix}"] = lof_value
            resolved[f"k_distance_{lof_suffix}"] = k_distances[i]
            resolved[f"lrd_{lof_suffix}"] = lrd[i]
            resolved[f"outlier_{lof_suffix}"] = lof_value > 1.5
            rows.append(resolved)
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    # ------------------------------------------------------------------
    # Tool 18: kernel_density
    # ------------------------------------------------------------------
    def kernel_density(
        self,
        bandwidth: float | None = None,
        weight_column: str | None = None,
        grid_resolution: int = 20,
        distance_method: str = "euclidean",
        kernel_suffix: str = "kde",
    ) -> "GeoPromptFrame":
        if not self._rows:
            return GeoPromptFrame._from_internal_rows([], geometry_column=self.geometry_column, crs=self.crs)
        centroids = self._centroids()
        b = self.bounds()
        extent = max(b.max_x - b.min_x, b.max_y - b.min_y, 1e-9)
        h = bandwidth if bandwidth is not None else extent / math.sqrt(len(self._rows))
        if h <= 0:
            raise ValueError("bandwidth must be greater than zero")
        dx = (b.max_x - b.min_x) / max(grid_resolution - 1, 1)
        dy = (b.max_y - b.min_y) / max(grid_resolution - 1, 1)
        weights_list = [float(row[weight_column]) if weight_column and row.get(weight_column) is not None else 1.0 for row in self._rows]
        use_euclidean = distance_method == "euclidean"
        rows: list[Record] = []
        cell_id = 0
        for gy in range(grid_resolution):
            py = b.min_y + gy * dy
            for gx in range(grid_resolution):
                px = b.min_x + gx * dx
                density = 0.0
                for ci, centroid in enumerate(centroids):
                    if use_euclidean:
                        d = math.hypot(px - centroid[0], py - centroid[1])
                    else:
                        d = coordinate_distance((px, py), centroid, method=distance_method)
                    u = d / h
                    if u < 1.0:
                        k_val = (3.0 / math.pi) * (1.0 - u * u) ** 2
                        density += weights_list[ci] * k_val / (h * h)
                cell_id += 1
                rows.append({
                    f"cell_id_{kernel_suffix}": f"kde-{cell_id:04d}",
                    f"density_{kernel_suffix}": density,
                    self.geometry_column: {"type": "Point", "coordinates": (px, py)},
                })
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    # ------------------------------------------------------------------
    # Tool 19: standard_deviational_ellipse
    # ------------------------------------------------------------------
    def standard_deviational_ellipse(
        self,
        weight_column: str | None = None,
        id_column: str = "site_id",
        ellipse_suffix: str = "sde",
    ) -> "GeoPromptFrame":
        if not self._rows:
            return GeoPromptFrame._from_internal_rows([], geometry_column=self.geometry_column, crs=self.crs)
        centroids = self._centroids()
        weights = [float(row[weight_column]) if weight_column and row.get(weight_column) is not None else 1.0 for row in self._rows]
        w_sum = sum(weights)
        if w_sum <= 0:
            return GeoPromptFrame._from_internal_rows([], geometry_column=self.geometry_column, crs=self.crs)
        cx = sum(w * c[0] for w, c in zip(weights, centroids)) / w_sum
        cy = sum(w * c[1] for w, c in zip(weights, centroids)) / w_sum
        dx_vals = [c[0] - cx for c in centroids]
        dy_vals = [c[1] - cy for c in centroids]
        sum_dx2 = sum(w * dx * dx for w, dx in zip(weights, dx_vals))
        sum_dy2 = sum(w * dy * dy for w, dy in zip(weights, dy_vals))
        sum_dxdy = sum(w * dx * dy for w, dx, dy in zip(weights, dx_vals, dy_vals))
        a = sum_dx2 - sum_dy2
        b_val = math.sqrt(a * a + 4.0 * sum_dxdy * sum_dxdy)
        theta = math.atan2(2.0 * sum_dxdy, a) / 2.0
        cos_t, sin_t = math.cos(theta), math.sin(theta)
        sigma_x = math.sqrt(sum(w * (dx * cos_t + dy * sin_t) ** 2 for w, dx, dy in zip(weights, dx_vals, dy_vals)) / w_sum)
        sigma_y = math.sqrt(sum(w * (dx * sin_t - dy * cos_t) ** 2 for w, dx, dy in zip(weights, dx_vals, dy_vals)) / w_sum)
        n_pts = 32
        ellipse_coords: list[Coordinate] = []
        for i in range(n_pts + 1):
            angle = 2.0 * math.pi * i / n_pts
            ex = sigma_x * math.cos(angle)
            ey = sigma_y * math.sin(angle)
            rx = cx + ex * cos_t - ey * sin_t
            ry = cy + ex * sin_t + ey * cos_t
            ellipse_coords.append((rx, ry))
        ellipse_geom: Geometry = {"type": "Polygon", "coordinates": tuple(ellipse_coords)}
        rows: list[Record] = [{
            f"center_x_{ellipse_suffix}": cx,
            f"center_y_{ellipse_suffix}": cy,
            f"sigma_x_{ellipse_suffix}": sigma_x,
            f"sigma_y_{ellipse_suffix}": sigma_y,
            f"rotation_degrees_{ellipse_suffix}": math.degrees(theta),
            f"feature_count_{ellipse_suffix}": len(self._rows),
            self.geometry_column: ellipse_geom,
        }]
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    # ------------------------------------------------------------------
    # Tool 20: center_of_minimum_distance (spatial median)
    # ------------------------------------------------------------------
    def center_of_minimum_distance(
        self,
        weight_column: str | None = None,
        max_iterations: int = 100,
        tolerance: float = 1e-8,
        distance_method: str = "euclidean",
        cmd_suffix: str = "cmd",
    ) -> "GeoPromptFrame":
        if not self._rows:
            return GeoPromptFrame._from_internal_rows([], geometry_column=self.geometry_column, crs=self.crs)
        centroids = self._centroids()
        weights = [float(row[weight_column]) if weight_column and row.get(weight_column) is not None else 1.0 for row in self._rows]
        w_sum = sum(weights)
        cx = sum(w * c[0] for w, c in zip(weights, centroids)) / max(w_sum, 1e-12)
        cy = sum(w * c[1] for w, c in zip(weights, centroids)) / max(w_sum, 1e-12)
        for iteration in range(max_iterations):
            wx_sum = 0.0
            wy_sum = 0.0
            denom = 0.0
            for ci, centroid in enumerate(centroids):
                d = coordinate_distance((cx, cy), centroid, method=distance_method)
                if d < 1e-12:
                    continue
                w = weights[ci] / d
                wx_sum += w * centroid[0]
                wy_sum += w * centroid[1]
                denom += w
            if denom < 1e-12:
                break
            new_cx = wx_sum / denom
            new_cy = wy_sum / denom
            if abs(new_cx - cx) + abs(new_cy - cy) < tolerance:
                cx, cy = new_cx, new_cy
                break
            cx, cy = new_cx, new_cy
        total_dist = sum(
            weights[ci] * coordinate_distance((cx, cy), centroids[ci], method=distance_method)
            for ci in range(len(centroids))
        )
        rows: list[Record] = [{
            f"center_x_{cmd_suffix}": cx,
            f"center_y_{cmd_suffix}": cy,
            f"total_weighted_distance_{cmd_suffix}": total_dist,
            f"feature_count_{cmd_suffix}": len(self._rows),
            f"iterations_{cmd_suffix}": min(iteration + 1 if 'iteration' in dir() else max_iterations, max_iterations),
            self.geometry_column: {"type": "Point", "coordinates": (cx, cy)},
        }]
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    # ------------------------------------------------------------------
    # Tool 21: spatial_regression (OLS with spatial diagnostics)
    # ------------------------------------------------------------------
    def spatial_regression(
        self,
        dependent_column: str,
        independent_columns: Sequence[str],
        id_column: str = "site_id",
        k_neighbors: int = 4,
        distance_method: str = "euclidean",
        regression_suffix: str = "reg",
    ) -> "GeoPromptFrame":
        self._require_column(dependent_column)
        for col in independent_columns:
            self._require_column(col)
        n = len(self._rows)
        if n == 0:
            return GeoPromptFrame._from_internal_rows([], geometry_column=self.geometry_column, crs=self.crs)
        p = len(independent_columns) + 1
        y_vals = [float(row[dependent_column]) for row in self._rows]
        x_matrix = [[1.0] + [float(row.get(col, 0) or 0) for col in independent_columns] for row in self._rows]
        xtx_inverse: list[list[float]] | None = None
        x_pseudoinverse = _matrix_pseudoinverse(x_matrix)
        effective_rank = _matrix_rank(x_matrix)
        if x_pseudoinverse is not None:
            coefficients = _matrix_vector_product(x_pseudoinverse, y_vals)
            xtx_inverse = _matrix_product(x_pseudoinverse, _transpose_matrix(x_pseudoinverse))
        else:
            xtx = [[sum(x_matrix[i][a] * x_matrix[i][b] for i in range(n)) for b in range(p)] for a in range(p)]
            xty = [sum(x_matrix[i][a] * y_vals[i] for i in range(n)) for a in range(p)]
            coefficients = _solve_linear_system(xtx, xty)
            xtx_inverse = _invert_matrix(xtx)
            if coefficients is None or xtx_inverse is None:
                xtx_pseudoinverse = _matrix_pseudoinverse(xtx)
                if xtx_pseudoinverse is not None:
                    coefficients = _matrix_vector_product(xtx_pseudoinverse, xty)
                    xtx_inverse = xtx_pseudoinverse
                elif coefficients is None:
                    coefficients = _solve_linear_system_with_regularization(xtx, xty)
                    xtx_inverse = _invert_matrix_with_regularization(xtx)
        if coefficients is None:
            coefficients = [0.0] * p
        predicted = _matrix_vector_product(x_matrix, coefficients)
        residuals = [y_vals[i] - predicted[i] for i in range(n)]
        y_mean = sum(y_vals) / n
        ss_res = sum(r * r for r in residuals)
        ss_tot = sum((y - y_mean) ** 2 for y in y_vals)
        if ss_tot <= 1e-12:
            r_squared = float("-inf")
            adj_r_squared = float("-inf")
        else:
            r_squared = 1.0 - ss_res / ss_tot
            adj_r_squared = 1.0 - (1.0 - r_squared) * (n - 1) / max(n - effective_rank, 1) if n > effective_rank else r_squared
        degrees_of_freedom = max(n - effective_rank, 0)
        sigma2 = ss_res / degrees_of_freedom if degrees_of_freedom > 0 else 0.0
        rmse = math.sqrt(ss_res / n) if n > 0 else 0.0
        coefficient_standard_errors: list[float | None]
        coefficient_t_statistics: list[float | None]
        coefficient_p_values: list[float | None]
        if xtx_inverse is None:
            coefficient_standard_errors = [None] * p
            coefficient_t_statistics = [None] * p
            coefficient_p_values = [None] * p
        else:
            coefficient_standard_errors = []
            coefficient_t_statistics = []
            coefficient_p_values = []
            for index in range(p):
                variance = max(xtx_inverse[index][index] * sigma2, 0.0)
                standard_error = math.sqrt(variance)
                coefficient_standard_errors.append(standard_error)
                coefficient = coefficients[index]
                if standard_error <= 0.0:
                    t_statistic = math.inf if abs(coefficient) > 1e-12 else 0.0
                    p_value = 0.0 if math.isinf(t_statistic) else 1.0
                else:
                    t_statistic = coefficient / standard_error
                    p_value = _two_sided_t_probability(abs(t_statistic), degrees_of_freedom)
                coefficient_t_statistics.append(t_statistic)
                coefficient_p_values.append(min(max(p_value, 0.0), 1.0))
        centroids = self._centroids()
        distance_matrix = _pairwise_distance_matrix(centroids, distance_method)
        moran_residuals = _moran_on_residuals(residuals, distance_matrix, k_neighbors)
        rows: list[Record] = []
        for i in range(n):
            resolved = dict(self._rows[i])
            resolved[f"predicted_{regression_suffix}"] = predicted[i]
            resolved[f"residual_{regression_suffix}"] = residuals[i]
            resolved[f"r_squared_{regression_suffix}"] = r_squared
            resolved[f"adj_r_squared_{regression_suffix}"] = adj_r_squared
            resolved[f"rmse_{regression_suffix}"] = rmse
            resolved[f"sigma2_{regression_suffix}"] = sigma2
            resolved[f"dof_{regression_suffix}"] = degrees_of_freedom
            resolved[f"coefficients_{regression_suffix}"] = coefficients
            resolved[f"coefficient_standard_errors_{regression_suffix}"] = coefficient_standard_errors
            resolved[f"coefficient_t_statistics_{regression_suffix}"] = coefficient_t_statistics
            resolved[f"coefficient_p_values_{regression_suffix}"] = coefficient_p_values
            resolved[f"intercept_{regression_suffix}"] = coefficients[0] if coefficients else None
            resolved[f"intercept_standard_error_{regression_suffix}"] = coefficient_standard_errors[0] if coefficient_standard_errors else None
            resolved[f"intercept_t_statistic_{regression_suffix}"] = coefficient_t_statistics[0] if coefficient_t_statistics else None
            resolved[f"intercept_p_value_{regression_suffix}"] = coefficient_p_values[0] if coefficient_p_values else None
            for coefficient_index, column_name in enumerate(independent_columns, start=1):
                resolved[f"coeff_{column_name}_{regression_suffix}"] = coefficients[coefficient_index] if coefficient_index < len(coefficients) else None
                resolved[f"std_err_{column_name}_{regression_suffix}"] = coefficient_standard_errors[coefficient_index] if coefficient_index < len(coefficient_standard_errors) else None
                resolved[f"t_stat_{column_name}_{regression_suffix}"] = coefficient_t_statistics[coefficient_index] if coefficient_index < len(coefficient_t_statistics) else None
                resolved[f"p_value_{column_name}_{regression_suffix}"] = coefficient_p_values[coefficient_index] if coefficient_index < len(coefficient_p_values) else None
            resolved[f"moran_residual_{regression_suffix}"] = moran_residuals
            rows.append(resolved)
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    # ------------------------------------------------------------------
    # Tool 22: geographically_weighted_summary
    # ------------------------------------------------------------------
    def geographically_weighted_summary(
        self,
        dependent_column: str,
        independent_columns: Sequence[str],
        bandwidth: float | None = None,
        distance_method: str = "euclidean",
        gwr_suffix: str = "gwr",
    ) -> "GeoPromptFrame":
        self._require_column(dependent_column)
        for col in independent_columns:
            self._require_column(col)
        n = len(self._rows)
        if n == 0:
            return GeoPromptFrame._from_internal_rows([], geometry_column=self.geometry_column, crs=self.crs)
        centroids = self._centroids()
        distance_matrix = _pairwise_distance_matrix(centroids, distance_method)
        b = self.bounds()
        extent = max(b.max_x - b.min_x, b.max_y - b.min_y, 1e-9)
        h = bandwidth if bandwidth is not None else extent / 3.0
        p = len(independent_columns) + 1
        y_vals = [float(row[dependent_column]) for row in self._rows]
        x_matrix = [[1.0] + [float(row.get(col, 0) or 0) for col in independent_columns] for row in self._rows]
        rows: list[Record] = []
        for i in range(n):
            local_weights = []
            for j in range(n):
                d = distance_matrix[i][j]
                u = d / max(h, 1e-12)
                w = math.exp(-0.5 * u * u) if u < 3.0 else 0.0
                local_weights.append(w)
            wxtx = [[sum(local_weights[k_idx] * x_matrix[k_idx][a] * x_matrix[k_idx][b] for k_idx in range(n)) for b in range(p)] for a in range(p)]
            wxty = [sum(local_weights[k_idx] * x_matrix[k_idx][a] * y_vals[k_idx] for k_idx in range(n)) for a in range(p)]
            local_coefficients = _solve_linear_system(wxtx, wxty)
            if local_coefficients is None:
                local_coefficients = [0.0] * p
            local_predicted = sum(local_coefficients[j] * x_matrix[i][j] for j in range(p))
            local_residual = y_vals[i] - local_predicted
            resolved = dict(self._rows[i])
            resolved[f"predicted_{gwr_suffix}"] = local_predicted
            resolved[f"residual_{gwr_suffix}"] = local_residual
            resolved[f"local_r_squared_{gwr_suffix}"] = None
            resolved[f"intercept_{gwr_suffix}"] = local_coefficients[0]
            for ci, col in enumerate(independent_columns):
                resolved[f"coeff_{col}_{gwr_suffix}"] = local_coefficients[ci + 1]
            rows.append(resolved)
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    def weighted_local_summary(
        self,
        dependent_column: str,
        independent_columns: Sequence[str],
        bandwidth: float | None = None,
        distance_method: str = "euclidean",
        summary_suffix: str = "local",
    ) -> "GeoPromptFrame":
        return self.geographically_weighted_summary(
            dependent_column=dependent_column,
            independent_columns=independent_columns,
            bandwidth=bandwidth,
            distance_method=distance_method,
            gwr_suffix=summary_suffix,
        )

    # ------------------------------------------------------------------
    # Tool 23: join_by_largest_overlap
    # ------------------------------------------------------------------
    def join_by_largest_overlap(
        self,
        other: "GeoPromptFrame",
        left_id_column: str = "site_id",
        right_id_column: str = "site_id",
        include_diagnostics: bool = False,
        overlap_suffix: str = "overlap",
    ) -> "GeoPromptFrame":
        if self.crs and other.crs and self.crs != other.crs:
            raise ValueError("frames must share the same CRS")
        left_geoms = [row[self.geometry_column] for row in self._rows]
        right_geoms = [row[other.geometry_column] for row in other._rows]
        rows: list[Record] = []
        for left_idx, left_row in enumerate(self._rows):
            best_overlap = 0.0
            best_right_idx: int | None = None
            for right_idx in range(len(other._rows)):
                overlap = _geometry_overlap_size(left_geoms[left_idx], right_geoms[right_idx])
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_right_idx = right_idx
            resolved = dict(left_row)
            if best_right_idx is not None:
                for key, value in other._rows[best_right_idx].items():
                    if key != other.geometry_column:
                        resolved[f"{key}_{overlap_suffix}"] = value
                resolved[f"overlap_area_{overlap_suffix}"] = best_overlap
            else:
                resolved[f"overlap_area_{overlap_suffix}"] = 0.0
            if include_diagnostics:
                resolved[f"candidate_count_{overlap_suffix}"] = len(other._rows)
            rows.append(resolved)
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    # ------------------------------------------------------------------
    # Tool 24: erase
    # ------------------------------------------------------------------
    def erase(self, mask: "GeoPromptFrame") -> "GeoPromptFrame":
        if self.crs and mask.crs and self.crs != mask.crs:
            raise ValueError("frames must share the same CRS")
        from .overlay import clip_geometries as _clip, geometry_to_shapely, geometry_from_shapely, _load_shapely
        _, _, unary_union, _ = _load_shapely()
        mask_geoms = [row[mask.geometry_column] for row in mask._rows]
        if not mask_geoms:
            return GeoPromptFrame._from_internal_rows([dict(r) for r in self._rows], geometry_column=self.geometry_column, crs=self.crs)
        mask_shape = unary_union([geometry_to_shapely(g) for g in mask_geoms])
        rows: list[Record] = []
        for row in self._rows:
            source_shape = geometry_to_shapely(row[self.geometry_column])
            diff = source_shape.difference(mask_shape)
            result_geoms = geometry_from_shapely(diff)
            for geom in result_geoms:
                resolved = dict(row)
                resolved[self.geometry_column] = geom
                rows.append(resolved)
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    # ------------------------------------------------------------------
    # Tool 25: identity_overlay
    # ------------------------------------------------------------------
    def identity_overlay(
        self,
        other: "GeoPromptFrame",
        left_id_column: str = "site_id",
        right_id_column: str = "site_id",
        identity_suffix: str = "identity",
    ) -> "GeoPromptFrame":
        if self.crs and other.crs and self.crs != other.crs:
            raise ValueError("frames must share the same CRS")
        from .overlay import geometry_to_shapely, geometry_from_shapely, _load_shapely
        _, _, unary_union, _ = _load_shapely()
        right_shapes = [geometry_to_shapely(row[other.geometry_column]) for row in other._rows]
        rows: list[Record] = []
        for left_row in self._rows:
            left_shape = geometry_to_shapely(left_row[self.geometry_column])
            remaining = left_shape
            matched = False
            for right_idx, right_shape in enumerate(right_shapes):
                intersection = left_shape.intersection(right_shape)
                if intersection.is_empty:
                    continue
                for geom in geometry_from_shapely(intersection):
                    resolved = dict(left_row)
                    resolved[self.geometry_column] = geom
                    for key, value in other._rows[right_idx].items():
                        if key != other.geometry_column:
                            resolved[f"{key}_{identity_suffix}"] = value
                    rows.append(resolved)
                    matched = True
                remaining = remaining.difference(right_shape)
            if not remaining.is_empty:
                for geom in geometry_from_shapely(remaining):
                    resolved = dict(left_row)
                    resolved[self.geometry_column] = geom
                    rows.append(resolved)
            elif not matched:
                rows.append(dict(left_row))
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    # ------------------------------------------------------------------
    # Tool 26: multipart_to_singlepart
    # ------------------------------------------------------------------
    def multipart_to_singlepart(
        self,
        id_column: str = "site_id",
        part_suffix: str = "part",
    ) -> "GeoPromptFrame":
        from .overlay import geometry_to_shapely, geometry_from_shapely, _load_shapely
        _load_shapely()
        rows: list[Record] = []
        part_counter = 0
        for row in self._rows:
            multipart_members = next(
                (
                    value
                    for key, value in row.items()
                    if key.startswith("part_geometries_") and isinstance(value, (list, tuple))
                ),
                None,
            )
            part_geometries = [
                member
                for member in (multipart_members or ())
                if isinstance(member, dict) and "type" in member and "coordinates" in member
            ]
            if not part_geometries:
                geom = row[self.geometry_column]
                shape = geometry_to_shapely(geom)
                if hasattr(shape, "geoms"):
                    for child in shape.geoms:
                        part_geometries.extend(geometry_from_shapely(child))
                else:
                    part_geometries.append(geom)
            for cg in part_geometries:
                part_counter += 1
                resolved = dict(row)
                resolved[self.geometry_column] = cg
                resolved[f"part_id_{part_suffix}"] = part_counter
                rows.append(resolved)
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    # ------------------------------------------------------------------
    # Tool 27: singlepart_to_multipart
    # ------------------------------------------------------------------
    def singlepart_to_multipart(
        self,
        group_column: str = "site_id",
        multipart_suffix: str = "multi",
    ) -> "GeoPromptFrame":
        self._require_column(group_column)
        from .overlay import geometry_to_shapely, geometry_from_shapely, _load_shapely
        _, _, unary_union, _ = _load_shapely()
        grouped: dict[str, list[Record]] = {}
        for row in self._rows:
            key = str(row[group_column])
            grouped.setdefault(key, []).append(row)
        rows: list[Record] = []
        for group_key, group_rows in grouped.items():
            shapes = [geometry_to_shapely(r[self.geometry_column]) for r in group_rows]
            merged = unary_union(shapes)
            merged_geoms = geometry_from_shapely(merged)
            first_row = dict(group_rows[0])
            if len(merged_geoms) == 1:
                first_row[self.geometry_column] = merged_geoms[0]
            first_row[f"part_geometries_{multipart_suffix}"] = tuple(
                dict(group_row[self.geometry_column]) for group_row in group_rows
            )
            first_row[f"part_count_{multipart_suffix}"] = len(group_rows)
            rows.append(first_row)
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    # ------------------------------------------------------------------
    # Tool 28: eliminate_slivers
    # ------------------------------------------------------------------
    def eliminate_slivers(
        self,
        min_area: float = 0.0,
        min_vertices: int = 0,
        sliver_suffix: str = "sliver",
    ) -> "GeoPromptFrame":
        rows: list[Record] = []
        eliminated = 0
        for row in self._rows:
            geom = row[self.geometry_column]
            area = geometry_area(geom)
            vertex_count = len(geometry_vertices(geom))
            if area < min_area or (min_vertices > 0 and vertex_count < min_vertices):
                eliminated += 1
                continue
            resolved = dict(row)
            resolved[f"area_{sliver_suffix}"] = area
            rows.append(resolved)
        for row in rows:
            row[f"eliminated_count_{sliver_suffix}"] = eliminated
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    # ------------------------------------------------------------------
    # Tool 29: simplify (Douglas-Peucker)
    # ------------------------------------------------------------------
    def simplify(
        self,
        tolerance: float = 0.001,
        simplify_suffix: str = "simplified",
    ) -> "GeoPromptFrame":
        if tolerance < 0:
            raise ValueError("tolerance must be zero or greater")
        rows: list[Record] = []
        for row in self._rows:
            geom = row[self.geometry_column]
            geom_kind = geometry_type(geom)
            resolved = dict(row)
            if geom_kind == "Point":
                resolved[f"vertex_count_{simplify_suffix}"] = 1
            elif geom_kind == "LineString":
                coords = list(geometry_vertices(geom))
                simplified = _douglas_peucker(coords, tolerance)
                if len(simplified) < 2:
                    simplified = coords[:2] if len(coords) >= 2 else coords
                resolved[self.geometry_column] = {"type": "LineString", "coordinates": tuple(simplified)}
                resolved[f"vertex_count_{simplify_suffix}"] = len(simplified)
                resolved[f"original_vertex_count_{simplify_suffix}"] = len(coords)
            elif geom_kind == "Polygon":
                coords = list(geometry_vertices(geom))
                simplified = _douglas_peucker(coords, tolerance)
                if len(simplified) < 4:
                    simplified = coords
                resolved[self.geometry_column] = {"type": "Polygon", "coordinates": tuple(simplified)}
                resolved[f"vertex_count_{simplify_suffix}"] = len(simplified)
                resolved[f"original_vertex_count_{simplify_suffix}"] = len(coords)
            rows.append(resolved)
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    # ------------------------------------------------------------------
    # Tool 30: densify
    # ------------------------------------------------------------------
    def densify(
        self,
        max_segment_length: float = 0.01,
        densify_suffix: str = "densified",
    ) -> "GeoPromptFrame":
        if max_segment_length <= 0:
            raise ValueError("max_segment_length must be greater than zero")
        rows: list[Record] = []
        for row in self._rows:
            geom = row[self.geometry_column]
            geom_kind = geometry_type(geom)
            resolved = dict(row)
            if geom_kind in ("LineString", "Polygon"):
                coords = list(geometry_vertices(geom))
                dense_coords = _densify_coordinates(coords, max_segment_length)
                resolved[self.geometry_column] = {"type": geom_kind, "coordinates": tuple(dense_coords)}
                resolved[f"vertex_count_{densify_suffix}"] = len(dense_coords)
                resolved[f"original_vertex_count_{densify_suffix}"] = len(coords)
            rows.append(resolved)
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    # ------------------------------------------------------------------
    # Tool 31: smooth_geometry (Chaikin)
    # ------------------------------------------------------------------
    def smooth_geometry(
        self,
        iterations: int = 3,
        smooth_suffix: str = "smoothed",
    ) -> "GeoPromptFrame":
        if iterations < 1:
            raise ValueError("iterations must be at least 1")
        rows: list[Record] = []
        for row in self._rows:
            geom = row[self.geometry_column]
            geom_kind = geometry_type(geom)
            resolved = dict(row)
            if geom_kind in ("LineString", "Polygon"):
                coords = list(geometry_vertices(geom))
                smoothed = coords
                for _ in range(iterations):
                    smoothed = _chaikin_smooth(smoothed, is_closed=(geom_kind == "Polygon"))
                resolved[self.geometry_column] = {"type": geom_kind, "coordinates": tuple(smoothed)}
                resolved[f"vertex_count_{smooth_suffix}"] = len(smoothed)
            rows.append(resolved)
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    # ------------------------------------------------------------------
    # Tool 32: snap_to_network_nodes
    # ------------------------------------------------------------------
    def snap_to_network_nodes(
        self,
        points: "GeoPromptFrame",
        from_node_column: str = "from_node",
        to_node_column: str = "to_node",
        max_distance: float | None = None,
        distance_method: str = "euclidean",
        snap_suffix: str = "snapped",
    ) -> "GeoPromptFrame":
        self._require_column(from_node_column)
        self._require_column(to_node_column)
        node_positions: dict[str, Coordinate] = {}
        for row in self._rows:
            from_node = row[from_node_column]
            to_node = row[to_node_column]
            verts = geometry_vertices(row[self.geometry_column])
            if verts:
                node_positions.setdefault(str(from_node), verts[0])
                node_positions.setdefault(str(to_node), verts[-1])
        node_list = list(node_positions.items())
        point_centroids = points._centroids()
        rows: list[Record] = []
        for pt_idx, pt_row in enumerate(points._rows):
            pt = point_centroids[pt_idx]
            best_node: str | None = None
            best_dist = float("inf")
            best_coord: Coordinate | None = None
            for node_id, node_coord in node_list:
                d = coordinate_distance(pt, node_coord, method=distance_method)
                if max_distance is not None and d > max_distance:
                    continue
                if d < best_dist:
                    best_dist = d
                    best_node = node_id
                    best_coord = node_coord
            resolved = dict(pt_row)
            resolved[f"node_id_{snap_suffix}"] = best_node
            resolved[f"snap_distance_{snap_suffix}"] = best_dist if best_node is not None else None
            if best_coord is not None:
                resolved[points.geometry_column] = {"type": "Point", "coordinates": best_coord}
            rows.append(resolved)
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=points.geometry_column, crs=points.crs or self.crs)

    # ------------------------------------------------------------------
    # Tool 33: origin_destination_matrix
    # ------------------------------------------------------------------
    def origin_destination_matrix(
        self,
        origins: "GeoPromptFrame",
        destinations: "GeoPromptFrame",
        origin_id_column: str = "site_id",
        destination_id_column: str = "site_id",
        from_node_id_column: str = "from_node_id",
        to_node_id_column: str = "to_node_id",
        from_node_column: str = "from_node",
        to_node_column: str = "to_node",
        cost_column: str = "edge_length",
        origin_node_column: str | None = None,
        destination_node_column: str | None = None,
        directed: bool = False,
        max_cost: float | None = None,
        od_suffix: str = "od",
    ) -> "GeoPromptFrame":
        for col in (from_node_id_column, to_node_id_column, from_node_column, to_node_column, cost_column):
            self._require_column(col)
        origins._require_column(origin_id_column)
        destinations._require_column(destination_id_column)
        adjacency = self._network_graph(from_node_id_column, to_node_id_column, cost_column, directed=directed)
        rows: list[Record] = []
        for origin_row in origins._rows:
            origin_node = self._resolve_network_node(
                origin_row.get(origin_node_column) if origin_node_column else geometry_centroid(origin_row[origins.geometry_column]),
                from_node_id_column, to_node_id_column, from_node_column, to_node_column,
            )
            distances: dict[str, float] = {origin_node: 0.0}
            queue: list[tuple[float, str]] = [(0.0, origin_node)]
            visited: set[str] = set()
            while queue:
                current_cost, current_node = heappop(queue)
                if current_node in visited:
                    continue
                visited.add(current_node)
                if max_cost is not None and current_cost > max_cost:
                    continue
                for next_node, edge_cost, _ in adjacency.get(current_node, []):
                    path_cost = current_cost + edge_cost
                    if path_cost < distances.get(next_node, float("inf")):
                        distances[next_node] = path_cost
                        heappush(queue, (path_cost, next_node))
            for dest_row in destinations._rows:
                dest_node = self._resolve_network_node(
                    dest_row.get(destination_node_column) if destination_node_column else geometry_centroid(dest_row[destinations.geometry_column]),
                    from_node_id_column, to_node_id_column, from_node_column, to_node_column,
                )
                cost = distances.get(dest_node)
                if max_cost is not None and cost is not None and cost > max_cost:
                    cost = None
                origin_centroid = geometry_centroid(origin_row[origins.geometry_column])
                dest_centroid = geometry_centroid(dest_row[destinations.geometry_column])
                rows.append({
                    f"origin_id_{od_suffix}": str(origin_row[origin_id_column]),
                    f"destination_id_{od_suffix}": str(dest_row[destination_id_column]),
                    f"network_cost_{od_suffix}": cost,
                    f"reachable_{od_suffix}": cost is not None,
                    self.geometry_column: {"type": "LineString", "coordinates": (origin_centroid, dest_centroid)},
                })
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    # ------------------------------------------------------------------
    # Tool 34: k_shortest_paths
    # ------------------------------------------------------------------
    def k_shortest_paths(
        self,
        origin: str | Coordinate,
        destination: str | Coordinate,
        k: int = 3,
        edge_id_column: str = "edge_id",
        from_node_id_column: str = "from_node_id",
        to_node_id_column: str = "to_node_id",
        from_node_column: str = "from_node",
        to_node_column: str = "to_node",
        cost_column: str = "edge_length",
        directed: bool = False,
        ksp_suffix: str = "ksp",
    ) -> "GeoPromptFrame":
        if k <= 0:
            raise ValueError("k must be greater than zero")
        for col in (edge_id_column, from_node_id_column, to_node_id_column, from_node_column, to_node_column, cost_column):
            self._require_column(col)
        origin_node = self._resolve_network_node(origin, from_node_id_column, to_node_id_column, from_node_column, to_node_column)
        dest_node = self._resolve_network_node(destination, from_node_id_column, to_node_id_column, from_node_column, to_node_column)
        adjacency = self._network_graph(from_node_id_column, to_node_id_column, cost_column, directed=directed)
        queue: list[tuple[float, str, tuple[int, ...], frozenset[str]]] = [
            (0.0, origin_node, (), frozenset({origin_node}))
        ]
        found_paths: list[tuple[float, tuple[int, ...]]] = []
        seen_paths: set[tuple[int, ...]] = set()
        while queue and len(found_paths) < k:
            path_cost, node_id, edge_path, visited_nodes = heappop(queue)
            if node_id == dest_node:
                if edge_path not in seen_paths:
                    seen_paths.add(edge_path)
                    found_paths.append((path_cost, edge_path))
                continue
            for next_node, edge_cost, edge_index in adjacency.get(node_id, []):
                if next_node in visited_nodes:
                    continue
                heappush(
                    queue,
                    (
                        path_cost + edge_cost,
                        next_node,
                        (*edge_path, edge_index),
                        visited_nodes | {next_node},
                    ),
                )
        if not found_paths:
            return GeoPromptFrame._from_internal_rows([], geometry_column=self.geometry_column, crs=self.crs)
        rows: list[Record] = []
        for path_rank, (path_cost, path_edges) in enumerate(found_paths, start=1):
            for step, edge_idx in enumerate(path_edges, start=1):
                resolved = dict(self._rows[edge_idx])
                resolved[f"path_rank_{ksp_suffix}"] = path_rank
                resolved[f"step_{ksp_suffix}"] = step
                resolved[f"total_cost_{ksp_suffix}"] = path_cost
                resolved[f"edge_count_{ksp_suffix}"] = len(path_edges)
                rows.append(resolved)
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    def _dijkstra_path(
        self,
        origin_node: str,
        dest_node: str,
        adjacency: dict[str, list[tuple[str, float, int]]],
    ) -> tuple[float, list[int]] | None:
        distances: dict[str, float] = {origin_node: 0.0}
        previous: dict[str, tuple[str, int]] = {}
        queue: list[tuple[float, str]] = [(0.0, origin_node)]
        visited: set[str] = set()
        while queue:
            cost, node = heappop(queue)
            if node in visited:
                continue
            visited.add(node)
            if node == dest_node:
                break
            for next_node, edge_cost, edge_idx in adjacency.get(node, []):
                new_cost = cost + edge_cost
                if new_cost < distances.get(next_node, float("inf")):
                    distances[next_node] = new_cost
                    previous[next_node] = (node, edge_idx)
                    heappush(queue, (new_cost, next_node))
        if dest_node not in distances:
            return None
        edges: list[int] = []
        current = dest_node
        while current != origin_node:
            prev_node, edge_idx = previous[current]
            edges.append(edge_idx)
            current = prev_node
        edges.reverse()
        return (distances[dest_node], edges)

    # ------------------------------------------------------------------
    # Tool 35: network_trace
    # ------------------------------------------------------------------
    def network_trace(
        self,
        start: str | Coordinate,
        direction: Literal["upstream", "downstream", "both"] = "both",
        max_cost: float | None = None,
        from_node_id_column: str = "from_node_id",
        to_node_id_column: str = "to_node_id",
        from_node_column: str = "from_node",
        to_node_column: str = "to_node",
        cost_column: str = "edge_length",
        trace_suffix: str = "trace",
    ) -> "GeoPromptFrame":
        for col in (from_node_id_column, to_node_id_column, from_node_column, to_node_column, cost_column):
            self._require_column(col)
        start_node = self._resolve_network_node(start, from_node_id_column, to_node_id_column, from_node_column, to_node_column)
        forward_adj: dict[str, list[tuple[str, float, int]]] = {}
        reverse_adj: dict[str, list[tuple[str, float, int]]] = {}
        for idx, row in enumerate(self._rows):
            from_node = str(row[from_node_id_column])
            to_node = str(row[to_node_id_column])
            cost = float(row[cost_column])
            forward_adj.setdefault(from_node, []).append((to_node, cost, idx))
            reverse_adj.setdefault(to_node, []).append((from_node, cost, idx))
        traced_edges: set[int] = set()
        edge_costs: dict[int, float] = {}
        if direction in ("downstream", "both"):
            self._bfs_trace(start_node, forward_adj, max_cost, traced_edges, edge_costs)
        if direction in ("upstream", "both"):
            self._bfs_trace(start_node, reverse_adj, max_cost, traced_edges, edge_costs)
        rows: list[Record] = []
        for edge_idx in sorted(traced_edges):
            resolved = dict(self._rows[edge_idx])
            resolved[f"trace_cost_{trace_suffix}"] = edge_costs.get(edge_idx, 0.0)
            resolved[f"direction_{trace_suffix}"] = direction
            resolved[f"start_node_{trace_suffix}"] = start_node
            rows.append(resolved)
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    @staticmethod
    def _bfs_trace(
        start_node: str,
        adjacency: dict[str, list[tuple[str, float, int]]],
        max_cost: float | None,
        traced_edges: set[int],
        edge_costs: dict[int, float],
    ) -> None:
        visited: set[str] = set()
        queue: list[tuple[float, str]] = [(0.0, start_node)]
        while queue:
            cost, node = heappop(queue)
            if node in visited:
                continue
            visited.add(node)
            for next_node, edge_cost, edge_idx in adjacency.get(node, []):
                new_cost = cost + edge_cost
                if max_cost is not None and new_cost > max_cost:
                    continue
                traced_edges.add(edge_idx)
                edge_costs[edge_idx] = min(edge_costs.get(edge_idx, float("inf")), new_cost)
                if next_node not in visited:
                    heappush(queue, (new_cost, next_node))

    # ------------------------------------------------------------------
    # Tool 36: route_sequence_optimize (greedy TSP)
    # ------------------------------------------------------------------
    def route_sequence_optimize(
        self,
        stops: "GeoPromptFrame",
        stop_id_column: str = "site_id",
        from_node_id_column: str = "from_node_id",
        to_node_id_column: str = "to_node_id",
        from_node_column: str = "from_node",
        to_node_column: str = "to_node",
        cost_column: str = "edge_length",
        stop_node_column: str | None = None,
        directed: bool = False,
        route_suffix: str = "route",
    ) -> "GeoPromptFrame":
        for col in (from_node_id_column, to_node_id_column, from_node_column, to_node_column, cost_column):
            self._require_column(col)
        stops._require_column(stop_id_column)
        stop_count = len(stops._rows)
        if stop_count == 0:
            return GeoPromptFrame._from_internal_rows([], geometry_column=self.geometry_column, crs=self.crs)
        adjacency = self._network_graph(from_node_id_column, to_node_id_column, cost_column, directed=directed)
        stop_nodes: list[str] = []
        for stop_row in stops._rows:
            node = self._resolve_network_node(
                stop_row.get(stop_node_column) if stop_node_column else geometry_centroid(stop_row[stops.geometry_column]),
                from_node_id_column, to_node_id_column, from_node_column, to_node_column,
            )
            stop_nodes.append(node)
        cost_matrix: list[list[float]] = []
        path_matrix: list[list[list[int] | None]] = []
        for i in range(stop_count):
            dists, paths = self._dijkstra_all(stop_nodes[i], adjacency)
            row_costs: list[float] = []
            row_paths: list[list[int] | None] = []
            for j in range(stop_count):
                row_costs.append(dists.get(stop_nodes[j], float("inf")))
                if stop_nodes[j] in dists:
                    edge_list: list[int] = []
                    current = stop_nodes[j]
                    while current != stop_nodes[i]:
                        prev_node, edge_idx = paths[current]
                        edge_list.append(edge_idx)
                        current = prev_node
                    edge_list.reverse()
                    row_paths.append(edge_list)
                else:
                    row_paths.append(None)
            cost_matrix.append(row_costs)
            path_matrix.append(row_paths)
        visited_set = {0}
        sequence = [0]
        current = 0
        reachable_sequence = {0}
        for _ in range(stop_count - 1):
            best_next: int | None = None
            best_cost = float("inf")
            for j in range(stop_count):
                if j not in visited_set and cost_matrix[current][j] < best_cost:
                    best_cost = cost_matrix[current][j]
                    best_next = j
            if best_next is None:
                break
            visited_set.add(best_next)
            sequence.append(best_next)
            current = best_next
            reachable_sequence.add(best_next)
        reachable_route = _two_opt_open_path(sequence, cost_matrix)
        total_cost = _path_sequence_cost(reachable_route, cost_matrix)
        sequence = list(reachable_route)
        visited_set = set(sequence)
        reachable_sequence = set(sequence)
        for stop_idx in range(stop_count):
            if stop_idx not in visited_set:
                sequence.append(stop_idx)
        rows: list[Record] = []
        for order, stop_idx in enumerate(sequence, start=1):
            resolved = dict(stops._rows[stop_idx])
            resolved[f"visit_order_{route_suffix}"] = order
            resolved[f"stop_node_{route_suffix}"] = stop_nodes[stop_idx]
            resolved[f"total_cost_{route_suffix}"] = total_cost
            resolved[f"stop_count_{route_suffix}"] = len(sequence)
            resolved[f"reachable_{route_suffix}"] = stop_idx in reachable_sequence
            resolved[f"method_{route_suffix}"] = "greedy_2opt"
            rows.append(resolved)
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=stops.geometry_column, crs=self.crs or stops.crs)

    def _dijkstra_all(
        self,
        origin_node: str,
        adjacency: dict[str, list[tuple[str, float, int]]],
    ) -> tuple[dict[str, float], dict[str, tuple[str, int]]]:
        distances: dict[str, float] = {origin_node: 0.0}
        previous: dict[str, tuple[str, int]] = {}
        queue: list[tuple[float, str]] = [(0.0, origin_node)]
        visited: set[str] = set()
        while queue:
            cost, node = heappop(queue)
            if node in visited:
                continue
            visited.add(node)
            for next_node, edge_cost, edge_idx in adjacency.get(node, []):
                new_cost = cost + edge_cost
                if new_cost < distances.get(next_node, float("inf")):
                    distances[next_node] = new_cost
                    previous[next_node] = (node, edge_idx)
                    heappush(queue, (new_cost, next_node))
        return distances, previous

    # ------------------------------------------------------------------
    # Tool 37: trajectory_staypoint_detection
    # ------------------------------------------------------------------
    def trajectory_staypoint_detection(
        self,
        time_column: str,
        id_column: str = "site_id",
        min_duration: float = 0.0,
        max_radius: float = 0.01,
        distance_method: str = "euclidean",
        staypoint_suffix: str = "staypoint",
    ) -> "GeoPromptFrame":
        self._require_column(time_column)
        self._require_column(id_column)
        if not self._rows:
            return GeoPromptFrame._from_internal_rows([], geometry_column=self.geometry_column, crs=self.crs)
        ordered_indexes = sorted(
            range(len(self._rows)),
            key=lambda index: (float(self._rows[index].get(time_column, 0) or 0), index),
        )
        ordered_rows = [self._rows[index] for index in ordered_indexes]
        centroids = self._centroids(ordered_rows, self.geometry_column)
        rows: list[Record] = []
        staypoint_id = 0
        i = 0
        while i < len(ordered_rows):
            anchor = centroids[i]
            j = i + 1
            while j < len(ordered_rows):
                d = coordinate_distance(anchor, centroids[j], method=distance_method)
                if d > max_radius:
                    break
                j += 1
            t_start = float(ordered_rows[i].get(time_column, 0) or 0)
            t_end = float(ordered_rows[j - 1].get(time_column, 0) or 0)
            duration = t_end - t_start
            is_staypoint = (j - i) >= 2 and duration >= min_duration
            if is_staypoint:
                staypoint_id += 1
                mean_x = sum(centroids[k][0] for k in range(i, j)) / (j - i)
                mean_y = sum(centroids[k][1] for k in range(i, j)) / (j - i)
                for k in range(i, j):
                    resolved = dict(ordered_rows[k])
                    resolved[f"staypoint_id_{staypoint_suffix}"] = staypoint_id
                    resolved[f"is_staypoint_{staypoint_suffix}"] = True
                    resolved[f"duration_{staypoint_suffix}"] = duration
                    resolved[f"point_count_{staypoint_suffix}"] = j - i
                    resolved[f"center_x_{staypoint_suffix}"] = mean_x
                    resolved[f"center_y_{staypoint_suffix}"] = mean_y
                    rows.append(resolved)
                i = j
            else:
                resolved = dict(ordered_rows[i])
                resolved[f"staypoint_id_{staypoint_suffix}"] = None
                resolved[f"is_staypoint_{staypoint_suffix}"] = False
                resolved[f"duration_{staypoint_suffix}"] = 0.0
                resolved[f"point_count_{staypoint_suffix}"] = 1
                rows.append(resolved)
                i += 1
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    # ------------------------------------------------------------------
    # Tool 38: trajectory_simplify (Ramer-Douglas-Peucker on trajectory)
    # ------------------------------------------------------------------
    def trajectory_simplify(
        self,
        tolerance: float = 0.001,
        time_column: str | None = None,
        simplify_suffix: str = "traj_simplified",
    ) -> "GeoPromptFrame":
        if tolerance < 0:
            raise ValueError("tolerance must be zero or greater")
        if not self._rows:
            return GeoPromptFrame._from_internal_rows([], geometry_column=self.geometry_column, crs=self.crs)
        ordered_indexes = list(range(len(self._rows)))
        if time_column is not None:
            self._require_column(time_column)
            ordered_indexes.sort(key=lambda index: (float(self._rows[index].get(time_column, 0) or 0), index))
        ordered_rows = [self._rows[index] for index in ordered_indexes]
        centroids = self._centroids(ordered_rows, self.geometry_column)
        keep_indices = set(_douglas_peucker_indices(centroids, tolerance))
        rows: list[Record] = []
        for i in keep_indices:
            resolved = dict(ordered_rows[i])
            resolved[f"kept_{simplify_suffix}"] = True
            resolved[f"original_index_{simplify_suffix}"] = ordered_indexes[i]
            rows.append(resolved)
        if time_column is not None:
            rows.sort(key=lambda row: (float(row.get(time_column, 0) or 0), int(row[f"original_index_{simplify_suffix}"])))
        else:
            rows.sort(key=lambda row: int(row[f"original_index_{simplify_suffix}"]))
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    # ------------------------------------------------------------------
    # Tool 39: spatiotemporal_cube
    # ------------------------------------------------------------------
    def spatiotemporal_cube(
        self,
        time_column: str,
        value_column: str,
        time_intervals: int = 5,
        grid_resolution: int = 10,
        aggregation: AggregationName = "count",
        distance_method: str = "euclidean",
        cube_suffix: str = "cube",
    ) -> "GeoPromptFrame":
        self._require_column(time_column)
        if time_intervals <= 0:
            raise ValueError("time_intervals must be greater than zero")
        if grid_resolution <= 0:
            raise ValueError("grid_resolution must be greater than zero")
        if aggregation != "count":
            self._require_column(value_column)
        if not self._rows:
            return GeoPromptFrame._from_internal_rows([], geometry_column=self.geometry_column, crs=self.crs)
        times = [float(row.get(time_column, 0) or 0) for row in self._rows]
        t_min, t_max = min(times), max(times)
        t_step = (t_max - t_min) / time_intervals if t_max > t_min else 1.0
        b = self.bounds()
        dx = (b.max_x - b.min_x) / grid_resolution
        dy = (b.max_y - b.min_y) / grid_resolution
        centroids = self._centroids()
        buckets: dict[tuple[int, int, int], list[float]] = {}
        for row_index, centroid in enumerate(centroids):
            time_value = times[row_index]
            if t_max > t_min:
                time_bin = min(int((time_value - t_min) / t_step), time_intervals - 1)
            else:
                time_bin = 0
            if dx > 0.0:
                grid_col = min(int((centroid[0] - b.min_x) / dx), grid_resolution - 1)
            else:
                grid_col = 0
            if dy > 0.0:
                grid_row = min(int((centroid[1] - b.min_y) / dy), grid_resolution - 1)
            else:
                grid_row = 0
            value = self._rows[row_index].get(value_column)
            buckets.setdefault((time_bin, grid_row, grid_col), []).append(float(value) if value is not None else 0.0)
        rows: list[Record] = []
        cell_id = 0
        for ti, gy, gx in sorted(buckets):
            t_lo = t_min + ti * t_step
            t_hi = t_lo + t_step
            matched_vals = buckets[(ti, gy, gx)]
            if not matched_vals and aggregation != "count":
                continue
            px = b.min_x + gx * dx + dx / 2.0 if dx > 0.0 else b.min_x
            py = b.min_y + gy * dy + dy / 2.0 if dy > 0.0 else b.min_y
            agg_val: float | None
            if aggregation == "count":
                agg_val = float(len(matched_vals))
            elif aggregation == "sum":
                agg_val = sum(matched_vals) if matched_vals else None
            elif aggregation == "mean":
                agg_val = (sum(matched_vals) / len(matched_vals)) if matched_vals else None
            elif aggregation == "min":
                agg_val = min(matched_vals) if matched_vals else None
            elif aggregation == "max":
                agg_val = max(matched_vals) if matched_vals else None
            else:
                agg_val = float(len(matched_vals))
            if aggregation == "count" and agg_val == 0.0:
                continue
            cell_id += 1
            rows.append({
                f"cell_id_{cube_suffix}": f"cube-{cell_id:04d}",
                f"time_bin_{cube_suffix}": ti,
                f"time_start_{cube_suffix}": t_lo,
                f"time_end_{cube_suffix}": t_hi,
                f"grid_row_{cube_suffix}": gy,
                f"grid_col_{cube_suffix}": gx,
                f"value_{cube_suffix}": agg_val,
                f"point_count_{cube_suffix}": len(matched_vals),
                self.geometry_column: {"type": "Point", "coordinates": (px, py)},
            })
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    # ------------------------------------------------------------------
    # Tool 40: geohash_encode
    # ------------------------------------------------------------------
    def geohash_encode(
        self,
        precision: int = 6,
        geohash_suffix: str = "geohash",
    ) -> "GeoPromptFrame":
        if precision < 1 or precision > 12:
            raise ValueError("precision must be between 1 and 12")
        centroids = self._centroids()
        rows: list[Record] = []
        for i, row in enumerate(self._rows):
            lon, lat = centroids[i]
            hash_val = _geohash_encode(lat, lon, precision)
            resolved = dict(row)
            resolved[f"hash_{geohash_suffix}"] = hash_val
            resolved[f"precision_{geohash_suffix}"] = precision
            rows.append(resolved)
        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs)

    # ------------------------------------------------------------------
    # Internal helper: IDW grid generation
    # ------------------------------------------------------------------
    def _idw_grid(
        self,
        value_column: str,
        grid_resolution: int,
        distance_method: str,
    ) -> tuple[list[list[float]], Bounds, float, float]:
        centroids = self._centroids()
        b = self.bounds()
        dx = (b.max_x - b.min_x) / max(grid_resolution - 1, 1)
        dy = (b.max_y - b.min_y) / max(grid_resolution - 1, 1)
        use_euclidean = distance_method == "euclidean"
        grid: list[list[float]] = []
        for gy in range(grid_resolution):
            row_vals: list[float] = []
            py = b.min_y + gy * dy
            for gx in range(grid_resolution):
                px = b.min_x + gx * dx
                weight_sum = 0.0
                value_sum = 0.0
                for ci, centroid in enumerate(centroids):
                    if use_euclidean:
                        d = math.hypot(px - centroid[0], py - centroid[1])
                    else:
                        d = coordinate_distance((px, py), centroid, method=distance_method)
                    w = 1.0 / max(d * d, 1e-12)
                    weight_sum += w
                    value_sum += w * float(self._rows[ci].get(value_column, 0) or 0)
                row_vals.append(value_sum / weight_sum if weight_sum > 0 else 0.0)
            grid.append(row_vals)
        return grid, b, dx, dy


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
    baseline_events = [_prepare_change_event_match(row, change_suffix, geometry_column) for row in baseline_rows]
    current_events = [_prepare_change_event_match(row, change_suffix, geometry_column) for row in current_rows]
    current_events_by_class: dict[str, list[tuple[int, dict[str, Any]]]] = {}
    for current_index, current_event in enumerate(current_events):
        current_events_by_class.setdefault(current_event["change_class"], []).append((current_index, current_event))

    candidate_pairs: list[tuple[float, int, int]] = []
    for baseline_index, baseline_event in enumerate(baseline_events):
        for current_index, current_event in current_events_by_class.get(baseline_event["change_class"], []):
            similarity = _equivalent_change_event_similarity_prepared(baseline_event, current_event)
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
    return _equivalent_change_event_similarity_prepared(
        _prepare_change_event_match(baseline_row, change_suffix, geometry_column),
        _prepare_change_event_match(current_row, change_suffix, geometry_column),
    )


def _prepare_change_event_match(row: Record, change_suffix: str, geometry_column: str) -> dict[str, Any]:
    summary = dict(row.get(f"event_summary_{change_suffix}") or {})
    geometry = row.get(geometry_column)
    return {
        "row": row,
        "change_class": str(row.get(f"change_class_{change_suffix}")),
        "event_side": str(row.get(f"event_side_{change_suffix}")),
        "left_id_set": {str(value) for value in row.get(f"left_ids_{change_suffix}", [])},
        "right_id_set": {str(value) for value in row.get(f"right_ids_{change_suffix}", [])},
        "feature_count": summary.get("feature_count"),
        "row_count": summary.get("row_count"),
        "attribute_columns_set": {str(value) for value in summary.get("attribute_columns", [])},
        "geometry": geometry,
        "centroid": geometry_centroid(geometry) if isinstance(geometry, dict) else None,
    }


def _equivalent_change_event_similarity_prepared(
    baseline_event: dict[str, Any],
    current_event: dict[str, Any],
) -> float:
    if baseline_event["change_class"] != current_event["change_class"]:
        return 0.0

    left_similarity = _prepared_set_similarity(baseline_event["left_id_set"], current_event["left_id_set"])
    right_similarity = _prepared_set_similarity(baseline_event["right_id_set"], current_event["right_id_set"])
    feature_count_similarity = _count_similarity(baseline_event["feature_count"], current_event["feature_count"])
    row_count_similarity = _count_similarity(baseline_event["row_count"], current_event["row_count"])
    attribute_similarity = _prepared_set_similarity(
        baseline_event["attribute_columns_set"],
        current_event["attribute_columns_set"],
    )
    side_similarity = 1.0 if baseline_event["event_side"] == current_event["event_side"] else 0.0
    partial_similarity = (
        (0.1 * side_similarity)
        + (0.2 * left_similarity)
        + (0.2 * right_similarity)
        + (0.15 * feature_count_similarity)
        + (0.1 * row_count_similarity)
        + (0.1 * attribute_similarity)
    )
    if partial_similarity >= 0.85:
        geometry_similarity = 1.0
    else:
        geometry_similarity = _geometry_similarity_prepared(
            baseline_event["geometry"],
            current_event["geometry"],
            baseline_event.get("centroid"),
            current_event.get("centroid"),
        )
    return partial_similarity + (0.15 * geometry_similarity)


def _prepared_set_similarity(left_values: set[str], right_values: set[str]) -> float:
    if not left_values and not right_values:
        return 1.0
    union = left_values | right_values
    if not union:
        return 0.0
    return len(left_values & right_values) / len(union)


def _geometry_similarity_prepared(
    left_geometry: Any,
    right_geometry: Any,
    left_centroid: Coordinate | None,
    right_centroid: Coordinate | None,
) -> float:
    if left_centroid is not None and right_centroid is not None:
        distance_value = coordinate_distance(left_centroid, right_centroid)
        return 1.0 / (1.0 + float(distance_value))
    return _geometry_similarity(left_geometry, right_geometry)


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


# ------------------------------------------------------------------
# Helper functions for new tools (40-tool expansion)
# ------------------------------------------------------------------

def _marching_square_edges(
    cell_values: list[float],
    cell_coords: list[Coordinate],
    level: float,
) -> list[Coordinate]:
    edges: list[Coordinate] = []
    sides = [
        (cell_values[0], cell_values[1], cell_coords[0], cell_coords[1]),
        (cell_values[1], cell_values[2], cell_coords[1], cell_coords[2]),
        (cell_values[2], cell_values[3], cell_coords[2], cell_coords[3]),
        (cell_values[3], cell_values[0], cell_coords[3], cell_coords[0]),
    ]
    crossing_points: list[Coordinate] = []
    for v0, v1, c0, c1 in sides:
        if (v0 < level) != (v1 < level):
            t = (level - v0) / (v1 - v0) if abs(v1 - v0) > 1e-12 else 0.5
            crossing_points.append((c0[0] + t * (c1[0] - c0[0]), c0[1] + t * (c1[1] - c0[1])))
    if len(crossing_points) == 2:
        edges.extend(crossing_points)
    elif len(crossing_points) == 4:
        edges.extend(crossing_points[:2])
        edges.extend(crossing_points[2:])
    return edges


def _variogram_value(
    variogram_model: str,
    h: float,
    range_val: float,
    sill: float,
    nugget: float,
    *,
    include_nugget_at_zero: bool = False,
) -> float:
    if variogram_model == "spherical":
        return _spherical_variogram(
            h,
            range_val,
            sill,
            nugget,
            include_nugget_at_zero=include_nugget_at_zero,
        )
    if variogram_model == "exponential":
        return _exponential_variogram(
            h,
            range_val,
            sill,
            nugget,
            include_nugget_at_zero=include_nugget_at_zero,
        )
    if variogram_model == "gaussian":
        return _gaussian_variogram(
            h,
            range_val,
            sill,
            nugget,
            include_nugget_at_zero=include_nugget_at_zero,
        )
    if variogram_model == "hole_effect":
        return _hole_effect_variogram(
            h,
            range_val,
            sill,
            nugget,
            include_nugget_at_zero=include_nugget_at_zero,
        )
    raise ValueError(f"unsupported variogram_model: {variogram_model}")


def _spherical_variogram(
    h: float,
    range_val: float,
    sill: float,
    nugget: float,
    *,
    include_nugget_at_zero: bool = False,
) -> float:
    partial_sill = max(sill - nugget, 0.0)
    if h <= 0:
        return nugget if include_nugget_at_zero else 0.0
    if h >= range_val:
        return nugget + partial_sill
    ratio = h / range_val
    return nugget + partial_sill * (1.5 * ratio - 0.5 * ratio ** 3)


def _exponential_variogram(
    h: float,
    range_val: float,
    sill: float,
    nugget: float,
    *,
    include_nugget_at_zero: bool = False,
) -> float:
    partial_sill = max(sill - nugget, 0.0)
    if h <= 0:
        return nugget if include_nugget_at_zero else 0.0
    return partial_sill * (1.0 - math.exp(-h / max(range_val / 3.0, 1e-12))) + nugget


def _gaussian_variogram(
    h: float,
    range_val: float,
    sill: float,
    nugget: float,
    *,
    include_nugget_at_zero: bool = False,
) -> float:
    partial_sill = max(sill - nugget, 0.0)
    if h <= 0:
        return nugget if include_nugget_at_zero else 0.0
    effective_scale = max(range_val * 4.0 / 7.0, 1e-12)
    return partial_sill * (1.0 - math.exp(-(h ** 2.0) / (effective_scale ** 2.0))) + nugget


def _hole_effect_variogram(
    h: float,
    range_val: float,
    sill: float,
    nugget: float,
    *,
    include_nugget_at_zero: bool = False,
) -> float:
    partial_sill = max(sill - nugget, 0.0)
    if h <= 0:
        return nugget if include_nugget_at_zero else 0.0
    scaled = h / max(range_val / 3.0, 1e-12)
    return partial_sill * (1.0 - (1.0 - scaled) * math.exp(-scaled)) + nugget


def _normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _two_sided_t_probability(t_statistic_abs: float, degrees_of_freedom: int) -> float:
    if degrees_of_freedom <= 0:
        return 2.0 * (1.0 - _normal_cdf(t_statistic_abs))
    try:
        scipy_stats = importlib.import_module("scipy.stats")
    except ImportError:
        return 2.0 * (1.0 - _normal_cdf(t_statistic_abs))
    return 2.0 * float(scipy_stats.t.sf(t_statistic_abs, degrees_of_freedom))


def _reference_getis_ord_statistics(
    values: Sequence[float],
    neighbor_indexes: Sequence[Sequence[int]],
    include_self: bool,
) -> list[tuple[float, float]] | None:
    try:
        esda = importlib.import_module("esda")
        libpysal_weights = importlib.import_module("libpysal.weights")
    except ImportError:
        return None
    try:
        weights = libpysal_weights.W(
            {index: list(neighbors) for index, neighbors in enumerate(neighbor_indexes)},
            {index: [1.0] * len(neighbors) for index, neighbors in enumerate(neighbor_indexes)},
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            statistic = esda.G_Local(
                values,
                weights,
                transform="B",
                permutations=0,
                star=include_self,
                keep_simulations=False,
                island_weight=0,
            )
    except Exception:
        return None
    z_scores = getattr(statistic, "Zs", None)
    p_values = getattr(statistic, "p_norm", None)
    if z_scores is None or p_values is None:
        return None
    statistics: list[tuple[float, float]] = []
    for z_score, p_value in zip(z_scores, p_values, strict=True):
        z_numeric = float(z_score) if z_score is not None and math.isfinite(float(z_score)) else 0.0
        p_numeric = float(p_value) if p_value is not None and math.isfinite(float(p_value)) else 1.0
        statistics.append((z_numeric, p_numeric))
    return statistics


def _pairwise_distance_matrix(
    coordinates: Sequence[Coordinate],
    distance_method: str,
) -> list[list[float]]:
    n = len(coordinates)
    matrix = [[0.0] * n for _ in range(n)]
    if distance_method == "euclidean":
        for i in range(n):
            x_i, y_i = coordinates[i]
            for j in range(i + 1, n):
                x_j, y_j = coordinates[j]
                distance = math.hypot(x_j - x_i, y_j - y_i)
                matrix[i][j] = distance
                matrix[j][i] = distance
        return matrix
    for i in range(n):
        for j in range(i + 1, n):
            distance = coordinate_distance(coordinates[i], coordinates[j], method=distance_method)
            matrix[i][j] = distance
            matrix[j][i] = distance
    return matrix


def _matrix_vector_product(matrix: Sequence[Sequence[float]], vector: Sequence[float]) -> list[float]:
    try:
        numpy = importlib.import_module("numpy")
    except ImportError:
        pass
    else:
        return [float(value) for value in (numpy.asarray(matrix, dtype=float) @ numpy.asarray(vector, dtype=float)).tolist()]
    return [sum(float(value) * float(vector[col_index]) for col_index, value in enumerate(row)) for row in matrix]


def _transpose_matrix(matrix: Sequence[Sequence[float]]) -> list[list[float]]:
    if not matrix:
        return []
    return [
        [float(matrix[row_index][col_index]) for row_index in range(len(matrix))]
        for col_index in range(len(matrix[0]))
    ]


def _matrix_product(left: Sequence[Sequence[float]], right: Sequence[Sequence[float]]) -> list[list[float]]:
    try:
        numpy = importlib.import_module("numpy")
    except ImportError:
        pass
    else:
        return [
            [float(value) for value in row]
            for row in (numpy.asarray(left, dtype=float) @ numpy.asarray(right, dtype=float)).tolist()
        ]
    if not left:
        return []
    shared_width = len(left[0])
    right_columns = _transpose_matrix(right)
    if shared_width == 0 or not right_columns:
        return [[0.0] * (len(right[0]) if right else 0) for _ in left]
    return [
        [
            sum(float(left_row[index]) * float(right_column[index]) for index in range(shared_width))
            for right_column in right_columns
        ]
        for left_row in left
    ]


def _path_sequence_cost(sequence: Sequence[int], cost_matrix: Sequence[Sequence[float]]) -> float:
    if len(sequence) <= 1:
        return 0.0
    total = 0.0
    for current_index, next_index in zip(sequence[:-1], sequence[1:]):
        step_cost = float(cost_matrix[current_index][next_index])
        if not math.isfinite(step_cost):
            return float("inf")
        total += step_cost
    return total


def _two_opt_open_path(sequence: Sequence[int], cost_matrix: Sequence[Sequence[float]]) -> list[int]:
    if len(sequence) < 4:
        return list(sequence)
    best_sequence = list(sequence)
    best_cost = _path_sequence_cost(best_sequence, cost_matrix)
    improved = True
    while improved:
        improved = False
        candidate_best_sequence = best_sequence
        candidate_best_cost = best_cost
        for start_index in range(1, len(best_sequence) - 2):
            for end_index in range(start_index + 1, len(best_sequence)):
                candidate_sequence = (
                    best_sequence[:start_index]
                    + list(reversed(best_sequence[start_index:end_index + 1]))
                    + best_sequence[end_index + 1:]
                )
                candidate_cost = _path_sequence_cost(candidate_sequence, cost_matrix)
                if candidate_cost + 1e-12 < candidate_best_cost:
                    candidate_best_sequence = candidate_sequence
                    candidate_best_cost = candidate_cost
                    improved = True
        best_sequence = candidate_best_sequence
        best_cost = candidate_best_cost
    return best_sequence


def _solve_linear_system(a: list[list[float]], b: list[float]) -> list[float] | None:
    n = len(b)
    aug = [list(a[i]) + [b[i]] for i in range(n)]
    for col in range(n):
        max_row = col
        for row in range(col + 1, n):
            if abs(aug[row][col]) > abs(aug[max_row][col]):
                max_row = row
        aug[col], aug[max_row] = aug[max_row], aug[col]
        if abs(aug[col][col]) < 1e-12:
            return None
        for row in range(col + 1, n):
            factor = aug[row][col] / aug[col][col]
            for j in range(col, n + 1):
                aug[row][j] -= factor * aug[col][j]
    result = [0.0] * n
    for i in range(n - 1, -1, -1):
        result[i] = aug[i][n]
        for j in range(i + 1, n):
            result[i] -= aug[i][j] * result[j]
        result[i] /= aug[i][i] if abs(aug[i][i]) > 1e-12 else 1.0
    return result


def _solve_linear_system_with_regularization(
    a: list[list[float]],
    b: list[float],
    diagonal_jitter: float = 1e-8,
) -> list[float] | None:
    solution = _solve_linear_system(a, b)
    if solution is not None:
        return solution
    regularized = [list(row) for row in a]
    for index in range(min(len(regularized), len(b))):
        regularized[index][index] += diagonal_jitter
    return _solve_linear_system(regularized, b)


def _invert_matrix(matrix: list[list[float]]) -> list[list[float]] | None:
    size = len(matrix)
    if size == 0:
        return []
    augmented = [
        list(matrix[row_index]) + [1.0 if row_index == col_index else 0.0 for col_index in range(size)]
        for row_index in range(size)
    ]
    for pivot_index in range(size):
        best_row = max(range(pivot_index, size), key=lambda row_index: abs(augmented[row_index][pivot_index]))
        if abs(augmented[best_row][pivot_index]) < 1e-12:
            return None
        augmented[pivot_index], augmented[best_row] = augmented[best_row], augmented[pivot_index]
        pivot_value = augmented[pivot_index][pivot_index]
        for col_index in range(2 * size):
            augmented[pivot_index][col_index] /= pivot_value
        for row_index in range(size):
            if row_index == pivot_index:
                continue
            factor = augmented[row_index][pivot_index]
            if abs(factor) < 1e-12:
                continue
            for col_index in range(2 * size):
                augmented[row_index][col_index] -= factor * augmented[pivot_index][col_index]
    return [row[size:] for row in augmented]


def _invert_matrix_with_regularization(
    matrix: list[list[float]],
    diagonal_jitter: float = 1e-8,
) -> list[list[float]] | None:
    inverse = _invert_matrix(matrix)
    if inverse is not None:
        return inverse
    regularized = [list(row) for row in matrix]
    for index in range(len(regularized)):
        regularized[index][index] += diagonal_jitter
    return _invert_matrix(regularized)


def _matrix_rank(matrix: list[list[float]], tolerance: float = 1e-10) -> int:
    try:
        numpy = importlib.import_module("numpy")
    except ImportError:
        working = [list(row) for row in matrix]
        rank = 0
        row_count = len(working)
        col_count = len(working[0]) if working else 0
        pivot_row = 0
        for pivot_col in range(col_count):
            best_row = max(range(pivot_row, row_count), key=lambda row_index: abs(working[row_index][pivot_col]), default=pivot_row)
            if pivot_row >= row_count or abs(working[best_row][pivot_col]) <= tolerance:
                continue
            working[pivot_row], working[best_row] = working[best_row], working[pivot_row]
            pivot_value = working[pivot_row][pivot_col]
            for row_index in range(pivot_row + 1, row_count):
                factor = working[row_index][pivot_col] / pivot_value
                for col_index in range(pivot_col, col_count):
                    working[row_index][col_index] -= factor * working[pivot_row][col_index]
            rank += 1
            pivot_row += 1
            if pivot_row >= row_count:
                break
        return rank
    return int(numpy.linalg.matrix_rank(numpy.asarray(matrix, dtype=float), tol=tolerance))


def _matrix_pseudoinverse(matrix: list[list[float]], tolerance: float = 1e-15) -> list[list[float]] | None:
    try:
        numpy = importlib.import_module("numpy")
    except ImportError:
        return None
    array = numpy.asarray(matrix, dtype=float)
    pseudoinverse = numpy.linalg.pinv(array, rcond=tolerance)
    return [[float(value) for value in row] for row in pseudoinverse.tolist()]


def _moran_on_residuals(
    residuals: list[float],
    distance_matrix: list[list[float]],
    k: int,
) -> float:
    n = len(residuals)
    if n < 2:
        return 0.0
    mean_r = sum(residuals) / n
    centered = [r - mean_r for r in residuals]
    var_sum = sum(c * c for c in centered)
    if var_sum < 1e-12:
        return 0.0
    w_sum = 0.0
    cross_sum = 0.0
    for i in range(n):
        dists = [(j, distance_matrix[i][j]) for j in range(n) if j != i]
        neighbors = nsmallest(k, dists, key=lambda x: x[1])
        for j, _ in neighbors:
            w_sum += 1.0
            cross_sum += centered[i] * centered[j]
    return (n / w_sum) * (cross_sum / var_sum) if w_sum > 0 else 0.0


def _douglas_peucker(coords: list[Coordinate], tolerance: float) -> list[Coordinate]:
    if len(coords) <= 2:
        return list(coords)
    max_dist = 0.0
    max_idx = 0
    start, end = coords[0], coords[-1]
    for i in range(1, len(coords) - 1):
        d = _perpendicular_distance(coords[i], start, end)
        if d > max_dist:
            max_dist = d
            max_idx = i
    if max_dist > tolerance:
        left = _douglas_peucker(coords[:max_idx + 1], tolerance)
        right = _douglas_peucker(coords[max_idx:], tolerance)
        return left[:-1] + right
    return [coords[0], coords[-1]]


def _douglas_peucker_indices(coords: list[Coordinate], tolerance: float) -> list[int]:
    if len(coords) <= 2:
        return list(range(len(coords)))
    indices = [0, len(coords) - 1]
    _dp_recurse(coords, 0, len(coords) - 1, tolerance, indices)
    return sorted(indices)


def _dp_recurse(coords: list[Coordinate], start: int, end: int, tolerance: float, indices: list[int]) -> None:
    if end - start <= 1:
        return
    max_dist = 0.0
    max_idx = start
    for i in range(start + 1, end):
        d = _perpendicular_distance(coords[i], coords[start], coords[end])
        if d > max_dist:
            max_dist = d
            max_idx = i
    if max_dist > tolerance:
        indices.append(max_idx)
        _dp_recurse(coords, start, max_idx, tolerance, indices)
        _dp_recurse(coords, max_idx, end, tolerance, indices)


def _perpendicular_distance(point: Coordinate, line_start: Coordinate, line_end: Coordinate) -> float:
    dx = line_end[0] - line_start[0]
    dy = line_end[1] - line_start[1]
    length_sq = dx * dx + dy * dy
    if length_sq < 1e-24:
        return math.hypot(point[0] - line_start[0], point[1] - line_start[1])
    t = max(0.0, min(1.0, ((point[0] - line_start[0]) * dx + (point[1] - line_start[1]) * dy) / length_sq))
    proj_x = line_start[0] + t * dx
    proj_y = line_start[1] + t * dy
    return math.hypot(point[0] - proj_x, point[1] - proj_y)


def _densify_coordinates(coords: list[Coordinate], max_length: float) -> list[Coordinate]:
    if len(coords) < 2:
        return list(coords)
    result: list[Coordinate] = [coords[0]]
    for i in range(1, len(coords)):
        start = coords[i - 1]
        end = coords[i]
        seg_len = math.hypot(end[0] - start[0], end[1] - start[1])
        if seg_len > max_length:
            n_segments = math.ceil(seg_len / max_length)
            for s in range(1, n_segments):
                t = s / n_segments
                result.append((start[0] + t * (end[0] - start[0]), start[1] + t * (end[1] - start[1])))
        result.append(end)
    return result


def _chaikin_smooth(coords: list[Coordinate], is_closed: bool = False) -> list[Coordinate]:
    if len(coords) < 3:
        return list(coords)
    result: list[Coordinate] = []
    n = len(coords)
    start = 0 if is_closed else 0
    end = n if is_closed else n - 1
    if not is_closed:
        result.append(coords[0])
    for i in range(start, end):
        p0 = coords[i]
        p1 = coords[(i + 1) % n]
        q = (0.75 * p0[0] + 0.25 * p1[0], 0.75 * p0[1] + 0.25 * p1[1])
        r = (0.25 * p0[0] + 0.75 * p1[0], 0.25 * p0[1] + 0.75 * p1[1])
        result.append(q)
        result.append(r)
    if not is_closed:
        result.append(coords[-1])
    if is_closed and result:
        result.append(result[0])
    return result


_GEOHASH_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"


def _geohash_encode(latitude: float, longitude: float, precision: int) -> str:
    lat_range = [-90.0, 90.0]
    lon_range = [-180.0, 180.0]
    is_longitude = True
    bits = 0
    char_index = 0
    result: list[str] = []
    while len(result) < precision:
        if is_longitude:
            mid = (lon_range[0] + lon_range[1]) / 2.0
            if longitude >= mid:
                char_index = char_index * 2 + 1
                lon_range[0] = mid
            else:
                char_index = char_index * 2
                lon_range[1] = mid
        else:
            mid = (lat_range[0] + lat_range[1]) / 2.0
            if latitude >= mid:
                char_index = char_index * 2 + 1
                lat_range[0] = mid
            else:
                char_index = char_index * 2
                lat_range[1] = mid
        is_longitude = not is_longitude
        bits += 1
        if bits == 5:
            result.append(_GEOHASH_BASE32[char_index])
            bits = 0
            char_index = 0
    return "".join(result)


__all__ = ["Bounds", "GeoPromptFrame"]