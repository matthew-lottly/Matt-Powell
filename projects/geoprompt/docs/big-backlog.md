# GeoPrompt Master Backlog

> Baseline: 400 tools, 940 passing tests, 1 skipped, version 0.1.18
>
> Mission: build a pure-Python spatial analysis package that does more than mirror GeoPandas and Shapely. GeoPrompt should provide better analysis workflows, better algorithm reuse, stronger large-data behavior, and a wider tool surface while maintaining scientific accuracy and precision.

---

## 0. Program-Level Goals

- [x] Keep algorithmic accuracy comparable to or better than major reference libraries where overlap exists.
- [x] Prefer specialized analysis algorithms over generic geometry-heavy workflows when that improves speed or clarity.
- [x] Reuse graphs, weights, neighborhoods, and surfaces across tools instead of recomputing them repeatedly.
- [x] Expand the package only where new tools either fill a real analytical gap or clearly improve an existing workflow.
- [x] Make every advanced tool explainable: assumptions, limits, dependency behavior, and output semantics.
- [x] Preserve pure-Python default behavior while using optional dependencies for acceleration or higher-fidelity algorithms where appropriate.
- [x] Keep the package operational on Windows, macOS, and Linux.
- [x] Maintain release discipline: version, changelog, tool count, test count, benchmarks, docs.

## 1. Canonical Inventory and Governance

- [x] Generate a machine-readable tool inventory file with tool number, method name, category, maturity level, return type, and test coverage.
- [x] Generate a human-readable tool matrix for docs from the same source of truth.
- [x] Add a release checklist that verifies tool count, test count, version, docs, and benchmark status.
- [x] Add a standard algorithm maturity tag system: deterministic, validated, approximation, heuristic, experimental.
- [x] Add a standard dependency behavior tag system: pure-python, optional-acceleration, optional-high-fidelity.
- [x] Add a consistent per-tool metadata block in docs: complexity, assumptions, limitations, references.
- [x] Add a canonical category map so every tool appears in exactly one primary family and optionally one secondary family.
- [x] Add a roadmap label system for backlog items: correctness, performance, tooling, docs, release, parity, differentiation.

## 2. Accuracy and Reference-Parity Reviews

### 2.1 Spatial Statistics

- [x] Review Moran-family tools against PySAL for weight transforms, normalization, and p-value behavior.
- [x] Review Geary-family tools against PySAL for denominator semantics and interpretation.
- [x] Review Getis-Ord tools against PySAL for local and global output parity.
- [x] Review join count outputs against standard formulations for directed vs undirected neighbor counting.
- [x] Review LOSH implementation against literature for scaling and variance interpretation.
- [x] Review bivariate Moran outputs against canonical formulations.
- [x] Review correlograms and variogram diagnostics against reference formulas and expected monotonic behavior.

### 2.2 Regression and Econometrics

- [x] Review OLS-related diagnostics against statsmodels conventions.
- [x] Review spatial lag and spatial error models against `spreg` semantics.
- [x] Review MGWR and GWR-family diagnostics against common references.
- [x] Review logistic GWR output semantics and numerical stability.
- [x] Review Poisson GWR output fields and diagnostics.
- [x] Review model comparison outputs for AIC, AICc, BIC, RMSE, pseudo-R^2 behavior.

### 2.3 Interpolation and Surface Modeling

- [x] Review ordinary kriging outputs against PyKrige for field naming and prediction parity.
- [x] Review universal kriging behavior against drift expectations.
- [x] Review co-kriging semantics against cross-variogram expectations.
- [x] Review empirical Bayesian kriging neighborhood fitting and surface behavior.
- [x] Review natural neighbor interpolation against true Voronoi area-stealing behavior.
- [x] Review thin-plate spline surfaces against known benchmark surfaces.
- [x] Review contour extraction logic against expected marching-squares behavior.

### 2.4 Hydrology and Terrain

- [x] Review flow direction semantics for D8 correctness.
- [x] Review accumulation behavior and downstream ordering.
- [x] Review watershed delineation behavior against GRASS/Whitebox conceptual models.
- [x] Review stream ordering and extraction semantics.
- [x] Review TWI, LS factor, and HAND formulations against standard references.
- [x] Review curvature, TRI, TPI, and related terrain metrics for expected sign and scale behavior.

### 2.5 Geometry and Topology

- [x] Review minimum bounding shapes against Shapely or standard computational geometry references.
- [x] Review Hausdorff distance against Shapely parity.
- [x] Review skeleton, subdivision, planarization, polygon repair, and shared-boundary tools for degenerate-input behavior.
- [x] Review WKT, WKB, TopoJSON, and shapefile-related semantics for format fidelity.

