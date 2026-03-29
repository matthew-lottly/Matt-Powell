# Geoprompt 0.1.5 Release Notes

## Highlights

- Tightened the overlay conversion path instead of adding more frame-level complexity.
- Improved `clip(...)` enough to move ahead of the reference path in the current benchmark and stress corpora.
- Preserved parity across the existing Shapely and GeoPandas comparison suite.

## What Changed

- Cached Shapely module loading inside `overlay.py` so repeated overlay operations do not keep paying import lookup overhead.
- Reworked `geometry_to_shapely(...)` to construct Point, LineString, and Polygon objects directly instead of round-tripping through a GeoJSON mapping.
- Regenerated the comparison report to confirm the new path still matches the reference stack on all current correctness checks.

## Why This Matters

- The previous release added more service-area capability. This release improves one of the remaining hot paths instead of broadening the API again.
- `clip(...)` is a foundation for masking, trimming, and many downstream overlay-style workflows, so improving it lifts a common building block rather than a niche helper.
- The optimization stays inside the overlay adapter layer, which keeps the public frame API simple and easier to maintain.

## Validation

- `pytest` passed on the standalone repository.
- The comparison report kept all summary parity flags at `true`.
- Current measured clip ratios from the built-in report:
  - `benchmark`: `1.83x`
  - `stress`: `1.05x`

## Remaining Focus

- `spatial_join(...)` is now the clearer next optimization target on the smaller benchmark corpus.
- Reprojection is still close to the reference path and may be worth another pass if CRS-heavy workflows become a priority.