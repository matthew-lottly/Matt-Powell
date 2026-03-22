# GeoPrompt Big Backlog

> Baseline: 148 tools, 498 passing tests, 1 skipped test, version 0.1.16
>
> Purpose: a large next-phase backlog that goes beyond the current TODO and groups work into delivery-sized buckets: reviews, tool additions, architecture, testing, docs, packaging, and release operations.

---

## 1. Immediate Follow-Up Work

- [ ] Review the 18 newest tools for API consistency: naming, suffixes, return shapes, parameter order.
- [ ] Audit all grid-producing tools to ensure cell-center placement is consistent.
- [ ] Audit all interpolation tools for empty-frame, 1-point, and 2-point behavior.
- [ ] Audit all network tools for directed vs undirected semantics.
- [ ] Audit all hydrology tools for slope sign conventions and downhill tie-breaking.
- [ ] Standardize result field naming across prediction tools: `predicted_*` vs `value_*`.
- [ ] Standardize error behavior for missing columns across all tools.
- [ ] Standardize how tools behave when optional dependencies are missing.
- [ ] Add a repo-wide tool inventory table with tool number, method name, category, and test coverage.
- [ ] Review the public API exports in `__init__.py` for completeness and stability.

## 2. Reviews Needed

### Algorithm Reviews

- [ ] Review kriging-family implementations against PyKrige for parameter semantics and output parity.
- [ ] Review Moran/Geary/Getis implementations against PySAL for normalization and p-value behavior.
- [ ] Review GWR, MGWR, and spatial regression methods against `spreg` and common references.
- [ ] Review hydrology tools against WhiteboxTools or GRASS conceptual behavior.
- [ ] Review clustering tools against scikit-learn conventions for reproducibility and labels.
- [ ] Review point-pattern methods against `spatstat` terminology and formula definitions.
- [ ] Review routing tools for shortest-path correctness under disconnected graphs.
- [ ] Review geometry tools for behavior on degenerate inputs and self-intersections.

### API Reviews

- [ ] Review whether mutating tools should eventually support an `inplace` option.
- [ ] Review whether analysis tools should return typed result objects instead of frames or raw dicts.
- [ ] Review whether all tools should accept an optional `weights` object when relevant.
- [ ] Review whether suffix parameters should be optional or centrally configurable.
- [ ] Review whether geometry-only transformations should preserve row order and IDs explicitly.
- [ ] Review whether every tool should carry provenance metadata in output fields.

### Documentation Reviews

- [ ] Review README examples for outdated tool counts and stale method references.
- [ ] Review docstrings for the newest 48 tools and fill missing examples.
- [ ] Review benchmark docs so performance claims stay tied to measured outputs.
- [ ] Review changelog entries for consistency in tense, scope, and version structure.
- [ ] Review CONTRIBUTING guidance for parity with actual test commands and local setup.

## 3. Tool Additions: Spatial Statistics

- [ ] Add local Getis-Ord G output with permutation-based significance.
- [ ] Add join count statistics for binary spatial autocorrelation.
- [ ] Add LOSH for local spatial heteroskedasticity.
- [ ] Add bivariate local Moran's I.
- [ ] Add multivariate Moran's I.
- [ ] Add local Geary decomposition diagnostics.
- [ ] Add Mantel test for spatial similarity matrices.
- [ ] Add Moran eigenvector maps / spatial filtering helpers.
- [ ] Add variogram surface / directional variogram diagnostics.
- [ ] Add directional correlograms.
- [ ] Add spatial entropy measures.
- [ ] Add local indicators of network association for network-constrained data.

## 4. Tool Additions: Interpolation and Surface Modeling

- [ ] Add space-time kriging.
- [ ] Add regression kriging.
- [ ] Add indicator kriging.
- [ ] Add ordinary cokriging with explicit cross-variogram handling.
- [ ] Add thin-plate spline interpolation with smoothing control.
- [ ] Add nearest-neighbor surface interpolation.
- [ ] Add trend-surface analysis with polynomial order selection.
- [ ] Add adaptive IDW with local power selection.
- [ ] Add natural neighbor interpolation using real Voronoi area stealing when Shapely is available.
- [ ] Add interpolation uncertainty summaries and confidence bands.
- [ ] Add contour generation from interpolated surfaces.
- [ ] Add breakline-aware interpolation mode.