## 3. Full Correctness Audit Matrix

- [x] Empty frame behavior for every tool.
- [x] One-row frame behavior for every tool.
- [x] Two-row frame behavior for every distance and interpolation tool.
- [x] Duplicate coordinate behavior for every distance-based tool.
- [x] Collinear coordinate behavior for hull, triangulation, interpolation, and skeleton tools.
- [x] Null geometry behavior for all geometry-aware tools.
- [x] Multipart geometry behavior for geometry tools.
- [x] Polygon-hole behavior for area, adjacency, shared-boundary, repair, and validity tools.
- [x] Self-intersection behavior for geometry audit and repair tools.
- [x] Disconnected network behavior for routing and centrality tools.
- [x] Directed vs undirected behavior for network tools.
- [x] Very small coordinate range behavior.
- [x] Very large coordinate range behavior.
- [x] CRS-sensitive tool warnings or errors when used with geographic coordinates.
- [x] Deterministic seeding checks for randomized tools.
- [x] Serialization and roundtrip audits for dict-returning tools.

## 4. Existing Tool Improvements Before Major Expansion

### 4.1 Interpolation Improvements

- [x] Strengthen `thin_plate_spline` with more stable solves and explicit diagnostics when the system is ill-conditioned.
- [x] Add optional smoothing auto-selection for `thin_plate_spline`.
- [x] Improve `natural_neighbor_interpolation` fallback quality documentation and confidence signaling.
- [x] Improve `regression_kriging` with explicit regression diagnostics in output metadata.
- [x] Improve `indicator_kriging` with clearer exceedance semantics and threshold diagnostics.
- [x] Add better uncertainty fields for kriging-family methods.
- [x] Improve contour generation with better segment stitching.

### 4.2 Geometry and Topology Improvements

- [x] Replace coarse Voronoi cell approximation with exact Voronoi polygon construction when dependencies permit.
- [x] Improve `shared_boundaries` to detect line overlap rather than only common vertices.
- [x] Improve `polygon_validity_check` with self-intersection detection.
- [x] Improve `polygon_validity_check` with duplicate-vertex detection.
- [x] Improve `polygon_validity_check` with zero-area ring detection.
- [x] Improve `polygon_validity_check` with shell-hole orientation diagnostics.
- [x] Improve `polygon_repair` with configurable repair strategy selection.
- [x] Improve `polygon_repair` with repair reports detailing what changed.
- [x] Improve `line_merge` with better graph-based merging instead of endpoint-only concatenation.
- [x] Improve `topology_audit` to detect overlaps and gaps beyond duplicate and dangle checks.

### 4.3 Hydrology Improvements

- [x] Make `stream_extraction` more explicit about flow-routing assumptions.
- [x] Make `hand` more explicit about drainage definition and stream threshold semantics.
- [x] Improve `ls_factor` assumptions for flow length and slope thresholds.
- [x] Add clearer tie-breaking rules for equal downhill candidates.
- [x] Add optional flow-direction diagnostics output.

### 4.4 Network Improvements

- [x] Improve `min_cut` to work from explicit residual graphs rather than simplistic capacity interpretation.
- [x] Improve OD matrix behavior for larger origin and destination sets.
- [x] Improve network centrality documentation and directed-graph semantics.
- [x] Add better route failure diagnostics for disconnected networks.

## 5. Performance Infrastructure

### 5.1 Neighborhood and Distance Reuse

- [x] Add reusable neighbor caches keyed by geometry fingerprint, method, and parameters.
- [x] Add sparse-neighbor representations for tools that do not need dense pairwise matrices.
- [x] Add adjacency reuse across Moran, Geary, lag, clustering, and regionalization tools.
- [x] Add distance cache invalidation rules when geometries change.
- [x] Add optional approximate-neighbor search mode for exploratory large-data workflows.

### 5.2 Grid and Raster Performance

- [x] Add chunked grid computation for interpolation tools.
- [x] Add chunked rasterization and focal-statistics workflows.
- [x] Add row-wise or tile-wise parallel processing for grid tools.
- [x] Add progressive surface generation hooks so large outputs can stream.
- [x] Add memory-conscious representations for large grids.
- [x] Add optional output writers for streamed grid products.

### 5.3 Profiling and Benchmarking

