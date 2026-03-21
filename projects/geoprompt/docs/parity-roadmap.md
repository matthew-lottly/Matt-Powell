# Parity Roadmap

## Purpose

This roadmap turns the tool audit into an execution plan. The intent is to move Geoprompt from internally tested, benchmarked tools toward externally defensible analytical methods with repeatable proof.

## Principles

- Prefer exact parity against a well-known reference implementation when one exists.
- If exact parity is not the goal, document the narrower operational scope explicitly.
- Separate performance evidence from correctness evidence.
- Keep each parity target small enough to verify with stable fixtures in CI.

## Phase 1: Statistical And Regression Parity

### `spatial_regression`

- Reference baseline: `statsmodels.OLS`
- Proof targets:
  - coefficient parity
  - intercept parity
  - prediction parity
  - residual parity
  - $R^2$ and adjusted $R^2$ parity
  - standard error parity within a defined tolerance
- Minimum fixture set:
  - exact linear relation
  - noisy linear relation
  - rank-deficient design matrix
  - constant dependent variable
- Current status:
  - OLS coefficients, predictions, residuals, standard errors, t-statistics, and p-value fields are now emitted by Geoprompt
  - `statsmodels.OLS` parity fixtures are now in place for coefficients, fitted values, residuals, $R^2$, adjusted $R^2$, residual degrees of freedom, residual scale, RMSE, standard errors, t-statistics, and p-values across noisy, constant-response, rank-stress, larger 10-observation 3-predictor, near-singular design, and high-leverage point cases
  - remaining work is now about any additional diagnostics we choose to expose, not the current inference path

### `weighted_local_summary`

- Reference baseline: a dedicated GWR package or a documented custom weighted-local-regression baseline
- Proof targets:
  - local coefficient reasonableness on synthetic non-stationary fields
  - bandwidth sensitivity checks
  - stable output ordering and reproducibility
  - sparse-neighborhood stability
  - `local_r_squared` intentional absence verification
- Decision gate:
  - either promote this into a fuller GWR implementation
  - or rename and document it permanently as a local weighted summary tool
- Current status:
  - the implementation remains a weighted local summary rather than full GWR
  - `weighted_local_summary()` is now the clearer preferred name while `geographically_weighted_summary()` remains for compatibility
  - reproducibility, sparse-neighborhood stability, and `local_r_squared` intentional-absence fixtures are now in place
  - export verification confirms `weighted_local_summary` is accessible on `GeoPromptFrame`

### `hotspot_getis_ord`

- Reference baseline: PySAL `esda`
- Proof targets:
  - local Gi* z-score parity on fixed fixtures
  - classification parity for hotspot, coldspot, and non-significant cells
  - significance parity under the chosen weighting scheme
- Minimum fixture set:
  - clustered high values
  - clustered low values
  - uniform field
  - edge-heavy sparse field
- Current status:
  - direct parity fixtures against `esda.G_Local` are now in place for both the original and a clustered layout on the optional comparison stack
  - uniform-field not-significant fixture confirms no false positives
  - classification stability fixture confirms deterministic output
  - fallback analytic mode still needs explicit scope language and should not be treated as fully equivalent to PySAL

## Phase 2: Interpolation And Partition Parity

### `thiessen_polygons`

- Reference baseline: exact Voronoi or Thiessen construction via Shapely or SciPy-compatible tooling
- Proof targets:
  - polygon ownership parity
  - area parity within tolerance
  - deterministic clipping to analysis extent
- Current status:
  - exact Voronoi cells via Shapely are now the primary path
  - the older grid approximation remains only as a fallback when the geometry stack is unavailable
  - duplicate-site handling fixture confirms no crash on coincident input
  - four-corner symmetric layout confirms roughly equal-area cells
  - explicit fallback-mode fixture proves grid_approximation output validity

### `kriging_surface`

- Reference baseline: a true kriging implementation
- Proof targets:
  - predicted surface parity on synthetic point fields
  - variance behavior parity
  - consistent response to nugget, sill, and range parameters
- Decision gate:
  - either verify the current ordinary-kriging implementation against an external baseline
  - or narrow the documented scope if the current semivariogram and variance behavior diverge materially
