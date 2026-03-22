# GeoPrompt Package TODO & Roadmap

See also: [docs/big-backlog.md](big-backlog.md) for a larger next-phase backlog covering tool additions, reviews, validation, CI, packaging, and release work.

## Current Status
- **148 spatial analysis tools** on GeoPromptFrame
- **498 tests** (338 core + 35 new-tool + 44 reference-parity + 38 P3-tool-batch-1 + 32 P3-tool-batch-2 + 11 SpatialWeights), all passing
- Reference parity confirmed against: Shapely, GeoPandas, SciPy, PySAL, PyKrige, statsmodels, scikit-learn
- `SpatialWeights` class for reusable spatial weight matrices
- Cross-platform CI (Linux/macOS/Windows × Python 3.11-3.13)
- Benchmark suite tracking 10 key tools at 3 dataset sizes

---

## Priority 1 — Bugs & Correctness

- [x] Moran's I numerical parity: Current global Moran's I uses a different weight normalization than PySAL (`R` row-standardized). Investigate aligning weight normalization to get value-level parity, not just sign agreement.
- [x] Local Moran's I (LISA) value parity: Currently only sign agreement with PySAL. Align z-score computation with `esda.Moran_Local` for tighter tolerance.
- [x] Geary's C global: Cross-validate against `esda.Geary` (currently only structural tests).
- [x] Kriging auto-fit variogram: Currently uses grid search. Consider gradient-based optimization for better fit on large datasets.
- [x] Natural neighbor interpolation: Current Sibson-style is 1/d² weighted, not true area-stealing. Implement true Voronoi-based area-stealing when Shapely is available.

## Priority 2 — Performance

- [x] KDTree spatial indexing: Wrap scipy.spatial.KDTree for O(n log n) neighbor queries in `_pairwise_distance_matrix`, `nearest_neighbor_distance`, `spatial_lag`, etc. Currently O(n²).
- [x] Sparse spatial weights: Replace dense pairwise distance matrices with sparse representations for large datasets.
- [ ] Parallel execution: Use `concurrent.futures` for embarrassingly parallel operations (IDW grid, KDE grid, kriging grid).
- [ ] Lazy evaluation: Defer heavy computation until results are accessed, not at method call time.
- [ ] Streaming/chunked mode: Process large datasets in chunks to reduce peak memory usage.

## Priority 3 — New Tools to Add

### Spatial Statistics
- [x] **Getis-Ord G (global)** — global G statistic for overall clustering tendency
- [x] **Lee's L statistic** — bivariate spatial association for spatial econometrics
- [x] **Spatial Markov chains** — transition probabilities between spatial states
- [x] **Space-time Moran's I** — spatiotemporal autocorrelation
- [x] **Variogram cloud** — raw semivariance point cloud before fitting
- [x] **Correlograms** — Moran's I at multiple distance lags

### Interpolation
- [x] **Universal Kriging** — kriging with drift (trend + residual kriging)
- [x] **Co-kriging** — multivariate kriging using correlated secondary variable
- [x] **Empirical Bayesian Kriging** — adaptive variogram fitting per neighborhood
- [x] **Radial Basis Function interpolation** — multiquadric, thin-plate, inverse
- [x] **Anisotropic IDW/Kriging** — directional distance weighting

### Clustering
- [x] **Spatially constrained clustering** — SKATER or REDCAP for regionalization
- [x] **Max-p regions** — maximize regions subject to constraint (min population)
- [x] **Fuzzy C-means** — soft clustering with membership degrees
- [x] **Gaussian Mixture Models (spatial)** — probabilistic clustering
- [x] **Self-Organizing Maps (SOM)** — neural-network-based spatial clustering

### Regression
- [x] **Spatial Error Model (SEM)** — error term with spatial structure
- [x] **Spatial Lag Model (SLM)** — endogenous spatial lag via 2SLS
- [x] **Multiscale GWR (MGWR)** — bandwidth varies by variable
- [x] **GWR with Poisson/logistic** — GWR for count/binary outcomes
- [x] **Spatial regime models** — different coefficients per region

### Terrain & Hydrology
- [x] **Curvature (plan/profile)** — second derivatives of surface
- [x] **Watershed delineation** — full watershed from pour points
- [x] **Stream ordering** — Strahler and Shreve ordering
- [x] **Depression filling** — fill sinks in DEM
- [x] **Topographic Wetness Index (TWI)** — ln(a/tan(β))
- [x] **Solar radiation** — hillshade-based annual insolation

### Network
- [x] **Network Voronoi** — service area partitioning on network
- [ ] **Turn restrictions** — conditional edge traversal in routing
- [x] **Time-dependent routing** — edge costs vary by time-of-day
- [x] **Capacitated Vehicle Routing (CVRP)** — multi-vehicle route optimization
- [x] **Network flow** — max flow / min cut on spatial networks

