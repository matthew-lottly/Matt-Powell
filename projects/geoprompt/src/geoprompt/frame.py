"""Core spatial frame object and operations for geographic feature analysis.

GeoPromptFrame provides a dataclass-like geospatial table structure supporting
points, lines, and polygons. Built-in operations include spatial joins, network
analysis, distance-based queries, and custom spatial equations without external
dependencies (geometry engines like Shapely/GeoPandas are opt-in via methods).
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from heapq import nsmallest
from typing import Any, Iterable, Literal, Sequence

from .equations import DistanceMethod, area_similarity, coordinate_distance, corridor_strength, directional_alignment, prompt_influence, prompt_interaction
from .geometry import Geometry, geometry_area, geometry_bounds, geometry_centroid, geometry_contains, geometry_distance, geometry_intersects, geometry_intersects_bounds, geometry_length, geometry_type, geometry_within, geometry_within_bounds, normalize_geometry, transform_geometry
from .overlay import buffer_geometries, clip_geometries, dissolve_geometries, overlay_intersections


Record = dict[str, Any]
BoundsQueryMode = Literal["intersects", "within", "centroid"]
SpatialJoinPredicate = Literal["intersects", "within", "contains"]
SpatialJoinMode = Literal["inner", "left"]
AggregationName = Literal["sum", "mean", "min", "max", "first", "count"]


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
        """Create a GeoPromptFrame from a sequence of row dicts.

        Each row must contain a geometry value under ``geometry_column``.
        Geometries are normalised to the canonical internal representation on
        construction; GeoJSON dicts, WKT strings, and coordinate tuples are
        all accepted.

        Args:
            rows: Sequence of dicts, each representing one spatial feature.
            geometry_column: Name of the key that holds geometry data.
            crs: Optional CRS string (e.g. ``"EPSG:4326"``).  Used for
                consistency checks and reprojection — it does not transform
                coordinates on its own.
        """
        self.geometry_column = geometry_column
        self.crs = crs
        self._rows = [dict(row) for row in rows]
        for row in self._rows:
            row[self.geometry_column] = normalize_geometry(row[self.geometry_column])

    @classmethod
    def from_records(cls, records: Iterable[Record], geometry: str = "geometry", crs: str | None = None) -> "GeoPromptFrame":
        """Construct a frame from any iterable of row dicts.

        Convenience alternative to the constructor when the input is a
        generator or other lazy iterable that must be materialised first.

        Args:
            records: Iterable of row dicts.
            geometry: Geometry column name.
            crs: Optional CRS string.

        Returns:
            A new :class:`GeoPromptFrame`.
        """
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
        return frame

    def __len__(self) -> int:
        return len(self._rows)

    def __iter__(self):
        """Iterate over rows as dictionaries.

        Each row is a dict mapping column names to values (including the
        geometry column).
        """
        return iter(self._rows)

    @property
    def columns(self) -> list[str]:
        """Return the column names of the first row, or an empty list if the frame is empty."""
        return list(self._rows[0].keys()) if self._rows else []

    def head(self, count: int = 5) -> list[Record]:
        """Return the first ``count`` rows as a list of dicts.

        Args:
            count: Number of rows to return (default 5).

        Returns:
            List of row dicts, each a shallow copy.
        """
        return [dict(row) for row in self._rows[:count]]

    def to_records(self) -> list[Record]:
        """Return all rows as a list of shallow-copied dicts."""
        return [dict(row) for row in self._rows]

    def bounds(self) -> Bounds:
        """Return the bounding box of all geometries in the frame.

        Returns:
            :class:`Bounds` with ``min_x``, ``min_y``, ``max_x``, ``max_y``.
        """
        xs: list[float] = []
        ys: list[float] = []
        for row in self._rows:
            min_x, min_y, max_x, max_y = geometry_bounds(row[self.geometry_column])
            xs.extend([min_x, max_x])
            ys.extend([min_y, max_y])
        return Bounds(min_x=min(xs), min_y=min(ys), max_x=max(xs), max_y=max(ys))

    def centroid(self) -> Coordinate:
        """Return the mean centroid of all geometries as an ``(x, y)`` tuple."""
        centroids = [geometry_centroid(row[self.geometry_column]) for row in self._rows]
        xs = [coord[0] for coord in centroids]
        ys = [coord[1] for coord in centroids]
        return (sum(xs) / len(xs), sum(ys) / len(ys))

    def _centroids(self, rows: Sequence[Record] | None = None, geometry_column: str | None = None) -> list[Coordinate]:
        active_rows = rows if rows is not None else self._rows
        active_geometry_column = geometry_column or self.geometry_column
        return [geometry_centroid(row[active_geometry_column]) for row in active_rows]

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

    def distance_matrix(self, distance_method: DistanceMethod = "euclidean") -> list[list[float]]:
        """Return a full NxN pairwise distance matrix between all rows.

        **Note:** Computing distance matrices for large frames (100K+ rows) can
        consume significant memory (e.g., 100K rows = 80GB for float64 matrix).
        Consider using :meth:`nearest_neighbors` with a smaller ``k`` value or
        streaming approaches for large datasets.

        Args:
            distance_method: ``"euclidean"`` (coordinate units) or
                ``"haversine"`` (kilometres, expects lon/lat coordinates).

        Returns:
            List of N lists of N floats.  ``result[i][j]`` is the distance
            from row *i* to row *j*.
        """
        if len(self._rows) > 100000:
            raise MemoryError(
                f"Distance matrix requires ~{(len(self._rows) ** 2 * 8) // (1024**3)}GB for {len(self._rows)} rows. "
                "Consider nearest_neighbors() or streaming instead."
            )
        return [
            [
                geometry_distance(origin=row[self.geometry_column], destination=other[self.geometry_column], method=distance_method)
                for other in self._rows
            ]
            for row in self._rows
        ]

    def geometry_types(self) -> list[str]:
        """Return the geometry type string for each row (e.g. ``"Point"``, ``"Polygon"``)."""
        return [geometry_type(row[self.geometry_column]) for row in self._rows]

    def geometry_lengths(self) -> list[float]:
        """Return the geometry length for each row.

        For Points, length is 0.  For LineStrings, total arc length.
        For Polygons, perimeter length.
        """
        return [geometry_length(row[self.geometry_column]) for row in self._rows]

    def geometry_areas(self) -> list[float]:
        """Return the geometry area for each row.

        For Points and LineStrings, area is 0.  For Polygons, the
        absolute planar area in coordinate-unit\u00b2.
        """
        return [geometry_area(row[self.geometry_column]) for row in self._rows]

    def nearest_neighbors(
        self,
        id_column: str = "site_id",
        k: int = 1,
        distance_method: DistanceMethod = "euclidean",
    ) -> list[Record]:
        """Find the *k* nearest neighbors for every row within the same frame.

        Returns a flat list of records describing each (origin, neighbor) pair.
        For a frame with N rows and ``k=1`` the output has N records.

        Args:
            id_column: Column used as the feature identifier in result records.
            k: Number of nearest neighbors to find per origin (must be ≥ 1).
            distance_method: ``"euclidean"`` or ``"haversine"``.

        Returns:
            List of dicts with keys: ``origin``, ``neighbor``, ``distance``,
            ``origin_geometry_type``, ``neighbor_geometry_type``, ``rank``,
            ``distance_method``.
        """
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
        distance_method: DistanceMethod,
        max_distance: float | None = None,
    ) -> list[tuple[Record, float]]:
        candidates: list[tuple[Record, float]] = []
        for right_row, right_centroid in zip(right_rows, right_centroids, strict=True):
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
        distance_method: DistanceMethod = "euclidean",
    ) -> "GeoPromptFrame":
        """Join each left row to its ``k`` nearest rows in ``other``.

        Each left row produces up to *k* output rows (one per nearest-right
        match).  With ``how="left"``, left rows that have no match within
        ``max_distance`` are kept with ``None`` values for all right columns.

        Args:
            other: The right frame to match against.
            k: Number of nearest neighbors to return per left row.
            how: ``"inner"`` drops unmatched left rows; ``"left"`` keeps them.
            lsuffix: Suffix appended to colliding left column names.
            rsuffix: Suffix appended to colliding right column names and to the
                distance/rank columns added to the output.
            max_distance: Optional upper bound on distance.  Left rows with no
                right match within this distance are treated as unmatched.
            distance_method: ``"euclidean"`` or ``"haversine"``.

        Returns:
            New :class:`GeoPromptFrame`.  See *output-columns.md* for the full
            column spec.
        """
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
        joined_rows: list[Record] = []

        for left_row, left_centroid in zip(self._rows, left_centroids, strict=True):
            row_matches = self._nearest_row_matches(
                origin_centroid=left_centroid,
                right_rows=right_rows,
                right_centroids=right_centroids,
                k=k,
                distance_method=distance_method,
                max_distance=max_distance,
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
        distance_method: DistanceMethod = "euclidean",
        origin_suffix: str = "origin",
    ) -> "GeoPromptFrame":
        """Assign each target to its nearest origin in ``self``.

        This is the reverse of :meth:`nearest_join` — ``self`` contains the
        origins (e.g. service locations) and ``targets`` are the demand points
        to be assigned.  Each target row appears once in the output, merged
        with the nearest origin's columns.

        Args:
            targets: Frame of demand points to assign.
            how: ``"inner"`` drops unassigned targets; ``"left"`` keeps them.
            max_distance: Optional maximum assignment distance.
            distance_method: ``"euclidean"`` or ``"haversine"``.
            origin_suffix: Suffix appended to origin columns on name collision.

        Returns:
            New :class:`GeoPromptFrame` with one row per target.
        """
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
        distance_method: DistanceMethod = "euclidean",
        assignment_suffix: str = "assigned",
    ) -> "GeoPromptFrame":
        """Summarise how many targets are assigned to each origin.

        Each target is assigned to its single nearest origin.  The output has
        one row per origin, augmented with assignment counts, distance stats,
        and any custom aggregations over the assigned targets.

        Args:
            targets: Frame of demand points to assign.
            origin_id_column: ID column in ``self`` (origins).
            target_id_column: ID column in ``targets``.
            aggregations: Optional dict mapping target column names to an
                aggregation operation (``"sum"``, ``"mean"``, ``"min"``,
                ``"max"``, ``"first"``, ``"count"``).  Each produces a column
                named ``{col}_{op}_{assignment_suffix}``.
            how: ``"left"`` keeps origins with zero assignments;
                ``"inner"`` drops them.
            max_distance: Optional maximum assignment distance.
            distance_method: ``"euclidean"`` or ``"haversine"``.
            assignment_suffix: Suffix for all added summary columns.

        Returns:
            New :class:`GeoPromptFrame` with one row per origin.  See
            *output-columns.md* for the full column spec.
        """
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
        assignments: dict[str, list[tuple[Record, float]]] = {}

        for target_row, target_centroid in zip(target_rows, target_centroids, strict=True):
            row_matches = self._nearest_row_matches(
                origin_centroid=target_centroid,
                right_rows=self._rows,
                right_centroids=origin_centroids,
                k=1,
                distance_method=distance_method,
                max_distance=max_distance,
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

    def query_radius(
        self,
        anchor: str | Geometry | Coordinate,
        max_distance: float,
        id_column: str = "site_id",
        include_anchor: bool = False,
        distance_method: DistanceMethod = "euclidean",
    ) -> "GeoPromptFrame":
        """Return all rows within ``max_distance`` of an anchor, sorted by distance.

        Args:
            anchor: An ID string looked up in ``id_column``, a geometry dict,
                or a raw ``(x, y)`` coordinate tuple.
            max_distance: Radius threshold (inclusive).  Must be ≥ 0.
            id_column: Column used to look up string anchors.
            include_anchor: If the anchor is specified by ID, include its own
                row in the results.
            distance_method: ``"euclidean"`` or ``"haversine"``.

        Returns:
            New :class:`GeoPromptFrame` with a ``distance`` column appended,
            sorted closest-first.
        """
        if max_distance < 0:
            raise ValueError("max_distance must be zero or greater")

        anchor_geometry, anchor_id = self._resolve_anchor_geometry(anchor, id_column=id_column)
        anchor_centroid = geometry_centroid(anchor_geometry)

        rows: list[Record] = []
        for row in self._rows:
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
        return GeoPromptFrame(rows=rows, geometry_column=self.geometry_column, crs=self.crs)

    def within_distance(
        self,
        anchor: str | Geometry | Coordinate,
        max_distance: float,
        id_column: str = "site_id",
        include_anchor: bool = False,
        distance_method: DistanceMethod = "euclidean",
    ) -> list[bool]:
        """Return a boolean mask indicating which rows are within ``max_distance`` of the anchor.

        Args:
            anchor: An ID string, geometry dict, or ``(x, y)`` coordinate.
            max_distance: Distance threshold (inclusive).  Must be ≥ 0.
            id_column: Column used to look up string anchors.
            include_anchor: Whether to mark the anchor row itself as ``True``.
            distance_method: ``"euclidean"`` or ``"haversine"``.

        Returns:
            List of bools aligned with the frame rows.
        """
        if max_distance < 0:
            raise ValueError("max_distance must be zero or greater")

        anchor_geometry, anchor_id = self._resolve_anchor_geometry(anchor, id_column=id_column)
        anchor_centroid = geometry_centroid(anchor_geometry)
        centroids = self._centroids()

        return [
            False
            if anchor_id is not None and not include_anchor and id_column in row and str(row[id_column]) == anchor_id
            else coordinate_distance(anchor_centroid, centroid, method=distance_method) <= max_distance
            for row, centroid in zip(self._rows, centroids, strict=True)
        ]

    def proximity_join(
        self,
        other: "GeoPromptFrame",
        max_distance: float,
        how: SpatialJoinMode = "inner",
        lsuffix: str = "left",
        rsuffix: str = "right",
        distance_method: str = "euclidean",
    ) -> "GeoPromptFrame":
        """Join each left row to every right row within ``max_distance``.

        Unlike :meth:`nearest_join`, this can produce multiple output rows per
        left row — one for each right row within range.  Results are
        distance-sorted within each left group.

        Args:
            other: Right frame.
            max_distance: Distance threshold (inclusive).  Must be ≥ 0.
            how: ``"inner"`` drops left rows with no matches;
                ``"left"`` keeps them with ``None`` right values.
            lsuffix: Suffix for colliding left columns.
            rsuffix: Suffix for colliding right columns and for the added
                ``distance_{rsuffix}`` column.
            distance_method: ``"euclidean"`` or ``"haversine"``.

        Returns:
            New :class:`GeoPromptFrame`.
        """
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
        joined_rows: list[Record] = []

        for left_row, left_centroid in zip(self._rows, left_centroids, strict=True):
            row_matches: list[tuple[Record, float]] = []
            for right_row, right_centroid in zip(right_rows, right_centroids, strict=True):
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
        """Return a new frame with each geometry replaced by its buffer polygon.

        Requires Shapely (``pip install -e .[overlay]``).

        Args:
            distance: Buffer radius in coordinate units.  Must be ≥ 0.
            resolution: Number of segments used to approximate each quarter
                circle (higher = smoother buffer polygon, default 16).

        Returns:
            New :class:`GeoPromptFrame` where each row's geometry is the
            expanded buffer shape.
        """
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
        return GeoPromptFrame(rows=rows, geometry_column=self.geometry_column, crs=self.crs)

    def buffer_join(
        self,
        other: "GeoPromptFrame",
        distance: float,
        how: SpatialJoinMode = "inner",
        lsuffix: str = "left",
        rsuffix: str = "right",
        resolution: int = 16,
    ) -> "GeoPromptFrame":
        """Join by expanding each left geometry to a buffer and intersecting with ``other``.

        Useful for proximity queries on polygon or line geometries where
        centroid-based distance does not capture the true footprint.
        Requires Shapely (``pip install -e .[overlay]``).

        Args:
            other: Right frame.
            distance: Buffer radius.  Must be ≥ 0.
            how: ``"inner"`` or ``"left"``.
            lsuffix: Suffix for colliding left columns and for the added
                ``buffer_geometry_{lsuffix}`` / ``buffer_distance_{lsuffix}`` columns.
            rsuffix: Suffix for colliding right column names.
            resolution: Buffer polygon resolution (default 16).

        Returns:
            New :class:`GeoPromptFrame`.
        """
        if distance < 0:
            raise ValueError("distance must be zero or greater")
        if how not in {"inner", "left"}:
            raise ValueError("how must be 'inner' or 'left'")
        if self.crs and other.crs and self.crs != other.crs:
            raise ValueError("frames must share the same CRS before buffer joins")

        right_rows = list(other._rows)
        right_columns = [column for column in other.columns if column != other.geometry_column]
        right_bounds = [geometry_bounds(row[other.geometry_column]) for row in right_rows]
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
                for right_row, right_bound in zip(right_rows, right_bounds, strict=True):
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

        return GeoPromptFrame(rows=joined_rows, geometry_column=self.geometry_column, crs=self.crs or other.crs)

    def coverage_summary(
        self,
        targets: "GeoPromptFrame",
        predicate: SpatialJoinPredicate = "intersects",
        target_id_column: str = "site_id",
        aggregations: dict[str, AggregationName] | None = None,
        rsuffix: str = "covered",
    ) -> "GeoPromptFrame":
        """Count targets whose geometry satisfies a predicate with each self geometry.

        The output has one row per ``self`` row with a ``count_{rsuffix}``
        column and a list of matching target IDs.

        Args:
            targets: Frame of target features to test against.
            predicate: Spatial relationship to test — ``"intersects"``
                (default), ``"within"``, or ``"contains"``.
            target_id_column: ID column in ``targets``.
            aggregations: Optional column → operation dict for numeric
                aggregations over the matched targets.
            rsuffix: Suffix appended to all summary columns added to the output.

        Returns:
            New :class:`GeoPromptFrame` with coverage summary columns.
        """
        if self.crs and targets.crs and self.crs != targets.crs:
            raise ValueError("frames must share the same CRS before coverage summaries")
        if predicate not in {"intersects", "within", "contains"}:
            raise ValueError(f"unsupported spatial join predicate: {predicate}")

        if targets._rows:
            targets._require_column(target_id_column)
        target_rows = list(targets._rows)
        target_bounds = [geometry_bounds(row[targets.geometry_column]) for row in target_rows]
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
            for target_row, target_bound in zip(target_rows, target_bounds, strict=True):
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

        return GeoPromptFrame(rows=rows, geometry_column=self.geometry_column, crs=self.crs or targets.crs)

    def query_bounds(
        self,
        min_x: float,
        min_y: float,
        max_x: float,
        max_y: float,
        mode: BoundsQueryMode = "intersects",
    ) -> "GeoPromptFrame":
        """Return all rows whose geometry passes the bounding-box filter.

        Args:
            min_x: Left edge of the query box.
            min_y: Bottom edge of the query box.
            max_x: Right edge of the query box.
            max_y: Top edge of the query box.
            mode: ``"intersects"`` (default) — geometry bounding box overlaps
                the query box; ``"within"`` — geometry bounding box fits
                entirely inside; ``"centroid"`` — geometry centroid falls
                inside the query box.

        Returns:
            Filtered :class:`GeoPromptFrame` preserving all columns.
        """
        if min_x > max_x or min_y > max_y:
            raise ValueError("query bounds must be ordered from minimum to maximum")

        rows: list[Record] = []
        for row in self._rows:
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

        return GeoPromptFrame(rows=rows, geometry_column=self.geometry_column, crs=self.crs)

    def set_crs(self, crs: str, allow_override: bool = False) -> "GeoPromptFrame":
        """Attach a CRS label to the frame without transforming coordinates.

        Args:
            crs: CRS string to attach (e.g. ``"EPSG:4326"``).
            allow_override: If ``True``, replace an existing CRS.  If
                ``False`` (default), raises ``ValueError`` if CRS is already
                set to a different value.

        Returns:
            New :class:`GeoPromptFrame` with the CRS set.
        """
        if self.crs is not None and self.crs != crs and not allow_override:
            raise ValueError("frame already has a CRS; pass allow_override=True to replace it")
        return GeoPromptFrame(rows=self.to_records(), geometry_column=self.geometry_column, crs=crs)

    def to_crs(self, target_crs: str) -> "GeoPromptFrame":
        """Reproject all geometries to a different CRS.

        Requires PyProj (``pip install -e .[projection]``).
        The frame must already have a CRS set via :meth:`set_crs`.

        Args:
            target_crs: Destination CRS string (e.g. ``"EPSG:3857"``).

        Returns:
            New :class:`GeoPromptFrame` with reprojected coordinates and
            ``crs=target_crs``.
        """
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
    ) -> "GeoPromptFrame":
        """Join rows by a spatial predicate test on their geometries.

        Produces one output row per (left, right) pair whose geometries satisfy
        the predicate.  Uses bounding-box pre-filtering for efficiency.

        Args:
            other: Right frame.
            predicate: ``"intersects"`` (default), ``"within"``, or
                ``"contains"``.
            how: ``"inner"`` drops left rows with no match;
                ``"left"`` keeps them with ``None`` right values.
            lsuffix: Suffix for colliding left column names.
            rsuffix: Suffix for colliding right column names and for the added
                ``{geometry}_{rsuffix}`` and ``join_predicate_{rsuffix}`` columns.

        Returns:
            New :class:`GeoPromptFrame`.
        """
        if how not in {"inner", "left"}:
            raise ValueError("how must be 'inner' or 'left'")
        if self.crs and other.crs and self.crs != other.crs:
            raise ValueError("frames must share the same CRS before spatial joins")

        right_columns = [column for column in other.columns if column != other.geometry_column]
        joined_rows: list[Record] = []
        right_rows = list(other._rows)
        right_bounds = [geometry_bounds(row[other.geometry_column]) for row in right_rows]

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

        for left_row in self._rows:
            left_geometry = left_row[self.geometry_column]
            left_bounds = geometry_bounds(left_geometry)
            row_matches = []
            for right_row, right_bound in zip(right_rows, right_bounds, strict=True):
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
                joined_rows.append(merged_row)

            for right_row in row_matches:
                merged_row = dict(left_row)
                for column in right_columns:
                    target_name = column if column not in merged_row else f"{column}_{rsuffix}"
                    merged_row[target_name] = right_row[column]
                merged_row[f"{other.geometry_column}_{rsuffix}"] = right_row[other.geometry_column]
                merged_row[f"join_predicate_{rsuffix}"] = predicate
                joined_rows.append(merged_row)

        return GeoPromptFrame(rows=joined_rows, geometry_column=self.geometry_column, crs=self.crs or other.crs)

    def clip(self, mask: "GeoPromptFrame") -> "GeoPromptFrame":
        """Clip all geometries in ``self`` to the union of ``mask`` geometries.

        Requires Shapely (``pip install -e .[overlay]``).

        Args:
            mask: Frame whose geometries form the clip boundary.

        Returns:
            New :class:`GeoPromptFrame` with geometries trimmed to the mask.
            Rows whose geometry has no overlap with the mask are omitted.
        """
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
        return GeoPromptFrame(rows=rows, geometry_column=self.geometry_column, crs=self.crs or mask.crs)

    def overlay_intersections(
        self,
        other: "GeoPromptFrame",
        lsuffix: str = "left",
        rsuffix: str = "right",
    ) -> "GeoPromptFrame":
        """Compute geometric intersections of all crossing left/right geometry pairs.

        The left geometry column in the output is replaced by the intersection
        geometry.  Produces one row per intersecting (left, right) pair.
        Requires Shapely (``pip install -e .[overlay]``).

        Args:
            other: Right frame.
            lsuffix: Suffix for colliding left column names.
            rsuffix: Suffix for colliding right column names and for the added
                ``{geometry}_{rsuffix}`` column.

        Returns:
            New :class:`GeoPromptFrame` with intersection geometries.
        """
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
        return GeoPromptFrame(rows=rows, geometry_column=self.geometry_column, crs=self.crs or other.crs)

    def dissolve(
        self,
        by: str,
        aggregations: dict[str, AggregationName] | None = None,
    ) -> "GeoPromptFrame":
        """Group rows by a column and merge their geometries (union).

        Non-geometry columns without an aggregation rule are kept by taking the
        first value in the group.  Requires Shapely for polygon/line merging
        (``pip install -e .[overlay]``).

        Args:
            by: Column name to group by.
            aggregations: Optional dict mapping column names to aggregation
                operations (``"sum"``, ``"mean"``, ``"min"``, ``"max"``,
                ``"first"``, ``"count"``).

        Returns:
            New :class:`GeoPromptFrame` with one row per unique ``by`` value.
        """
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
        """Return a new frame with ``name`` added (or replaced) from ``values``.

        Args:
            name: Column name to add or overwrite.
            values: Sequence of values, one per row.  Must have the same
                length as the frame.

        Returns:
            New :class:`GeoPromptFrame` with the column added.
        """
        if len(values) != len(self._rows):
            raise ValueError("column length must match the frame length")
        rows = self.to_records()
        for row, value in zip(rows, values, strict=True):
            row[name] = value
        return GeoPromptFrame(rows=rows, geometry_column=self.geometry_column, crs=self.crs)

    def assign(self, **columns: Any) -> "GeoPromptFrame":
        """Return a new frame with one or more columns added or replaced.

        Each keyword argument is a new column.  The value can be:

        * A scalar — broadcast to every row.
        * A sequence of length ``len(self)`` — one value per row.
        * A callable ``(frame) -> value_or_sequence`` — evaluated against
          the *current* frame state (columns are applied sequentially, so
          later columns can reference earlier ones).

        Args:
            **columns: Column names mapped to scalars, sequences, or callables.

        Returns:
            New :class:`GeoPromptFrame`.
        """
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
        distance_method: DistanceMethod = "euclidean",
    ) -> list[float]:
        """Compute cumulative influence pressure on each row from all neighbors.

        Applies the :func:`~geoprompt.equations.prompt_influence` decay formula
        for every (row, neighbor) pair and sums the result.  Good for mapping
        congestion or density gradients.

        Args:
            weight_column: Column containing numeric weights (e.g. demand).
            scale: Distance decay scale parameter.
            power: Distance decay exponent.
            include_self: Whether a row contributes to its own pressure score.
            distance_method: ``"euclidean"`` or ``"haversine"``.

        Returns:
            List of floats aligned with the frame rows.
        """
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
        """Compute how strongly each row influences (or is influenced by) a single anchor.

        Uses the :func:`~geoprompt.equations.prompt_influence` formula with
        each row's weight and its distance to the anchor row.  Useful for
        ranked site scoring relative to a hub.

        Args:
            weight_column: Column containing numeric weights.
            anchor: ID of the anchor row in ``id_column``.
            id_column: Column used to locate the anchor.
            scale: Distance decay scale parameter.
            power: Distance decay exponent.
            distance_method: ``"euclidean"`` or ``"haversine"``.

        Returns:
            List of floats aligned with the frame rows.
        """
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
        """Compute accessibility scores weighted by corridor length and decay from an anchor.

        Uses :func:`~geoprompt.equations.corridor_strength`, which extends
        :func:`~geoprompt.equations.prompt_influence` by incorporating the
        physical length of each geometry (a LineString corridor).  Suitable for
        scoring road or utility corridor access from a hub.

        Args:
            weight_column: Column containing numeric weights (e.g. capacity).
            anchor: ID of the anchor row in ``id_column``.
            id_column: Column used to locate the anchor.
            scale: Distance decay scale parameter.
            power: Distance decay exponent.
            distance_method: ``"euclidean"`` or ``"haversine"``.

        Returns:
            List of floats aligned with the frame rows.
        """
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
        distance_method: DistanceMethod = "euclidean",
    ) -> list[Record]:
        """Return a pairwise table of area-weighted similarity scores.

        Uses :func:`~geoprompt.equations.area_similarity`.  Useful for
        comparing polygon features by both size and proximity.

        Args:
            id_column: Column used as the identifier in result records.
            scale: Distance decay scale parameter.
            power: Distance decay exponent.
            distance_method: ``"euclidean"`` or ``"haversine"``.

        Returns:
            List of dicts with keys: ``origin``, ``destination``,
            ``area_similarity``, ``distance_method``.
        """
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
        """Return a pairwise gravity-model interaction table.

        Applies :func:`~geoprompt.equations.prompt_interaction` to every
        (origin, destination) pair.  When ``preferred_bearing`` is set, a
        ``directional_alignment`` score is also included using
        :func:`~geoprompt.equations.directional_alignment`.

        Args:
            origin_weight: Column holding the origin mass/weight.
            destination_weight: Column holding the destination mass/weight.
            id_column: Column used as the identifier in result records.
            scale: Distance decay scale parameter.
            power: Distance decay exponent.
            preferred_bearing: Optional compass bearing (degrees from north,
                clockwise) used to score directional alignment.
            distance_method: ``"euclidean"`` or ``"haversine"``.

        Returns:
            List of dicts with keys: ``origin``, ``destination``, ``distance``,
            ``interaction``, ``distance_method``, and optionally
            ``directional_alignment``.
        """
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


__all__ = ["Bounds", "GeoPromptFrame"]