- [x] Add a profiling harness for the slowest 20 methods.
- [x] Add separate benchmark suites for interpolation, clustering, routing, hydrology, geometry, and I/O.
- [x] Track runtime deltas across Python versions.
- [x] Track memory growth on large grids and large point sets.
- [x] Add CI gates for severe regressions.
- [x] Add benchmark snapshots to releases.

## 6. Where GeoPrompt Should Outperform GeoPandas and Shapely

### 6.1 Analysis-First Design

- [x] Build algorithms that use centroids, graphs, neighborhoods, and grids directly when exact polygon geometry is unnecessary.
- [x] Avoid repeated object-heavy geometry conversions in statistical workflows.
- [x] Reuse graph and weight structures across tool families in one analysis session.
- [x] Prefer direct matrix, graph, and raster computations over repeated overlay-heavy workflows.

### 6.2 Large-Data Workflows

- [x] Add chunked and streaming paths for interpolation and raster tools.
- [x] Add persistent adjacency and neighbor graphs for repeated spatial statistics workflows.
- [x] Add memory-aware execution modes.
- [x] Add optional approximation modes for exploration and exact modes for final outputs.

### 6.3 Developer and Analyst Ergonomics

- [x] Add `describe_tool()` or `tool_info()` to expose assumptions, parameters, output schema, and maturity.
- [x] Add typed result objects for statistics and routing outputs.
- [x] Add unified diagnostics mode across major algorithms.
- [x] Add structured progress callbacks.
- [x] Add richer exceptions with actionable remediation guidance.

## 7. New Tools: Spatial Statistics

- [x] Local Getis-Ord G with permutation significance and multiple-comparison support.
- [x] Multivariate Moran's I.
- [x] Local Geary decomposition diagnostics.
- [x] Moran eigenvector maps.
- [x] Spatial filtering helpers built from Moran eigenvectors.
- [x] Local indicators of network association.
- [x] Spatial entropy variants beyond the current implementation.
- [x] Directional variogram surface.
- [x] Distance-band significance scanning for autocorrelation diagnostics.
- [x] Robust Moran-family methods for outlier-resistant workflows.
- [x] Weighted join count variants.
- [x] Spatial inequality and segregation metrics.
- [x] Spatial diversity indices.
- [x] Local variance decomposition tools.
- [x] Region-level autocorrelation summary tools.

## 8. New Tools: Interpolation and Surface Modeling

- [x] Space-time kriging.
- [x] Ordinary cokriging with explicit cross-variogram handling.
- [x] Trend-surface analysis with polynomial order selection.
- [x] Adaptive IDW with local power selection.
- [x] Nearest-neighbor surface interpolation.
- [x] Interpolation uncertainty summaries.
- [x] Kriging confidence bands or variance summaries.
- [x] Breakline-aware interpolation mode.
- [x] Surface resampling utilities.
- [x] Contour-to-polygon conversion.
- [x] Surface masking by polygon extent.
- [x] Surface blending or model stacking helpers.
- [x] Surface comparison tools for multiple interpolators.
- [x] Drift diagnostics for trend-aware interpolation.
- [x] Interpolator recommendation helper based on data geometry and density.

## 9. New Tools: Clustering and Regionalization

- [x] DBSCAN.
- [x] HDBSCAN-style fallback when dependency is unavailable.
- [x] Hierarchical agglomerative clustering with contiguity rules.
- [x] Community detection on adjacency graphs.
- [x] REDCAP-style regionalization.
- [x] Cluster stability diagnostics across random seeds.
- [x] Constrained k-means with travel-distance or contiguity limits.
- [x] Balanced clustering variants.
- [x] Region compactness diagnostics beyond current implementation.
- [x] Cluster explanation summaries.
- [x] Soft regionalization outputs.
- [x] Cluster comparison utilities.
- [x] Automatic cluster-number diagnostics.
- [x] Regionalization feasibility diagnostics.
- [x] Contiguity-repair helpers for clustering outputs.

## 10. New Tools: Regression and Econometrics

- [x] Negative binomial GWR.
- [x] Geographically weighted PCA.
- [x] Local collinearity diagnostics for GWR-family tools.
- [x] Heteroskedasticity diagnostics for local regression.
- [x] Quantile regression by location.
- [x] Spatial two-stage least squares helpers.
- [x] SLX model support.
- [x] SAC / SARAR model support.
- [x] Panel spatial regression scaffolding.
- [x] Local influence diagnostics.
- [x] Local leverage diagnostics.
- [x] Residual spatial structure diagnostics.
- [x] Model-comparison helpers that aggregate across model families.
- [x] Regression report generator for diagnostics and summaries.
- [x] Automatic bandwidth recommendation diagnostics.

