# Changelog

## 0.1.8

- Added `GeoPromptFrame.overlay_summary(...)` for per-feature intersection counts, overlap metrics, and proportional area or length summaries.
- Added regression coverage for overlay summaries in both `left` and `inner` modes.
- Evaluated an alternate `spatial_join(...)` predicate engine during this pass and kept the existing join path because it did not produce a clear enough benchmark win to justify shipping it.

## 0.1.7

- Added `GeoPromptFrame.catchment_competition(...)` for overlap-aware service-radius competition summaries, including exclusive, shared, won, and unserved target rollups.
- Added regression coverage for catchment competition workflows and inner-mode filtering.
- Added rectangle-oriented predicate fast paths in `geometry.py` so axis-aligned polygon workloads spend less time in the general segment-intersection path.
- Reduced redundant row normalization in more frame methods so `clip(...)`, `spatial_join(...)`, coverage summaries, and related workflows spend less time rebuilding already-normalized geometry rows.

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