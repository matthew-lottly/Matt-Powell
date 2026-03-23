# GeoPrompt Execution Roadmap

Use [docs/big-backlog.md](big-backlog.md) as the canonical long-form backlog.

This file is the short execution view for the next major phase.

## Current Baseline

- 400 public spatial analysis tools on `GeoPromptFrame`
- 940 tests passing, 1 skipped
- Version 0.1.18
- Goal: build a spatial analysis package that is more capable, more efficient, and more analysis-oriented than typical GeoPandas and Shapely workflows while preserving scientific accuracy and precision

## What To Do Next

### 1. Improve Existing High-Leverage Tools First

- [x] Improve `voronoi_polygons` from coarse grid assignment toward true Voronoi construction when optional dependencies are available.
- [x] Improve `thin_plate_spline` stability and singular-system fallback behavior.
- [x] Improve `shared_boundaries` so it extracts actual shared segments, not just shared vertices.
- [x] Improve `polygon_validity_check` with self-intersection, duplicate-vertex, zero-area, and shell-hole diagnostics.
- [x] Improve `polygon_repair` with more repair strategies and explicit repair reports.
- [x] Improve `stream_extraction`, `hand`, and `ls_factor` with clearer D8 assumptions and stronger hydrology semantics.

### 2. Expand Correctness Audits

- [x] Add empty-frame audits for every public tool.
- [x] Add single-feature audits for every public tool.
- [x] Add duplicate-coordinate and collinear-point audits for distance- and interpolation-based tools.
- [x] Add disconnected-network audits for routing, centrality, and flow tools.
- [x] Add multipart and polygon-hole audits for geometry tools.
- [x] Add CRS misuse diagnostics for tools that require projected coordinates.

### 3. Build Performance Infrastructure

- [x] Add reusable neighbor caches (`_cached_distance_matrix`, `_cached_knn`).
- [x] Add sparse-neighbor execution paths beyond current dense matrix use.
- [x] Add chunked grid processing.
- [x] Add parallel execution for grid and simulation tools.
- [x] Add profiling harnesses and benchmark gates.
- [x] Add memory and runtime tracking for large interpolation, clustering, routing, and raster workloads.

### 4. Add The Next Highest-Value Tools

- [x] Multivariate Moran's I
- [x] Local Geary decomposition diagnostics
- [x] Negative binomial GWR
- [x] Geographically weighted PCA
- [x] Space-time kriging
- [x] Adaptive IDW
- [x] DBSCAN
- [x] HDBSCAN-style fallback
- [x] Service-area polygons
- [x] Isochrones
- [x] ~~Focal statistics~~ (already existed as Tool 80)
- [x] Raster algebra
- [x] Polygon triangulation
- [x] Constrained Delaunay triangulation
- [x] GeoParquet read/write
- [x] FlatGeobuf read/write

### 5. Make GeoPrompt More Distinctive

- [x] Reuse adjacency and weights across tool families instead of recomputing neighborhoods.
- [x] Add analysis-first algorithms that avoid generic geometry overhead when centroids, graphs, or grids are enough.
- [x] Add overlay-light alternatives to common expensive GeoPandas workflows.
- [x] Add chunked and streaming paths for large spatial analysis jobs.
- [x] Add tool introspection and diagnostics so users can understand method maturity, assumptions, and output semantics quickly.

## Working Rule

Only count work as good progress if it does at least one of these:

- adds a meaningful tool
- improves correctness
- improves precision
- improves runtime or memory use
- improves reproducibility or testability
- clearly differentiates GeoPrompt from standard GeoPandas/Shapely workflows