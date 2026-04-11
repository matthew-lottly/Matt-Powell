# Changelog

## 0.1.8

- Added 10 new equation-driven analysis tools for drought stress, heat island intensity, school and healthcare access, food desert risk, digital divide, wildfire risk, emergency response, infrastructure lifecycle, and adaptive capacity.
- Added 40 new equation functions and dedicated coverage in `tests/test_new_equations.py`.
- Added independent parity checks for tool outputs in `tests/test_tools_open_source_parity.py`.
- Improved CLI analyze coverage so all registered tools are exercised end to end.
- Refreshed documentation with cleaner Mermaid system/data-flow graphs and an extended equation catalog.
- Cleaned repository artifacts by ignoring generated `outputs/` files and removing tracked generated build metadata.

## 0.1.6

- Improved `nearest_neighbors(...)` so small-`k` lookups do not sort the full candidate list.
- Added `GeoPromptFrame.nearest_join(...)` for ranked nearest-feature joins with optional `max_distance` filtering and `left` join behavior.
- Added `GeoPromptFrame.assign_nearest(...)` for target-focused nearest-origin allocation workflows.
- Added `GeoPromptFrame.summarize_assignments(...)` for per-origin assignment counts, assigned ids, distance summaries, and target aggregations.
- Reduced join-output overhead by skipping redundant geometry normalization for already-normalized derived rows.

## 0.1.5

- Optimized the Shapely-backed overlay path by caching Shapely module loading inside `overlay.py`.
- Replaced the GeoJSON reshaping step in `geometry_to_shapely(...)` with direct Point, LineString, and Polygon construction.
- Improved `clip(...)` runtime enough to move ahead of the reference path in the current benchmark and stress corpora while keeping all comparison parity flags green.

## 0.1.4

- Added `GeoPromptFrame.buffer_join(...)` for service-area style joins driven by buffered geometries.
- Added `GeoPromptFrame.coverage_summary(...)` for per-zone counts, covered ids, and target aggregation rollups.
- Kept the recently added `buffer(...)`, `within_distance(...)`, `query_radius(...)`, and `proximity_join(...)` tools in the public API.
- Expanded tests and docs for the service-area workflow surface.

## 0.1.3

- Added `GeoPromptFrame.buffer(...)`.
- Added `GeoPromptFrame.within_distance(...)`.
- Improved `clip(...)` with prepared-geometry checks.
- Published the `0.1.3` release to PyPI.

## 0.1.2

- Added `query_radius(...)` and `proximity_join(...)`.
- Improved benchmark coverage with a generated stress corpus.

## 0.1.1

- Fixed PyPI trusted publishing configuration.

## 0.1.0

- Initial public Geoprompt package release.