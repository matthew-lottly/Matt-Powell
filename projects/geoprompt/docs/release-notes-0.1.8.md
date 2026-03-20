# Geoprompt 0.1.8

## Highlights

- Added `GeoPromptFrame.overlay_summary(...)` for overlap-focused metrics without forcing users to inspect derived intersection geometries.
- Kept comparison parity checks green while expanding the summary tool surface.
- Re-measured `spatial_join(...)` during this pass and left the existing join implementation in place after a speculative alternative failed to show a stable enough advantage.

## What Changed

### New Tool

- `overlay_summary(...)` returns per-feature summary rows with:
  - intersecting ids
  - intersecting feature count
  - exploded intersection count
  - total overlap area
  - total overlap length
  - per-feature area share for polygon-like rows
  - per-feature length share for line-like rows
  - optional aggregate rollups from the matched right-side rows

### Validation Notes

- `31` tests pass in the current release state.
- Comparison parity remains green across the built-in corpora.
- The latest benchmark snapshot shows `spatial_join(...)` ahead of the reference path on the small benchmark corpus and well ahead on the stress corpus, while `clip(...)` remains close enough to keep watching in later passes.

## Next Direction

- Corridor reach is now the next tool priority.
- Zone fit scoring and multi-scale clustering remain the next higher-level analytic additions after corridor tooling.