## 5. Tool Additions: Clustering and Regionalization

- [ ] Add DBSCAN.
- [ ] Add HDBSCAN-style clustering fallback when dependency is unavailable.
- [ ] Add constrained k-means with maximum travel distance.
- [ ] Add hierarchical agglomerative clustering with spatial contiguity rules.
- [ ] Add spectral clustering for spatial graphs.
- [ ] Add community detection on adjacency graphs.
- [ ] Add SKATER-style spanning-tree regionalization.
- [ ] Add REDCAP-style regionalization.
- [ ] Add region compactness scoring.
- [ ] Add cluster stability diagnostics across random seeds.
- [ ] Add cluster summary report helper with centroids, hulls, and within-cluster variance.

## 6. Tool Additions: Regression and Spatial Econometrics

- [ ] Add logistic GWR.
- [ ] Add negative binomial GWR.
- [ ] Add geographically weighted summary statistics.
- [ ] Add geographically weighted PCA.
- [ ] Add quantile regression by location.
- [ ] Add spatial two-stage least squares helpers.
- [ ] Add SLX model support.
- [ ] Add SAC / SARAR model support.
- [ ] Add panel spatial regression scaffolding.
- [ ] Add heteroskedasticity diagnostics for local regression.
- [ ] Add local collinearity diagnostics for GWR-family tools.
- [ ] Add model comparison helpers: AIC, AICc, BIC, pseudo-R².

## 7. Tool Additions: Terrain, Hydrology, and Raster-Like Analysis

- [ ] Add stream extraction from flow accumulation thresholds.
- [ ] Add flow length upstream and downstream.
- [ ] Add sink and flat-area diagnostics.
- [ ] Add D-infinity flow direction option.
- [ ] Add HAND: height above nearest drainage.
- [ ] Add LS factor for erosion modeling.
- [ ] Add roughness and ruggedness family metrics.
- [ ] Add aspect classification helpers.
- [ ] Add hillshade variants with multiple sun positions.
- [ ] Add viewshed / intervisibility analysis.
- [ ] Add least-cost surface creation from terrain and friction.
- [ ] Add watershed summary rollups by polygon or catchment ID.

## 8. Tool Additions: Network Analysis and Routing

- [ ] Add turn restrictions support.
- [ ] Add route barriers and temporary closures.
- [ ] Add k-shortest paths.
- [ ] Add multi-source / multi-destination routing.
- [ ] Add service-area polygons from network reachability.
- [ ] Add origin-destination cost matrix.
- [ ] Add network centrality metrics: betweenness, closeness, degree.
- [ ] Add isochrone generation.
- [ ] Add route sequencing with time windows.
- [ ] Add pickup-and-delivery routing.
- [ ] Add min-cut output paired with max-flow.
- [ ] Add transit-style schedule-aware routing.

## 9. Tool Additions: Point Patterns and Event Analysis

- [ ] Add mark variogram.
- [ ] Add nearest-neighbor contingency table analysis.
- [ ] Add quadrat analysis.
- [ ] Add pairwise directionality / rose diagnostics.
- [ ] Add spatiotemporal Knox test.
- [ ] Add space-time K function.
- [ ] Add inhomogeneous pair correlation function.
- [ ] Add covariate-adjusted intensity estimation.
- [ ] Add local hotspot duration analysis across time slices.
- [ ] Add event burst detection on spatial windows.

## 10. Tool Additions: Geometry and Topology

