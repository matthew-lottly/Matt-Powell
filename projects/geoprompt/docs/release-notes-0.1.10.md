# Release Notes — 0.1.10

## Summary

This is a patch release focused on correctness and edge-case behavior in the 0.1.9 additions.

## Fixes

### Convex Hull

`geometry_convex_hull(...)` now returns a `LineString` for fully collinear inputs instead of constructing an invalid polygon-like hull.

### Corridor Reach Distance Semantics

`GeoPromptFrame.corridor_reach(...)` now explicitly supports only Euclidean distance. The method previously exposed a `distance_method` parameter without a correct haversine line-distance implementation.

### Distance Validation

- `gravity_model(...)` now rejects negative distances.
- `accessibility_index(...)` now rejects negative distances.
- `accessibility_index(...)` now returns infinite accessibility when a positive-weight destination is at zero distance.

### Frame Utilities

- `GeoPromptFrame.filter(...)` now accepts boolean sequences such as tuples.
- `GeoPromptFrame.sort(...)` now keeps `None` values at the end in both ascending and descending order.

## Test Coverage

The regression suite increased to 56 tests, covering the new edge cases fixed in this release.
