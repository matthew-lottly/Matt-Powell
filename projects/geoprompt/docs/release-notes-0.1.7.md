# Geoprompt 0.1.7

## Highlights

- Added `GeoPromptFrame.catchment_competition(...)` for overlap-aware service-radius analysis.
- Improved rectangle-heavy predicate workflows so benchmark `clip(...)` moves materially closer to the reference path.
- Kept correctness parity checks green across bounds, geometry metrics, reprojection, clip, dissolve, nearest neighbors, and spatial joins.

## What Changed

### New Tool

- `catchment_competition(...)` summarizes which targets fall inside each origin catchment and breaks them into:
  - total covered targets
  - exclusive targets reached by only one origin
  - shared targets reached by multiple origins
  - won targets assigned to the nearest origin inside the contested set
  - unserved targets outside every catchment

### Algorithm Pass

- Added fast rectangle-oriented predicate checks in `geometry.py` for the axis-aligned polygon cases that dominate the built-in benchmark regions.
- Reduced redundant row normalization in additional frame methods so join, clip, and coverage-style outputs spend less time rebuilding already-normalized rows.

## Current Focus After 0.1.7

- `clip(...)` is now much closer to parity on the smaller benchmark corpus.
- `spatial_join(...)` remains the clearest next optimization target.
- The next planned tool family is overlay summaries, followed by corridor reach and zone fit scoring.