## 11. New Tools: Terrain, Hydrology, and Raster-Like Analysis

- [x] Flow length upstream and downstream.
- [x] Sink diagnostics.
- [x] Flat-area diagnostics.
- [x] D-infinity flow direction.
- [x] Roughness metrics.
- [x] Ruggedness metrics.
- [x] Aspect classification helpers.
- [x] Hillshade with multiple sun positions.
- [x] Viewshed analysis.
- [x] Intervisibility analysis.
- [x] Least-cost surface creation from terrain and friction.
- [x] Watershed summary rollups by polygon or catchment.
- [x] Stream-network summarization.
- [x] Terrain derivative bundles.
- [x] Ridge and valley extraction heuristics.
- [x] Surface roughness segmentation.

## 12. New Tools: Network Analysis and Routing

- [x] Turn restrictions support.
- [x] Route barriers and temporary closures.
- [x] Multi-source routing.
- [x] Multi-destination routing.
- [x] Service-area polygons from network reachability.
- [x] Isochrone generation.
- [x] Route sequencing with time windows.
- [x] Pickup-and-delivery routing.
- [x] Transit-style schedule-aware routing.
- [x] Route explanation outputs.
- [x] Edge criticality diagnostics.
- [x] Network resilience metrics.
- [x] Redundancy and detour metrics.
- [x] Accessibility scoring.
- [x] Flow-assignment helpers.

## 13. New Tools: Point Patterns and Event Analysis

- [x] Nearest-neighbor contingency table analysis.
- [x] Quadrat analysis.
- [x] Pairwise directionality or rose diagnostics.
- [x] Space-time K function.
- [x] Inhomogeneous pair correlation function.
- [x] Covariate-adjusted intensity estimation.
- [x] Local hotspot duration analysis across time slices.
- [x] Event burst detection on spatial windows.
- [x] Point-process simulation helpers.
- [x] Multi-type interaction diagnostics.
- [x] Local cluster persistence analysis.
- [x] Time-slice comparison helpers.
- [x] Event density trend surfaces.
- [x] Local dispersion diagnostics.
- [x] Event anisotropy diagnostics.

## 14. New Tools: Geometry and Topology

- [x] Polygon triangulation.
- [x] Constrained Delaunay triangulation.
- [x] Medial axis refinement beyond current skeleton approximation.
- [x] Line offset or parallel curve generation.
- [x] Polygon smoothing with topology preservation.
- [x] Polygon simplification with topology preservation.
- [x] Mesh-style subdivision for polygons.
- [x] Polygon mesh quality diagnostics.
- [x] Boundary generalization tools.
- [x] Gap and overlap repair helpers.
- [x] Multipart normalization tools.
- [x] Ring-orientation correction utilities.
- [x] Segment intersection diagnostics.
- [x] Topology normalization helpers.
- [x] Coverage validation helpers.

## 15. New Tools: I/O and Format Support

- [x] GeoParquet read support.
- [x] GeoParquet write support.
- [x] FlatGeobuf read support.
- [x] FlatGeobuf write support.
- [x] Feather or Arrow spatial export helpers.
- [x] KMZ read support.
- [x] KMZ write support if feasible.
- [x] Metadata-preserving roundtrip checks for all formats.
- [x] Dependency matrix docs per format.
- [x] Explicit schema-report tools for loaded datasets.
- [x] Format autodetection helpers.
- [x] Encoding diagnostics for file import errors.
- [x] Windows path and encoding hardening for all file I/O.
- [x] Export validation helpers.

## 16. New Tools: Raster and Grid Utilities

- [x] Focal statistics: mean, max, min, variance.
- [x] Raster algebra on surface outputs.
- [x] Nodata masking and propagation rules.
- [x] Grid resampling utilities.
- [x] Contour-to-polygon conversion.
- [x] Raster clipping by polygon.
- [x] Raster summary reports.
- [x] Grid neighborhood extraction helpers.
- [x] Local raster morphology helpers.
- [x] Surface differencing tools.
- [x] Surface threshold and classification tools.
- [x] Grid-cell provenance metadata helpers.

## 17. API and Developer Experience

- [x] Method-chaining support review for mutating operations.
- [x] Central config object for defaults like suffixes, distance method, and seeds.
- [x] Structured logging hooks.
- [x] Progress callbacks for long-running tools.
- [x] Plugin registration system for third-party tool packs.
- [x] Typed result models for statistics, routing, and diagnostics.
- [x] Consistent exception types with remediation hints.
- [x] Tool introspection helpers.
- [x] Unified diagnostics mode.
- [x] Provenance metadata review for outputs.
- [x] Optional `inplace` strategy review.
- [x] Stable public API review for exports and naming.