### Point Patterns
- [x] **K-cross function** — bivariate Ripley's K between two point types
- [x] **Pair correlation function g(r)** — unnormalized K derivative
- [x] **Inhomogeneous K** — K function adjusting for varying intensity
- [x] **Nearest-neighbor G function** — CDF of NN distances
- [x] **Empty space F function** — CDF of point-to-nearest-event distances

### Geometry
- [x] **Polygon skeletonization** — medial axis transform
- [x] **Minimum bounding circle / rectangle** — rotated bounding shapes
- [x] **Polygon subdivision** — split polygons into sub-areas
- [x] **Line network planarization** — split at intersections
- [x] **Snap geometries to grid** — coordinate rounding/snapping
- [x] **Hausdorff distance** — shape similarity metric

### I/O & Format
- [ ] **GeoParquet I/O** — read/write Apache Parquet with geometry
- [x] **Shapefile I/O** — read/write ESRI Shapefiles
- [x] **GeoPackage I/O** — read/write OGC GeoPackage (SQLite)
- [x] **WKT/WKB conversion** — parse/emit Well-Known Text/Binary
- [x] **KML/KMZ I/O** — Google Earth format
- [x] **TopoJSON** — topology-encoded GeoJSON

## Priority 4 — API & Developer Experience

- [ ] **Method chaining API**: Return `self` from mutating methods for `frame.buffer(100).dissolve("group")` style.
- [x] **Spatial weights as first-class object**: `SpatialWeights` class with `from_knn()`, `from_distance_band()`, `.transform()`, reusable across multiple tools.
- [ ] **Progress callbacks**: Optional callback parameter for long-running tools (kriging, OPTICS, scan statistic).
- [ ] **Logging**: Structured logging for debug-level algorithm tracing.
- [x] **Type stubs / py.typed marker**: Ship type hints for IDE autocomplete.
- [ ] **Plugin system**: Allow third-party tool registration on GeoPromptFrame.

## Priority 5 — Testing & CI

- [ ] **Property-based testing**: Use Hypothesis to fuzz tool inputs (random coords, edge-case values, NaN, empty frames).
- [x] **Benchmark suite**: Track wall-clock and memory for key tools across releases. Flag regressions.
- [ ] **Coverage target**: Reach 90%+ line coverage. Currently untested: some network edge cases, some overlay edge cases.
- [ ] **Mutation testing**: Use mutmut to verify test quality.
- [x] **Cross-platform CI**: Test on Linux, macOS, Windows in GitHub Actions.
- [ ] **Nightly parity**: Scheduled CI job running reference-parity tests against latest Shapely/PySAL/etc.

## Priority 6 — Documentation & Packaging

- [ ] **API reference**: Auto-generate from docstrings (Sphinx or MkDocs).
- [ ] **Tutorials / notebooks**: Step-by-step Jupyter notebooks for common workflows.
- [x] **Changelog**: Maintain CHANGELOG.md with semantic versioning.
- [ ] **PyPI metadata**: Classifiers, keywords, project URLs for discoverability.
- [x] **Contributing guide**: CONTRIBUTING.md with dev setup, test conventions, PR process.
- [ ] **License file**: Ensure LICENSE is present at repo root.

---

## Completed (This Session)

- [x] Upgraded 8 existing tools with scientifically grounded algorithms (IDW, KDE, Hotspot, Kriging, GWR, Ripley's K, Natural Neighbor, Spatial Outlier)
- [x] Added 15 new tools (86-100): Bivariate Moran's I, Local Geary's C, LOESS, Spatial Scan, OPTICS, Geographic Detector, TRI, TPI, Flow Direction, Flow Accumulation, Mark Correlation, Point Pattern Intensity, Location Allocation, Spatial Durbin Model, Kriging Cross-Validation
- [x] Created 44 reference-parity tests vs GeoPandas, Shapely, SciPy, PySAL, PyKrige, statsmodels, sklearn
- [x] Professional README rewrite with 148-tool reference tables
- [x] Updated tool-methodology.md with accuracy evidence and parity results
- [x] Fixed all `get_errors` type issues (0 errors remaining)
- [x] Verified all image links (1 image, not broken)
- [x] P1: Fixed Moran's I row standardization, LISA, Geary's C, kriging variogram optimization, natural neighbor interpolation
- [x] P2: KDTree acceleration for O(n log n) queries, scipy pdist/squareform for distance matrices
- [x] P3: Added 48 new tools (101-148) across spatial statistics, interpolation, clustering, regression, terrain, network, point patterns, geometry, and I/O
- [x] P4: SpatialWeights class (from_knn, from_distance_band, transform R/B/D), py.typed marker
- [x] P5: Cross-platform CI matrix (Linux/macOS/Windows × Python 3.11-3.13), benchmark suite
- [x] P6: CHANGELOG.md v0.1.16, CONTRIBUTING.md, README update
- [x] 498 tests passing, 0 failures, 1 skipped
