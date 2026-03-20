# Changelog

## 0.1.12

- Extended `GeoPromptFrame.corridor_reach(...)` with `distance_mode` (`direct` or `network`), corridor scoring modes, optional corridor weights, and directional alignment support.
- Extended `GeoPromptFrame.zone_fit_score(...)` with grouped zone rankings through `group_by`, `group_aggregation`, and `top_n` controls.
- Added `GeoPromptFrame.cluster_diagnostics(...)` and `GeoPromptFrame.recommend_cluster_count(...)` for cluster-count exploration using SSE and silhouette summaries.
- Extended `GeoPromptFrame.overlay_summary(...)` with grouped overlay summaries and optional right-side normalization.
- Added benchmark coverage for grouped overlay summaries and cluster diagnostics.
- Expanded regression coverage for corridor scoring, network distance mode, grouped zone rankings, grouped overlay summaries, and cluster recommendation helpers.

## 0.1.11

- Added haversine support to `GeoPromptFrame.corridor_reach(...)` using local tangent-plane segment distance so lon/lat corridor screening can run in geographic mode.
- Added configurable `score_weights` and optional `preferred_bearing` support to `GeoPromptFrame.zone_fit_score(...)` so containment, overlap, size, access, and directional alignment can be weighted per workflow.
- Improved `GeoPromptFrame.centroid_cluster(...)` with deterministic id-based seed selection, stable tie handling, per-row cluster quality metrics, cluster SSE, cluster size, and silhouette summaries.
- Added benchmark coverage in `compare.py` for `centroid_cluster(...)`, `zone_fit_score(...)`, and `corridor_reach(...)` so the newer tools appear in the comparison report.
- Expanded regression coverage for haversine corridor reach, custom zone-fit weighting, alignment-aware scoring, deterministic clustering, and benchmark registration.

## 0.1.10

- Fixed `geometry_convex_hull(...)` so fully collinear inputs return a `LineString` hull instead of an invalid polygon shell.
- Tightened `corridor_reach(...)` semantics by rejecting unsupported distance methods instead of silently mixing Euclidean segment math with haversine labels.
- Fixed `gravity_model(...)` and `accessibility_index(...)` input validation so negative distances now raise clear errors.
- Updated `accessibility_index(...)` zero-distance handling to return infinite accessibility for positive-weight exact hits instead of an arbitrary large finite sentinel.
- Improved `GeoPromptFrame.filter(...)` to accept boolean sequences, not just boolean lists.
- Improved `GeoPromptFrame.sort(...)` so `None` values stay at the end in both ascending and descending sorts.
- Added targeted regression coverage for all of the above edge cases.

## 0.1.9

### New Tools
- Added `GeoPromptFrame.corridor_reach(...)` for route-like screening that finds features within a distance of line corridors, with distance and corridor length summaries.
- Added `GeoPromptFrame.zone_fit_score(...)` for scoring how well features fit zones using containment, overlap, area similarity, and configurable distance limits.
- Added `GeoPromptFrame.centroid_cluster(...)` for deterministic k-means centroid-distance clustering that assigns cluster ids, centers, and distances.

### New Equations
- Added `gravity_model(...)` for classic gravity/Huff-style interaction scoring between origin and destination weights scaled by distance friction.
- Added `accessibility_index(...)` for computing cumulative accessibility from a set of weighted destinations at given distances.

### New Geometry Helpers
- Added `geometry_envelope(...)` for computing a bounding-box polygon from any geometry.
- Added `geometry_convex_hull(...)` for computing the convex hull of any geometry using a pure-Python Andrew's monotone chain algorithm.

### Frame Utilities
- Added `GeoPromptFrame.select(...)` for column projection that keeps only named columns plus the geometry column.
- Added `GeoPromptFrame.rename_columns(...)` for renaming columns via a mapping dict.
- Added `GeoPromptFrame.filter(...)` for row filtering using a callable predicate or boolean mask.
- Added `GeoPromptFrame.sort(...)` for sorting rows by a named column with ascending or descending order.
- Added `GeoPromptFrame.describe()` for summary statistics (count, min, max, mean, sum) on numeric columns.
- Added `GeoPromptFrame.envelopes()` for replacing geometries with their bounding-box envelopes.
- Added `GeoPromptFrame.convex_hulls()` for replacing geometries with their convex hulls.
- Added `GeoPromptFrame.gravity_table(...)` for pairwise gravity-model interaction scoring.
- Added `GeoPromptFrame.accessibility_scores(...)` for per-origin cumulative accessibility against a target frame.
- Added `GeoPromptFrame.__repr__` so frames display row count, column count, and CRS.
- Added `GeoPromptFrame.__getitem__` so `frame["column"]` returns a list of column values.

### IO Improvements
- `read_geojson(...)` now accepts a dict payload in addition to file paths, so in-memory GeoJSON can be loaded directly.
- Added `frame_to_records_flat(...)` for flattening geometry into centroid, bounds, and type columns.

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