## 18. Testing Expansion

- [x] Hypothesis-based property tests.
- [x] Fuzz tests for malformed geometries.
- [x] Snapshot tests for WKT, WKB, and TopoJSON outputs.
- [x] Golden-data tests for routing outputs.
- [x] Cross-library parity tests for every overlapping spatial statistic.
- [x] Large-data stress tests.
- [x] Memory-usage tracking for grid tools.
- [x] Optional-dependency matrix tests in CI.
- [x] Mutation testing.
- [x] Performance regression tests.
- [x] Windows-specific path and encoding tests.
- [x] Seed determinism tests for randomized tools.
- [x] File-format roundtrip test matrix.
- [x] Diagnostic-output schema tests.

## 19. Benchmarking and Profiling Docs

- [x] Document benchmark datasets.
- [x] Document benchmark methodology.
- [x] Publish baseline numbers per release.
- [x] Add profiler reports for hot methods.
- [x] Add memory benchmark summaries.
- [x] Add why-this-is-faster-than-a-common-GeoPandas-workflow notes where justified.

## 20. Documentation Work

- [x] Generated API reference site.
- [x] Quickstart examples for each major tool family.
- [x] Tutorial notebooks for interpolation, clustering, routing, hydrology, geometry, and parity testing.
- [x] How-to-choose-a-tool guidance by problem type.
- [x] Algorithm notes and citations for advanced methods.
- [x] Dependency-specific docs showing what improves when SciPy, Shapely, Fiona, PySAL, or others are installed.
- [x] Gallery of reproducible examples.
- [x] Failure-mode docs for common issues.
- [x] Migration notes for each minor release.
- [x] Contributor guide for parity testing and benchmarking.

## 21. Packaging and Release Work

- [x] Improve PyPI metadata.
- [x] Add project URLs and keywords review.
- [x] Verify license placement and packaging behavior.
- [x] Add release automation checks.
- [x] Add source-distribution validation.
- [x] Add wheel validation checks.
- [x] Add optional dependency group review.
- [x] Add release notes generation template.

## 22. Strategy Items: What Not To Do

- [x] Avoid adding tools that are just thin wrappers with no algorithmic or usability gain.
- [x] Avoid introducing optional dependencies unless they clearly improve fidelity, speed, or interoperability.
- [x] Avoid generic geometry-heavy implementations where a specialized spatial-analysis algorithm is cheaper.
- [x] Avoid increasing tool count without increasing validation and documentation quality.
- [x] Avoid silently changing output field semantics between related tools.

## 23. Suggested Work Order

### Phase A - Strengthen What Already Exists

- [x] Improve Voronoi, polygon validity, polygon repair, shared boundaries, topology audit, thin-plate spline, and hydrology semantics.
- [x] Add parity and edge-case audits around those improvements.

### Phase B - Build the Infrastructure That Makes Future Work Cheaper

- [x] Add reusable neighbor caches.
- [x] Add sparse adjacency reuse.
- [x] Add chunked and parallel grid execution.
- [x] Add profiling harnesses and benchmark gates.

### Phase C - Add the Highest-Leverage New Tools

- [x] Multivariate Moran's I.
- [x] Local Geary decomposition.
- [x] Negative binomial GWR.
- [x] Geographically weighted PCA.
- [x] Space-time kriging.
- [x] Adaptive IDW.
- [x] DBSCAN and HDBSCAN-style fallback.
- [x] Service-area polygons and isochrones.
- [x] Focal statistics and raster algebra.
- [x] Polygon triangulation and constrained Delaunay.
- [x] GeoParquet and FlatGeobuf support.

### Phase D - Make GeoPrompt Distinctive

- [x] Add tool introspection and diagnostics.
- [x] Add reusable analysis pipelines for adjacency-heavy methods.
- [x] Add overlay-light alternatives to common GeoPandas analysis patterns.
- [x] Publish benchmark evidence showing where GeoPrompt wins.

## 24. Definition of Good Progress

Only count backlog work as high-quality progress if it does at least one of the following:

- [x] Adds a meaningful analytical capability.
- [x] Improves accuracy.
- [x] Improves precision.
- [x] Improves runtime.
- [x] Improves memory behavior.
- [x] Improves reproducibility.
- [x] Improves diagnostics or explainability.
- [x] Clearly differentiates GeoPrompt from standard GeoPandas or Shapely workflows.