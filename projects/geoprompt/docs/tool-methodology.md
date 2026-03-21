# Tool Methodology

## Purpose

This document explains what kind of algorithm each Geoprompt tool currently uses and how strongly it is validated today.

The goal is to avoid overstating maturity. Some tools are deterministic transformations with clear expected behavior. Some are operational approximations designed for fast review workflows. Some are heuristic optimizers or lightweight statistical summaries that still need stronger parity checks against external reference libraries.

## Current Evidence Base

- Regression suite status: `223 passed`
- Validation harness: `geoprompt-compare` and `build_comparison_report(...)`
- Current reference engines where applicable: Shapely, GeoPandas, hand-built analytical fixtures
- Optional reference engines now exercised directly where applicable: Shapely Voronoi, PySAL `esda`, PyKrige, and `statsmodels`
- Current internal standards: deterministic ordering, explicit edge-case tests, benchmark coverage on `sample`, `benchmark`, and `stress` corpora

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
| `idw_interpolation` | interpolation | inverse-distance weighted grid interpolation | Approximation | regression tests |
| `kriging_surface` | interpolation | ordinary kriging system solve with spherical, exponential, gaussian, or hole-effect semivariogram options and shared system inversion | Approximation | regression tests, exact-at-source fixture, multi-case PyKrige parity fixtures across variogram families including nonzero nugget behavior and irregular five-point layouts plus denser spherical, exponential, gaussian, and hole-effect point-layout fixtures, nugget-heavy smoothing envelope, short-range isolation, sill–variance monotonicity, benchmark timings |
| `thiessen_polygons` | partitioning | exact Voronoi cells via Shapely when available, with a documented grid fallback | Approximation | regression tests, exact half-plane fixture, duplicate-site handling, four-corner symmetry area check, explicit fallback-mode fixture, benchmark timings |
| `spatial_weights_matrix` | neighborhood structure | dense pairwise distances converted to sparse neighbor weights | Deterministic | regression tests |
| `hotspot_getis_ord` | local statistic | PySAL-backed local Gi* when `esda` and `libpysal` are installed, with an analytic fallback | Approximation | regression tests, direct PySAL parity fixtures (original and clustered layouts), uniform-field not-significant fixture, classification stability fixture, benchmark timings |
| `local_outlier_factor_spatial` | anomaly detection | LOF-like neighbor density ratio on spatial or hybrid distance | Approximation | regression tests |
| `kernel_density` | density surface | quartic kernel density evaluated on a grid | Approximation | regression tests |
| `standard_deviational_ellipse` | dispersion summary | weighted covariance ellipse | Approximation | regression tests |
| `center_of_minimum_distance` | spatial median | Weiszfeld-style iterative spatial median | Approximation | regression tests |
| `spatial_regression` | regression | lightweight OLS with shared global diagnostics, standard errors, t-statistics, and t-distribution p-values when SciPy is available, with a normal fallback otherwise | Needs Reference Parity | regression tests, benchmark timings, exact-fit synthetic fixture, direct `statsmodels.OLS` parity fixtures for noisy, constant-response, rank-stress, and larger 10-observation 3-predictor cases, near-singular design stability, high-leverage point stability |
| `weighted_local_summary` | local regression summary | Gaussian-weighted local coefficient solve without full GWR diagnostics; `geographically_weighted_summary()` remains as a compatibility alias | Needs Reference Parity | regression tests, alias-equivalence checks, bandwidth-sensitivity checks on synthetic non-stationary fields, sparse-neighborhood stability, `local_r_squared` intentional-absence check, reproducibility proof, benchmark timings |
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
| `geohash_encode` | encoding | geohash string generation from centroid coordinates | Deterministic | regression tests |

## High-Risk Naming Gaps

These tools currently need extra documentation because their names are stronger than their present implementations.

### `kriging_surface`

Current implementation now solves an ordinary-kriging system with spherical, exponential, gaussian, and hole-effect semivariogram options, treats `sill` consistently with PyKrige's full-sill parameterization, reproduces source values exactly when the nugget is zero, and matches multiple fixed PyKrige reference fixtures for both predictions and variance, including nonzero-nugget smoothing behavior plus denser spherical, exponential, and hole-effect point-layout fixtures. Broader external parity would still be useful before calling it fully reference-grade across still wider sampling patterns and additional variogram families.

### `thiessen_polygons`

Current implementation now produces exact Voronoi cells when Shapely is available and falls back to the older grid ownership approximation otherwise. Public docs should call out the fallback clearly so the exact path is not overstated in minimal installs.

### `hotspot_getis_ord`

Current implementation now uses PySAL `esda.G_Local` when the optional comparison stack is installed and falls back to the lighter analytic implementation otherwise. Public docs should describe both modes explicitly and avoid claiming permutation inference on the fallback path.

### `spatial_regression`

Current implementation is a compact OLS solve with coefficient standard errors, t-statistics, p-values, and residual summaries. It now matches `statsmodels.OLS` fixtures for coefficients, fitted values, residuals, $R^2$, adjusted $R^2$, residual degrees of freedom, residual scale, RMSE, standard errors, t-statistics, and p-values across noisy, constant-response, and rank-stress cases. It uses a design-matrix pseudoinverse path when NumPy is available so the current rank-deficient inference fixtures follow `statsmodels` closely, while broader model diagnostics still remain out of scope.

### `weighted_local_summary`

Current implementation gives local coefficients from Gaussian weighting, but it is not yet a full geographically weighted regression implementation. `local_r_squared_gwr` is intentionally not populated yet. For now this should be treated and documented as a weighted local summary tool with simple bandwidth sensitivity checks, not as reference-grade GWR. `weighted_local_summary()` is the clearer public name, while `geographically_weighted_summary()` remains for compatibility.

## How To Talk About These Tools Publicly

- Use `deterministic transformation` or `deterministic graph analysis` for direct transformation and traversal tools.
- Use `lightweight operational approximation` for gridded surfaces and simplified local statistics.
- Use `greedy plus local improvement heuristic` for route sequencing.
- Avoid calling the current fallback `hotspot_getis_ord`, fallback `thiessen_polygons`, `spatial_regression`, or `weighted_local_summary` / `geographically_weighted_summary` implementation reference-grade until external parity is added.

## Required Proof Before Stronger Claims

- Broaden `kriging_surface` parity against a true kriging implementation beyond the current regular-grid, irregular five-point, and denser layout families if additional variogram models or anisotropy support are added.
- Keep `thiessen_polygons` exact-path tests in place and document the fallback behavior clearly.
- Keep `hotspot_getis_ord` parity fixtures against PySAL local Gi* outputs and document the fallback behavior clearly.
- Broaden `spatial_regression` parity beyond the current `statsmodels.OLS` fixtures (which now include larger 10-observation 3-predictor, near-singular, and high-leverage cases) if we want to expose additional diagnostics beyond the current OLS scope.
- Keep `weighted_local_summary()` as the preferred documented name, with `geographically_weighted_summary()` retained as the compatibility alias, until we either compare it against a proper GWR implementation or choose a fuller rename.