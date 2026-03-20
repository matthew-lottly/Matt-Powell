# Release Notes — 0.1.12

## Summary

This release completes the next roadmap pass after 0.1.11. Corridor reach now supports scoring and network-style distance, zone fit scoring supports grouped rankings, clustering now has cluster-count diagnostics and recommendations, and overlay summaries can be grouped and normalized against the right-side geometries.

## Corridor Reach

`GeoPromptFrame.corridor_reach(...)` now supports:

- `distance_mode="direct"` or `distance_mode="network"`
- `score_mode="distance"`, `"strength"`, `"alignment"`, or `"combined"`
- `weight_column=` for corridor-weighted scoring
- `preferred_bearing=` for direction-aware corridor ranking
- detailed per-corridor score output in `corridor_scores_*`

## Zone Fit Scoring

`GeoPromptFrame.zone_fit_score(...)` now supports grouped rankings through:

- `group_by=`
- `group_aggregation=`
- `top_n=`

This allows best-group outputs alongside best-zone outputs.

## Cluster Diagnostics

Added:

- `GeoPromptFrame.cluster_diagnostics(...)`
- `GeoPromptFrame.recommend_cluster_count(...)`

These provide SSE, silhouette summaries, cluster-size breakdowns, and recommended `k` values.

## Grouped Overlay Summaries

`GeoPromptFrame.overlay_summary(...)` now supports:

- `group_by=` for grouped overlay summaries
- `normalize_by="left" | "right" | "both"`
- `top_n_groups=` for limiting returned group summaries

## Benchmark Coverage

The comparison harness now benchmarks:

- `cluster_diagnostics(...)`
- grouped `overlay_summary(...)`

## Validation

- 64 tests passing
- comparison report regenerated
- package version bumped to `0.1.12`
