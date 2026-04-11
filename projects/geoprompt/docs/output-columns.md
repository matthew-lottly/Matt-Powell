# Output Columns Reference

This document describes the exact columns added or returned by each `GeoPromptFrame` method. Use it to know what to expect in results without inspecting source code.

---

## Join Methods

All join methods produce a new `GeoPromptFrame`. Column collision rules: if a right-side column name already exists in the left frame, the right-side copy is renamed with the suffix (e.g. `name` → `name_right`).

### `nearest_join(other, k, how, lsuffix, rsuffix, max_distance, distance_method)`

Joins each left row to its `k` nearest right rows by centroid distance.

| Column | Type | Description |
|---|---|---|
| *(all left columns)* | — | Preserved as-is |
| *(right non-geometry columns)* | — | Copied, suffixed with `_{rsuffix}` on collision |
| `{other.geometry_column}_{rsuffix}` | geometry | Right geometry |
| `distance_{rsuffix}` | float / None | Centroid distance to matched right row |
| `distance_method_{rsuffix}` | str | Distance method used (`"euclidean"` or `"haversine"`) |
| `nearest_rank_{rsuffix}` | int / None | Match rank (1 = closest); None on unmatched left rows in `how="left"` |

> With `k > 1`, each left row produces up to `k` output rows (one per match).

---

### `assign_nearest(targets, how, max_distance, distance_method, origin_suffix)`

Thin wrapper around `nearest_join(k=1)` — reverses the join direction so targets are matched to their nearest origin.

Output columns are identical to `nearest_join`, with `rsuffix=origin_suffix` (default `"origin"`).

---

### `proximity_join(other, max_distance, how, lsuffix, rsuffix, distance_method)`

Joins each left row to all right rows within `max_distance`. One output row per (left, right) pair.

| Column | Type | Description |
|---|---|---|
| *(all left columns)* | — | Preserved as-is |
| *(right non-geometry columns)* | — | Copied, suffixed with `_{rsuffix}` on collision |
| `{other.geometry_column}_{rsuffix}` | geometry | Right geometry |
| `distance_{rsuffix}` | float / None | Centroid distance to matched right row |
| `distance_method_{rsuffix}` | str | Distance method used |

---

### `buffer_join(other, distance, how, lsuffix, rsuffix, resolution)`

Expands each left geometry by `distance` (requires Shapely) and joins to all right geometries that intersect the buffer.

| Column | Type | Description |
|---|---|---|
| *(all left columns)* | — | Preserved as-is |
| `buffer_geometry_{lsuffix}` | geometry / None | The buffer polygon used for matching |
| `buffer_distance_{lsuffix}` | float | Buffer radius applied |
| *(right non-geometry columns)* | — | Copied, suffixed with `_{rsuffix}` on collision |
| `{other.geometry_column}_{rsuffix}` | geometry / None | Right geometry |

---

### `spatial_join(other, predicate, how, lsuffix, rsuffix)`

Geometry-predicate join (`"intersects"`, `"within"`, `"contains"`). Requires Shapely for non-trivial geometries.

| Column | Type | Description |
|---|---|---|
| *(all left columns)* | — | Preserved as-is |
| *(right non-geometry columns)* | — | Copied, suffixed with `_{rsuffix}` on collision |
| `{other.geometry_column}_{rsuffix}` | geometry / None | Right geometry |
| `join_predicate_{rsuffix}` | str | Predicate applied (`"intersects"`, `"within"`, or `"contains"`) |

---

### `overlay_intersections(other, lsuffix, rsuffix)`

Computes geometric intersections of all crossing left/right geometry pairs. The left geometry column is replaced with the intersection geometry.

| Column | Type | Description |
|---|---|---|
| *(all left columns, geometry replaced)* | — | `geometry_column` holds the intersection polygon |
| *(right non-geometry columns)* | — | Copied, suffixed with `_{rsuffix}` on collision |
| `{other.geometry_column}_{rsuffix}` | geometry | Original right geometry |

---

## Aggregation / Summary Methods

These methods return a new `GeoPromptFrame` with one row per origin, summarising matched targets.

### `summarize_assignments(targets, origin_id_column, target_id_column, aggregations, how, max_distance, distance_method, assignment_suffix)`

For each origin, finds all targets whose nearest origin is this one and summarises the assignment.

