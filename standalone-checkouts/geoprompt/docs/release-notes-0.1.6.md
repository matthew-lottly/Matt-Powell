# Geoprompt 0.1.6 Release Notes

## Highlights

- Expanded the nearest-distance workflow from lookup into allocation and summary tools.
- Added assignment summaries so nearest-origin allocation can roll up into per-origin metrics directly.
- Kept comparison parity green while reducing redundant work in join-derived frame construction.

## What Changed

- Added `GeoPromptFrame.nearest_join(...)` for ranked nearest-feature joins.
- Added `GeoPromptFrame.assign_nearest(...)` for target-focused nearest-origin allocation.
- Added `GeoPromptFrame.summarize_assignments(...)` for per-origin assigned ids, counts, distance summaries, and target aggregations.
- Improved `nearest_neighbors(...)` for small-`k` lookups.
- Reduced join output overhead by bypassing redundant geometry normalization for internal derived rows.

## Why This Matters

- These tools make Geoprompt more useful for facility allocation, territory design, service balancing, and first-pass catchment analysis.
- Users can now move from nearest matching to operational summaries without having to rebuild the grouping logic themselves.
- The new summary workflow fits the package’s strength: compact frame-level GIS tasks without a heavier dataframe dependency.

## Validation

- `pytest` passed on the standalone repository.
- `python -m build` and `python -m twine check dist/*` are expected release checks for this version.
- The comparison suite kept all summary parity flags `true`.

## Remaining Focus

- `spatial_join(...)` is still the clearest algorithmic improvement target on smaller benchmark cases.
- Catchment competition and overlay summaries are the next strongest user-facing tools to build.