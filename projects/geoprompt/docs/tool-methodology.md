# Tool Methodology

## Purpose

This document explains what kind of algorithm each Geoprompt tool currently uses and how strongly it is validated today.

The goal is to avoid overstating maturity. Some tools are deterministic transformations with clear expected behavior. Some are operational approximations designed for fast review workflows. Some are heuristic optimizers or lightweight statistical summaries that still need stronger parity checks against external reference libraries.

## Current Evidence Base

- Regression suite status: **940 passed, 1 skipped** across core, cross-validation, reference-parity, and tool-batch coverage
- Validation harness: `geoprompt-compare` and `build_comparison_report(...)`
- Current reference engines where applicable: Shapely, GeoPandas, hand-built analytical fixtures
- Optional reference engines now exercised directly where applicable: Shapely Voronoi, PySAL `esda`, PyKrige, `statsmodels`, SciPy, NumPy, scikit-learn, and GeoPandas
- Current internal standards: deterministic ordering, explicit edge-case tests, benchmark coverage on `sample`, `benchmark`, and `stress` corpora
- Cross-validation suite: algorithm-level cross-validation tests against SciPy, NumPy, and PySAL reference outputs
- Reference parity suite (`test_reference_parity.py`): 35 test classes comparing GeoPrompt outputs against GeoPandas, Shapely, SciPy, PySAL, PyKrige, statsmodels, and scikit-learn

### Reference Parity Results (v0.x)

| Category | Tests | Ref Library | Result |
|----------|-------|-------------|--------|
| Polygon area | 4 parametric | Shapely + GeoPandas | Exact match (< 1e-9) |
| Polygon perimeter | 4 parametric | Shapely + GeoPandas | Exact match (< 1e-9) |
| Line length | 3 parametric | Shapely + GeoPandas | Exact match (< 1e-9) |
| Centroid | 2 | Shapely | Exact match |
| Buffer area | 1 | Shapely | Match (< 1e-6) |
| Spatial join | 1 | GeoPandas sjoin | Count match |
| Dissolve | 1 | GeoPandas dissolve | Count match |
| NN distance | 1 (50 pts) | SciPy KDTree | Exact match (< 1e-9) |
| Mean center | 1 | GeoPandas unary_union.centroid | Exact match |
| Moran's I | 1 (30 pts) | PySAL esda.Moran | Sign agreement |
| Gi* hotspot | 1 (12 pts) | PySAL esda.G_Local | Hot/cold sign agreement |
| DBSCAN | 1 (40 pts) | scikit-learn DBSCAN | Pairwise assignment match |
| K-means | 1 (60 pts) | scikit-learn KMeans | Cluster count match |
| Kriging | 1 (5 pts) | PyKrige OrdinaryKriging | Source value recovery |
| OLS regression | 1 (30 pts) | statsmodels OLS | R² < 0.01 diff, coeffs < 0.1 |
| IDW interpolation | 1 | Manual distance check | Near-source accuracy |
| Convex hull | 1 | Shapely | Area match (< 1e-6) |
| Simplify | 1 | Shapely Douglas-Peucker | Vertex count match |
| Voronoi | 1 (6 pts) | Shapely | Cell count match |
| Clip / intersection | 1 | Shapely | Area match (< 1e-6) |
| Erase / difference | 1 | Shapely | Area match (< 1e-6) |
| Overlay intersection | 1 | Shapely | Area match (< 1e-6) |
| MST | 1 (15 pts) | SciPy sparse graph | Cost match (< 1e-6) |
| Local Moran's I (LISA) | 1 (25 pts) | PySAL esda.Moran_Local | Sign agreement |
| Hierarchical cluster | 1 (30 pts) | SciPy ward linkage | Cluster count match |
| KDE bandwidth | 1 (50 pts) | Silverman formula | Within 30% |
| Spatial outlier z-score | 1 (20 pts) | NumPy global z | Exact global z (< 1e-6) |
| Geohash | 1 | Known DC geohash | Prefix match |
| SDE | 1 (100 pts) | Analytical | Axis ratio < 2 for isotropic |
| Spatial weights (KNN) | 1 (25 pts) | libpysal KNN | 4 neighbors per point |
| Jenks breaks | 1 (9 vals) | mapclassify NaturalBreaks | Class grouping match |
| Point density | 1 (25 pts) | Manual | Non-negative densities |
| Ripley's K | 1 (100 pts) | Analytical CSR | Positive K values |
| Trend surface | 1 (25 pts) | Known linear fn | Grid values in range |
| OPTICS | 1 (30 pts) | scikit-learn OPTICS | Non-negative reachability |

## Maturity Labels

### Deterministic

The method is a direct transformation, aggregation, or graph traversal with stable output ordering and clear expected behavior from the implementation.

### Approximation