- Current status:
  - ordinary kriging system solving is now implemented
  - spherical, exponential, gaussian, and hole-effect semivariogram options are now implemented
  - exact-at-source interpolation is covered for the zero-nugget case
  - direct PyKrige parity is now in place across multiple fixed spherical, exponential, gaussian, and hole-effect parameter regimes for both predictions and variance, including nonzero-nugget smoothing behavior, irregular five-point layouts, and denser point-layout fixtures
  - nugget-heavy smoothing, short-range isolation, and sill–variance monotonicity behavioral fixtures are now in place

### `idw_interpolation`

- Reference baseline: analytical point sets and a second IDW implementation if available
- Proof targets:
  - exact value recovery at source points
  - monotonic decay behavior away from sources
  - stable gridded output under deterministic ordering

## Phase 3: Optimization And Network Quality

### `route_sequence_optimize`

- Reference baseline: brute-force optimal routing for very small stop counts
- Proof targets:
  - exact optimal-tour parity for `n <= 8` on fixed fixtures
  - explicit detection of unreachable stops
  - route-quality ratio compared to optimum on small graphs
- Current status:
  - greedy seed routing plus `2-opt` local improvement is now implemented
  - a fixed counterexample proves the post-pass improves the seed route on a small network instance
  - a brute-force tiny-graph battery now proves exact optimality across multiple fixed open-path cases, including directed asymmetric, six-stop dense, directed seven-stop dense, and seven-stop dense fixtures
  - non-collinear adversarial layout confirms correctness on 2D geometry
  - equal-cost multi-optima fixture confirms correct cost reporting when ties exist
  - mixed-reachability metadata fixture confirms stop ordering and marking consistency

### `k_shortest_paths`

- Reference baseline: NetworkX or hand-built exact fixtures
- Proof targets:
  - path uniqueness
  - cost ordering monotonicity
  - parity on small directed and undirected graphs

## Phase 4: Aggregation And Surface Documentation

### `spatiotemporal_cube`

- Reference baseline: hand-built expected cube bins
- Proof targets:
  - time boundary correctness
  - cell-boundary correctness
  - aggregation parity for count, sum, mean, min, and max
  - no duplicate assignment for features that land exactly on internal grid boundaries
- Current status:
  - exact-boundary timestamp assignment fixture confirms each point is counted once
  - sparse-bin non-empty fixture confirms only populated bins appear in output
  - sum-equals-input-total fixture confirms aggregation arithmetic

### `contours`, `hillshade`, `slope_aspect`

- Reference baseline: analytical fixtures and documented approximations
- Proof targets:
  - deterministic output counts and value ranges
  - explicit documentation that these methods operate on point-derived interpolated surfaces rather than native raster DEM pipelines
- Current status:
  - contour-level range-within-bounds fixture confirms levels stay within input value range
  - hillshade deterministic-output reproducibility fixture confirms identical calls produce identical results
  - slope_aspect flat-surface zero-slope and tilted-surface positive-slope fixtures confirm expected behavior on analytically clear inputs

## Recommended Implementation Order

1. broaden `spatial_regression` parity fixtures against `statsmodels` across larger and more varied regression families if we want stronger public claims
2. `route_sequence_optimize` broader quality proof against larger brute-force tiny graphs beyond the current undirected and directed asymmetric battery when affordable
3. `hotspot_getis_ord` fallback-scope tightening and broader parity fixtures
4. `thiessen_polygons` fallback-scope tightening and optional dependency guidance
5. `kriging_surface` broader parity against external kriging implementations, denser point layouts, and additional variogram families beyond spherical, exponential, gaussian, and hole-effect
6. `spatiotemporal_cube` edge-boundary fixtures
7. `weighted_local_summary` or `geographically_weighted_summary` comparison against a proper GWR baseline if we want to promote it beyond the current documented weighted-summary scope

## Acceptance Standard

A tool should be considered strongly validated only when all of the following are true:

- deterministic regression coverage exists
- edge-case fixtures exist
- benchmark coverage exists on built-in corpora
- external parity or a documented analytical baseline exists
- public docs describe the method at the same strength as the implementation actually supports