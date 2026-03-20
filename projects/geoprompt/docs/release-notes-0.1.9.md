# Release Notes — 0.1.9

## Summary

This release adds three major new spatial analysis tools (corridor reach, zone fit scoring, centroid clustering), two new equations (gravity model, accessibility index), two new geometry helpers (convex hull, envelope), a full suite of frame utilities, and IO improvements. The test suite expanded from 31 to 53 tests.

## New Tools

### `GeoPromptFrame.corridor_reach(...)`

Find features within a distance of line corridors. Returns corridor ids, distance summaries, total corridor length, and optional target aggregations. Supports `inner` and `left` modes.

### `GeoPromptFrame.zone_fit_score(...)`

Score how well each feature fits candidate zones using containment (40%), overlap (30%), and area similarity (30%) components, weighted by distance. Returns the best zone assignment and per-zone score breakdowns.

### `GeoPromptFrame.centroid_cluster(...)`

Deterministic k-means clustering on feature centroids. Assigns cluster ids, cluster centers, and cluster distances. Uses evenly-spaced seed initialization and converges within a configurable iteration limit.

## New Equations

### `gravity_model(...)`

Classic gravity/Huff-style interaction: `origin_weight * destination_weight / distance^friction`. Returns infinity for zero-distance pairs.

### `accessibility_index(...)`

Cumulative accessibility: `sum(weight_i / distance_i^friction)` across a set of weighted destinations.

## New Geometry Helpers

### `geometry_envelope(...)`

Returns the bounding-box polygon (axis-aligned rectangle) for any geometry.

### `geometry_convex_hull(...)`

Pure-Python convex hull using Andrew's monotone chain algorithm. Works on points, lines, and polygons.

## Frame Utilities

- `select(*columns)` — Column projection; always keeps the geometry column.
- `rename_columns(mapping)` — Rename columns via a dict mapping.
- `filter(predicate)` — Row filtering with a callable or boolean mask.
- `sort(by, descending=False)` — Sort rows by a column.
- `describe()` — Summary stats (count, min, max, mean, sum) for numeric columns.
- `envelopes()` — Replace geometries with their bounding-box envelopes.
- `convex_hulls()` — Replace geometries with their convex hulls.
- `gravity_table(origin_weight, destination_weight)` — Pairwise gravity-model scoring.
- `accessibility_scores(targets, weight_column)` — Per-origin accessibility against a target frame.
- `__repr__` — Displays row count, column count, and CRS.
- `__getitem__` — `frame["column"]` returns a list of values.

## IO Improvements

- `read_geojson(...)` now accepts a `dict` payload for in-memory GeoJSON loading.
- Added `frame_to_records_flat(...)` for exporting records with geometry replaced by centroid, bounds, and type columns.

## Test Coverage

53 tests (up from 31), covering all new tools, equations, geometry helpers, frame utilities, and IO features.