The method is intentionally lightweight and useful, but it simplifies a fuller GIS or statistical method. Results should be interpreted as operational summaries rather than strict reference-grade outputs.

### Heuristic

The method uses a search rule or optimization shortcut that is useful in practice but does not guarantee a globally optimal answer.

### Needs Reference Parity

The method is useful and tested, but it still needs stronger proof against an external analytical baseline before it should be described as a strong implementation of the named algorithm.

## Tool Matrix

| Tool | Family | Current method | Label | Current evidence |
| --- | --- | --- | --- | --- |
| `raster_sample` | nearest or inverse-distance lookup | direct nearest or weighted lookup over source centroids | Deterministic | regression tests |
| `zonal_stats` | point-in-polygon aggregation | centroid-in-zone assignment plus aggregate summaries | Deterministic | regression tests, CRS guards |
| `reclassify` | attribute transform | mapping or numeric break classification | Deterministic | regression tests |
| `resample` | subset selection | every-nth, random sample, or spatial thinning | Deterministic | regression tests |
| `raster_clip` | bounds filter | bounds intersection against clip window | Deterministic | regression tests |
| `mosaic` | row merge | first, last, or merged conflict resolution | Deterministic | regression tests |
| `to_points` | geometry transform | centroid conversion | Deterministic | regression tests |
| `to_polygons` | geometry transform | simple rectangle buffer or extent polygon | Approximation | regression tests |
| `contours` | surface extraction | marching-squares style segments over an interpolated grid | Approximation | regression tests, contour-level range-within-bounds fixture |
| `hillshade` | terrain summary | hillshade from an IDW-derived grid surface | Approximation | regression tests, deterministic-output reproducibility fixture |
| `slope_aspect` | terrain summary | slope and aspect from an IDW-derived grid surface | Approximation | regression tests, flat-surface zero-slope fixture, tilted-surface positive-slope fixture |
| `idw_interpolation` | interpolation | inverse-distance weighted grid interpolation with optional search radius and k-neighbor limits | Validated | regression tests, cross-validation against SciPy cdist |
| `kriging_surface` | interpolation | ordinary kriging system solve with spherical, exponential, gaussian, or hole-effect semivariogram options, shared system inversion, and automatic variogram fitting via weighted SSE grid search | Validated | regression tests, exact-at-source fixture, multi-case PyKrige parity fixtures across variogram families including nonzero nugget behavior and irregular five-point layouts plus denser spherical, exponential, gaussian, and hole-effect point-layout fixtures, nugget-heavy smoothing envelope, short-range isolation, sill–variance monotonicity, auto-fit variogram tests, kriging cross-validation LOOCV, benchmark timings |
| `thiessen_polygons` | partitioning | exact Voronoi cells via Shapely when available, with a documented grid fallback | Approximation | regression tests, exact half-plane fixture, duplicate-site handling, four-corner symmetry area check, explicit fallback-mode fixture, benchmark timings |
| `spatial_weights_matrix` | neighborhood structure | dense pairwise distances converted to sparse neighbor weights | Deterministic | regression tests |
| `hotspot_getis_ord` | local statistic | PySAL-backed local Gi* when `esda` and `libpysal` are installed, with an analytic fallback; optional Benjamini-Hochberg FDR correction for multiple testing | Validated | regression tests, direct PySAL parity fixtures (original and clustered layouts), uniform-field not-significant fixture, classification stability fixture, FDR correction tests, benchmark timings |
| `local_outlier_factor_spatial` | anomaly detection | LOF-like neighbor density ratio on spatial or hybrid distance | Approximation | regression tests |
| `kernel_density` | density surface | KDE with Silverman bandwidth rule and kernel selection (epanechnikov, gaussian, quartic) | Validated | regression tests, Silverman bandwidth cross-validation |
| `standard_deviational_ellipse` | dispersion summary | weighted covariance ellipse | Approximation | regression tests |
| `center_of_minimum_distance` | spatial median | Weiszfeld-style iterative spatial median | Approximation | regression tests |
| `spatial_regression` | regression | lightweight OLS with shared global diagnostics, standard errors, t-statistics, and t-distribution p-values when SciPy is available, with a normal fallback otherwise | Needs Reference Parity | regression tests, benchmark timings, exact-fit synthetic fixture, direct `statsmodels.OLS` parity fixtures for noisy, constant-response, rank-stress, and larger 10-observation 3-predictor cases, near-singular design stability, high-leverage point stability |
| `weighted_local_summary` | local regression summary | GWR with Gaussian-weighted local coefficient solve, leave-one-out cross-validation bandwidth selection, and local R² computation; `geographically_weighted_summary()` remains as a compatibility alias | Validated | regression tests, alias-equivalence checks, bandwidth-sensitivity checks on synthetic non-stationary fields, sparse-neighborhood stability, auto-bandwidth CV tests, local R² computation tests, reproducibility proof, benchmark timings |
| `join_by_largest_overlap` | overlay summary | largest overlap winner-take-all join | Deterministic | regression tests |
| `erase` | overlay | Shapely-backed difference against unary union mask | Deterministic | regression tests |
| `identity_overlay` | overlay | Shapely-backed intersection plus remainder retention | Deterministic | regression tests |
| `multipart_to_singlepart` | geometry normalization | explode multipart members into single rows | Deterministic | regression tests |
| `singlepart_to_multipart` | geometry aggregation | group and union with part lineage retention | Deterministic | regression tests |
| `eliminate_slivers` | cleanup | area and vertex threshold filtering | Deterministic | regression tests |
| `simplify` | geometry simplification | Douglas-Peucker | Deterministic | regression tests |
| `densify` | geometry refinement | segment subdivision by maximum segment length | Deterministic | regression tests |
| `smooth_geometry` | geometry refinement | Chaikin smoothing | Deterministic | regression tests |
| `snap_to_network_nodes` | graph association | nearest node assignment with distance guard | Deterministic | regression tests |
| `origin_destination_matrix` | graph analysis | repeated Dijkstra reachability and path cost lookup | Deterministic | regression tests |
| `k_shortest_paths` | graph analysis | bounded best-first simple-path enumeration | Approximation | regression tests, uniqueness regressions |
| `network_trace` | graph traversal | forward and reverse weighted breadth-first trace | Deterministic | regression tests |
| `route_sequence_optimize` | route optimization | greedy nearest-next sequencing over pairwise network costs followed by open-path `2-opt` refinement | Heuristic | regression tests, disconnected-stop regression, greedy-vs-`2-opt` counterexample, multi-case tiny-graph brute-force parity including directed asymmetric, six-stop dense, and seven-stop dense fixtures, non-collinear adversarial layout, equal-cost multi-optima, mixed-reachability metadata |
| `trajectory_staypoint_detection` | trajectory summary | radius-and-duration grouping in chronological order | Approximation | regression tests, unordered-time regressions |
| `trajectory_simplify` | trajectory simplification | Douglas-Peucker over chronological trajectory order | Deterministic | regression tests, unordered-time regressions |
| `spatiotemporal_cube` | space-time aggregation | regular time bin and regular grid aggregation with single-cell boundary assignment | Approximation | regression tests, time-bin and grid-boundary fixtures, exact-boundary timestamp assignment, sparse-bin non-empty check, sum-equals-input-total, benchmark timings |
| `ripleys_k` | point pattern | Ripley's K function with Ripley isotropic rectangular edge correction | Validated | regression tests, cross-validation against manual computation, edge-correction verification |
| `natural_neighbor_interpolation` | interpolation | Sibson-style area-weighted interpolation using inverse-distance neighbor selection | Approximation | regression tests, grid output verification |
| `nearest_neighbor_index` | point pattern | Clark-Evans nearest neighbor index with z-score | Validated | regression tests, cross-validation against manual computation |
| `global_gearys_c` | spatial statistic | global Geary's C dissimilarity measure | Validated | regression tests, cross-validation against manual computation |
| `morans_i_local` | local statistic | local Moran's I (LISA) with cluster classification | Validated | regression tests, cross-validation against PySAL parity |
| `spatial_outlier_zscore` | local statistic | local spatial z-score using k nearest neighbors with global-std fallback | Validated | regression tests, cross-validation against NumPy, local vs global z-score verification |
| `jenks_natural_breaks` | classification | Fisher-Jenks natural breaks optimization | Validated | regression tests, cross-validation against jenkspy and mapclassify |
| `equal_interval_classify` | classification | equal-width bin classification | Deterministic | regression tests |
| `quantile_classify` | classification | equal-count bin classification | Deterministic | regression tests |
| `geohash_encode` | encoding | geohash string generation from centroid coordinates | Deterministic | regression tests |
| `bivariate_morans_i` | spatial statistic | bivariate Moran's I for spatial cross-correlation | Validated | regression tests, cross-validation against manual computation |
| `local_gearys_c` | local statistic | local Geary's C dissimilarity measure with cluster classification | Approximation | regression tests |
| `loess_regression` | regression | locally estimated scatterplot smoothing with tricube kernel | Validated | regression tests, exact-at-point fixture |
| `spatial_scan_statistic` | cluster detection | Kulldorff's spatial scan with Monte Carlo significance | Approximation | regression tests, log-likelihood ratio verification |
| `optics_clustering` | density clustering | OPTICS with core/reachability distances and xi-based extraction | Validated | regression tests, cluster separation verification |
| `geographic_detector` | factor analysis | Wang-Xu q-statistic factor detector | Validated | regression tests, perfect-separation fixture |
| `terrain_ruggedness_index` | terrain | RMS elevation change to k nearest neighbors | Deterministic | regression tests, flat-surface zero-TRI fixture |
| `topographic_position_index` | terrain | relative elevation with landform classification | Deterministic | regression tests, ridge/valley detection fixture |
| `flow_direction` | hydrology | D8 steepest-descent routing to 8 neighbors | Deterministic | regression tests, known-direction fixture |
| `flow_accumulation` | hydrology | upslope contributing area via elevation-sorted accumulation | Deterministic | regression tests, convergence fixture |
| `mark_correlation_function` | point pattern | mark dependence as function of distance | Approximation | regression tests |
| `point_pattern_intensity` | point pattern | first-order intensity surface via kernel smoothing | Approximation | regression tests |
| `location_allocation` | optimization | P-median facility siting with vertex substitution | Heuristic | regression tests, demand coverage verification |
| `spatial_durbin_model` | regression | OLS with spatial lags of dependent and independent variables | Approximation | regression tests, coefficient sign verification |
| `kriging_cross_validation` | interpolation diagnostics | leave-one-out cross-validation for kriging quality | Validated | regression tests, RMSE/MAE computation verification |

