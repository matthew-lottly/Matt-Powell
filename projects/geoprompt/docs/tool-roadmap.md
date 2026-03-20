# Tool Roadmap

## Current Direction

Geoprompt is strongest when a tool does one of these well:

- turns a repeated GIS workflow into a compact frame method
- stays lightweight without forcing pandas-style table machinery
- composes with the current nearest, predicate, buffer, and coverage primitives
- remains easy to validate against Shapely and GeoPandas when reference behavior exists

## Near-Term Tools

### 1. Assignment Summaries

- Implemented through `summarize_assignments(...)`
- Current scope covers per-origin assigned ids, counts, distance summaries, and target aggregation rollups
- Next extension should add contested and unassigned-target summaries

### 2. Catchment Competition

- Implemented through `catchment_competition(...)`
- Current scope covers exclusive, shared, won, and unserved target summaries inside a service radius
- Next extension should add geometry-driven competition summaries on top of buffered service areas and contested-demand rollups

### 3. Corridor Reach

- Build on current line support plus `within_distance(...)`
- Add route-like screening around line features without requiring full network analysis
- Useful for frontage, corridor exposure, and near-route opportunity scanning

## Mid-Term Tools

### 4. Overlay Summaries

- Implemented through `overlay_summary(...)`
- Current scope covers intersecting ids, intersection counts, overlap area, overlap length, and per-feature area or length shares
- Next extension should add right-side normalization controls and grouped overlay summaries by class or band

### 5. Zone Fit Scoring

- Combine existing equations with nearest and coverage outputs
- Score how well a site fits a zone by demand, overlap, access distance, and corridor alignment

### 6. Multi-Scale Clustering

- Start with simple centroid-distance clustering for points and mixed geometries
- Keep the first version deterministic and parameter-light

## Design Rules For New Tools

- Prefer a frame method when the output should stay row-oriented and composable.
- Prefer summaries when users need metrics, not derived geometry.
- Add `max_distance`, `k`, or aggregation controls early if they change workflow value materially.
- Keep geometry normalization and CRS handling inside existing frame and geometry layers.
- Add comparison coverage when a clear Shapely or GeoPandas reference exists.

## Recommended Next Implementation Order

1. Corridor reach
2. Zone fit scoring
3. Multi-scale clustering