- [ ] Add polygon validity diagnostics with repair suggestions.
- [ ] Add polygon repair tool with configurable strategies.
- [ ] Add line merging and dissolve by connectivity.
- [ ] Add polygon triangulation.
- [ ] Add constrained Delaunay triangulation.
- [ ] Add Voronoi polygon generation.
- [ ] Add medial axis refinement beyond current skeleton approximation.
- [ ] Add line offset / parallel curve generation.
- [ ] Add polygon smoothing and simplification with topology preservation.
- [ ] Add mesh-style subdivision for polygons.
- [ ] Add shared-boundary extraction between adjacent polygons.
- [ ] Add topology audit report: dangles, overlaps, gaps, self-intersections.

## 11. Tool Additions: I/O and Format Support

- [ ] Add GeoParquet read support.
- [ ] Add GeoParquet write support.
- [ ] Add WKB read support.
- [ ] Add WKB write support.
- [ ] Add KMZ read support.
- [ ] Add GeoJSON sequence / NDJSON support.
- [ ] Add CSV with WKT autodetection helpers.
- [ ] Add Feather / Arrow spatial export helpers.
- [ ] Add FlatGeobuf read support.
- [ ] Add FlatGeobuf write support.
- [ ] Add metadata-preserving roundtrip tests for all supported formats.
- [ ] Add explicit dependency matrix doc for each I/O format.

## 12. Tool Additions: Raster and Grid Utilities

- [ ] Add rasterization of point, line, and polygon features.
- [ ] Add zonal statistics over generated grids.
- [ ] Add resampling utilities for interpolation outputs.
- [ ] Add focal statistics: mean, max, min, variance.
- [ ] Add connected-component labeling on grid outputs.
- [ ] Add contour-to-polygon conversion.
- [ ] Add raster algebra on surface outputs.
- [ ] Add nodata masking and propagation rules.

## 13. Validation and Correctness Audits

- [ ] Add a full empty-frame audit for every public tool.
- [ ] Add a single-feature audit for every public tool.
- [ ] Add duplicate-coordinate audit for every distance-based tool.
- [ ] Add collinear-point audit for interpolation and hull tools.
- [ ] Add disconnected-network audit for all routing and flow tools.
- [ ] Add polygon-hole audit for geometry and area tools.
- [ ] Add CRS audit for tools that assume planar coordinates.
- [ ] Add numeric stability audit for very small and very large coordinate ranges.
- [ ] Add deterministic-seed audit for randomized tools.
- [ ] Add serialization audit for all results returned as dicts.

## 14. Testing Expansion

- [ ] Add Hypothesis-based property tests.
- [ ] Add fuzz tests for malformed geometries.
- [ ] Add benchmark thresholds that fail on severe regressions.
- [ ] Add snapshot tests for TopoJSON and WKT/WKB outputs.
- [ ] Add golden-data tests for routing outputs.
- [ ] Add cross-library parity tests for every overlapping spatial statistic.
- [ ] Add stress tests for 10k-point interpolation and clustering runs.
- [ ] Add memory-usage tracking for grid-based tools.
- [ ] Add Windows-specific path and encoding tests for file I/O.
- [ ] Add optional-dependency matrix tests in CI.

## 15. Performance Work

- [ ] Replace more dense distance matrices with sparse neighbor structures.
- [ ] Add reusable neighbor search caches keyed by geometry fingerprint.
- [ ] Add chunked execution for large grid interpolation.
- [ ] Add parallel execution for independent grid rows.
- [ ] Add streaming results for long-running computations.
- [ ] Add profiling harness for top 20 slowest methods.
- [ ] Add benchmark comparisons across Python 3.11, 3.12, and 3.13.
- [ ] Add fast-path implementations for point-only inputs.
- [ ] Add selective NumPy vectorization for hot loops.
- [ ] Review whether Shapely-backed optional acceleration is worth introducing in selected geometry tools.

## 16. API and Developer Experience

- [ ] Add method-chaining support for mutating operations.
- [ ] Add a central config object for defaults like suffixes, distance method, and random seed.
- [ ] Add progress callbacks for long-running tools.
- [ ] Add structured logging hooks.
- [ ] Add plugin registration for third-party tools.
- [ ] Add typed result models for statistics and routing outputs.
- [ ] Add richer exceptions with remediation hints.
- [ ] Add deprecation policy and compatibility notes.
- [ ] Add `tool_info()` or `describe_tool()` introspection helper.
- [ ] Add a unified diagnostics mode for all major algorithms.