## High-Risk Naming Gaps

These tools currently need extra documentation because their names are stronger than their present implementations.

### `kriging_surface`

Current implementation solves an ordinary-kriging system with spherical, exponential, gaussian, and hole-effect semivariogram options, treats `sill` consistently with PyKrige's full-sill parameterization, reproduces source values exactly when the nugget is zero, and matches multiple fixed PyKrige reference fixtures. The `auto_fit_variogram` parameter enables automatic variogram model selection via weighted SSE grid search over candidate models (spherical, exponential, gaussian). Leave-one-out cross-validation is available via `kriging_cross_validation()` for quality assessment.

### `thiessen_polygons`

Current implementation now produces exact Voronoi cells when Shapely is available and falls back to the older grid ownership approximation otherwise. Public docs should call out the fallback clearly so the exact path is not overstated in minimal installs.

### `hotspot_getis_ord`

Current implementation now uses PySAL `esda.G_Local` when the optional comparison stack is installed and falls back to the lighter analytic implementation otherwise. Public docs should describe both modes explicitly and avoid claiming permutation inference on the fallback path.

### `spatial_regression`

Current implementation is a compact OLS solve with coefficient standard errors, t-statistics, p-values, and residual summaries. It now matches `statsmodels.OLS` fixtures for coefficients, fitted values, residuals, $R^2$, adjusted $R^2$, residual degrees of freedom, residual scale, RMSE, standard errors, t-statistics, and p-values across noisy, constant-response, and rank-stress cases. It uses a design-matrix pseudoinverse path when NumPy is available so the current rank-deficient inference fixtures follow `statsmodels` closely, while broader model diagnostics still remain out of scope.