| Column | Type | Description |
|---|---|---|
| *(all origin columns)* | — | Preserved as-is |
| `{target_id_column}s_{assignment_suffix}` | list[str] | IDs of all assigned targets |
| `count_{assignment_suffix}` | int | Number of assigned targets |
| `distance_method_{assignment_suffix}` | str | Distance method used |
| `distance_min_{assignment_suffix}` | float / None | Minimum assignment distance |
| `distance_max_{assignment_suffix}` | float / None | Maximum assignment distance |
| `distance_mean_{assignment_suffix}` | float / None | Mean assignment distance |
| `{col}_{op}_{assignment_suffix}` | any | One column per `aggregations` entry (e.g. `demand_sum_assigned`) |

---

### `coverage_summary(targets, predicate, target_id_column, aggregations, rsuffix)`

For each row, counts targets that satisfy the spatial predicate.

| Column | Type | Description |
|---|---|---|
| *(all self columns)* | — | Preserved as-is |
| `{target_id_column}s_{rsuffix}` | list[str] | IDs of all matched targets |
| `count_{rsuffix}` | int | Number of matched targets |
| `predicate_{rsuffix}` | str | Predicate used |
| `{col}_{op}_{rsuffix}` | any | One column per `aggregations` entry |

---

## Spatial Filter Methods

### `query_radius(anchor, max_distance, id_column, include_anchor, distance_method)`

Returns a filtered `GeoPromptFrame` with rows within `max_distance` of the anchor, sorted by distance.

| Column | Type | Description |
|---|---|---|
| *(all row columns)* | — | Preserved as-is |
| `distance` | float | Distance to anchor |
| `distance_method` | str | Distance method used |
| `anchor_id` | str | Anchor ID *(only present when anchor is specified by ID string)* |

---

### `within_distance(...)`

Returns a `list[bool]` mask — one per row — not a `GeoPromptFrame`. No output columns.

---

### `query_bounds(min_x, min_y, max_x, max_y, mode)`

Returns a filtered `GeoPromptFrame` preserving all columns of matching rows unchanged.

---

## Analysis Table Methods

These return `list[Record]` (plain dicts), not a `GeoPromptFrame`.

### `nearest_neighbors(id_column, k, distance_method)` → `list[Record]`

| Column | Type | Description |
|---|---|---|
| `origin` | any | Origin row ID |
| `neighbor` | any | Neighbor row ID |
| `distance` | float | Centroid distance |
| `origin_geometry_type` | str | Geometry type of origin |
| `neighbor_geometry_type` | str | Geometry type of neighbor |
| `rank` | int | Rank (1 = closest) |
| `distance_method` | str | Distance method used |

---

### `interaction_table(origin_weight, destination_weight, id_column, ...)` → `list[Record]`

| Column | Type | Description |
|---|---|---|
| `origin` | any | Origin row ID |
| `destination` | any | Destination row ID |
| `distance` | float | Centroid distance |
| `interaction` | float | Gravity-model interaction score |
| `distance_method` | str | Distance method used |
| `directional_alignment` | float | *(Only present when `preferred_bearing` is set)* |

---

### `area_similarity_table(id_column, ...)` → `list[Record]`

| Column | Type | Description |
|---|---|---|
| `origin` | any | Origin row ID |
| `destination` | any | Destination row ID |
| `area_similarity` | float | Area-weighted similarity score |
| `distance_method` | str | Distance method used |

---

## Scalar / Vector Methods

| Method | Returns | Description |
|---|---|---|
| `neighborhood_pressure(...)` | `list[float]` | One float per row — cumulative influence score from all neighbors |
| `anchor_influence(...)` | `list[float]` | One float per row — influence score relative to a single anchor |
| `corridor_accessibility(...)` | `list[float]` | One float per row — corridor strength weighted by line length |
| `geometry_types()` | `list[str]` | Geometry type string per row |
| `geometry_lengths()` | `list[float]` | Geometry length per row |
| `geometry_areas()` | `list[float]` | Geometry area per row |
| `distance_matrix(...)` | `list[list[float]]` | N×N pairwise distance matrix |
| `centroid()` | `(float, float)` | Mean centroid of the frame |
| `bounds()` | `Bounds` | Bounding box of the frame |

---

## Suffix Defaults Quick Reference

| Method | lsuffix default | rsuffix default | assignment_suffix default |
|---|---|---|---|
| `nearest_join` | `"left"` | `"right"` | — |
| `assign_nearest` | — | `origin_suffix="origin"` | — |
| `proximity_join` | `"left"` | `"right"` | — |
| `buffer_join` | `"left"` | `"right"` | — |
| `spatial_join` | `"left"` | `"right"` | — |
| `overlay_intersections` | `"left"` | `"right"` | — |
| `summarize_assignments` | — | — | `"assigned"` |
| `coverage_summary` | — | `"covered"` | — |