## 17. Documentation Work

- [ ] Build a generated API reference site.
- [ ] Add quickstart examples for each major tool family.
- [ ] Add tutorial notebooks for interpolation, clustering, routing, hydrology, and parity testing.
- [ ] Add “how to choose a tool” guidance by problem type.
- [ ] Add algorithm notes with references for every advanced method.
- [ ] Add dependency-specific docs: what gets better when SciPy, Shapely, or Fiona are installed.
- [ ] Add a gallery of reproducible examples.
- [ ] Add failure-mode docs for common issues: CRS misuse, disconnected networks, null geometry.
- [ ] Add migration notes for each minor release.
- [ ] Add a testing cookbook for contributors writing new tools.

## 18. Packaging and Release Work

- [ ] Review PyPI metadata, classifiers, and keywords.
- [ ] Add release checklist doc.
- [ ] Add wheel/sdist verification step.
- [ ] Add version bump automation.
- [ ] Add automated release notes generation from changelog sections.
- [ ] Add signed artifact verification if desired.
- [ ] Review minimum supported Python version policy.
- [ ] Review optional extras layout for `io`, `stats`, `viz`, and `dev`.
- [ ] Add dependency pinning policy for CI vs library consumers.
- [ ] Add release candidate workflow for larger algorithm changes.

## 19. CI and Maintenance

- [ ] Add nightly parity workflow against latest upstream dependencies.
- [ ] Add scheduled benchmark workflow.
- [ ] Add optional-dependency matrix workflow.
- [ ] Add coverage reporting and threshold enforcement.
- [ ] Add linting and formatting checks if the project wants them.
- [ ] Add docs build validation in CI.
- [ ] Add changelog format validation.
- [ ] Add stale issue / stale PR automation if the repo wants it.
- [ ] Add reproducible benchmark environment notes.
- [ ] Add support matrix documentation for platforms and optional dependencies.

## 20. Product-Level Reviews and Direction Questions

- [ ] Decide whether GeoPrompt should remain dependency-light or invest in stronger optional integrations.
- [ ] Decide whether advanced econometrics should stay inside the core package or move behind extras.
- [ ] Decide whether raster-heavy workflows belong in GeoPrompt or in a companion package.
- [ ] Decide whether network analysis should grow toward logistics optimization or remain lightweight.
- [ ] Decide whether typed result objects are worth the API churn.
- [ ] Decide whether a stable tool numbering scheme should remain public-facing.
- [ ] Decide whether a long-term plugin ecosystem is a real goal or just an internal extension point.
- [ ] Decide what parity level is required before declaring certain tools production-grade.

## 21. Suggested Execution Order

### High Leverage First

1. Full API consistency audit for tools 101-148.
2. Empty-frame and edge-case audit for all public tools.
3. GeoParquet support.
4. Turn restrictions and OD matrix.
5. Real natural neighbor interpolation.
6. Logistic GWR and richer model diagnostics.
7. Topology audit + repair tools.
8. Property-based testing and coverage enforcement.

### Strong Release Candidate Bundle

1. GeoParquet I/O.
2. Turn restrictions.
3. DBSCAN / HDBSCAN-style clustering.
4. Service-area polygons and OD matrix.
5. Topology audit report.
6. Generated API reference.
7. Nightly parity CI.

### Stretch Bundle

1. Space-time kriging.
2. Transit-aware routing.
3. Logistic and negative binomial GWR.
4. Viewshed and visibility graph analysis.
5. Plugin registration system.

---

## 22. Definition of Done for Future Tools

- [ ] Public method added to `GeoPromptFrame` or exported helper object.
- [ ] Clear docstring with algorithm summary, parameters, outputs, and caveats.
- [ ] At least one happy-path test.
- [ ] At least one edge-case test.
- [ ] If applicable, one parity or reference comparison test.
- [ ] Consistent suffix naming and output field names.
- [ ] Changelog entry included.
- [ ] Tool inventory docs updated.