### `weighted_local_summary`

Current implementation now provides full GWR functionality with Gaussian-weighted local coefficient solve, leave-one-out cross-validation bandwidth selection (golden section search), and local R² computation. The `auto_bandwidth` parameter enables automatic optimal bandwidth selection. `weighted_local_summary()` is the clearer public name, while `geographically_weighted_summary()` remains for compatibility.

## How To Talk About These Tools Publicly

- Use `deterministic transformation` or `deterministic graph analysis` for direct transformation and traversal tools.
- Use `validated implementation` for tools with cross-validation against reference libraries (Shapely, SciPy, PySAL, PyKrige, statsmodels).
- Use `lightweight operational approximation` for gridded surfaces and simplified local statistics without external parity.
- Use `greedy plus local improvement heuristic` for route sequencing and facility location.
- Avoid calling the current fallback `hotspot_getis_ord`, fallback `thiessen_polygons`, or `spatial_regression` implementation reference-grade until external parity is added on all code paths.

## Required Proof Before Stronger Claims

- Broaden `kriging_surface` parity against a true kriging implementation beyond the current fixture families if additional variogram models or anisotropy support are added.
- Keep `thiessen_polygons` exact-path tests in place and document the fallback behavior clearly.
- Keep `hotspot_getis_ord` parity fixtures against PySAL local Gi* outputs and document the fallback behavior clearly.
- Broaden `spatial_regression` parity beyond the current `statsmodels.OLS` fixtures if we want to expose additional diagnostics beyond the current OLS scope.
- Keep `weighted_local_summary()` as the preferred documented name, with `geographically_weighted_summary()` retained as the compatibility alias.
- Add cross-validation against PySAL `esda` for `bivariate_morans_i`, `local_gearys_c`, and `spatial_scan_statistic` when those libraries are available.
- Add parity fixtures against scikit-learn for `optics_clustering` beyond the current cluster-separation tests.