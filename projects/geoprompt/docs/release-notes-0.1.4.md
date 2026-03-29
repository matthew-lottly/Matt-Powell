# Geoprompt 0.1.4 Release Notes

## Highlights

- Added service-area tooling for buffered matching and coverage rollups.
- Extended the frame API without adding a pandas dependency.
- Preserved parity against the Shapely and GeoPandas reference checks already built into the comparison workflow.

## New Tools

- `GeoPromptFrame.buffer_join(...)`
  - Buffer each left-side geometry by a distance threshold and join it to matching right-side geometries.
  - Useful for service areas, catchment approximations, and quick reach analysis.
- `GeoPromptFrame.coverage_summary(...)`
  - Summarize how many target features each geometry covers.
  - Supports target id rollups plus aggregation of matched target columns.

## Why These Matter

- They fit the package’s current strength: fast, geometry-aware frame workflows without forcing callers into a heavier dataframe stack.
- They make Geoprompt more useful for accessibility, catchment, and coverage-style analysis where users often want a compact answer instead of a full overlay result.

## Validation

- Tests passed on the standalone repository.
- Existing comparison parity checks remained green.

## Remaining Focus

- `clip(...)` is still the clearest remaining performance gap against the reference stack.
- A future pass should add catchment-specific helpers on top of the new service-area tools.