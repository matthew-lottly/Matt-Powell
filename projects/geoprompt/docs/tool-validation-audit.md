# Tool Validation Audit

## Summary

This audit identifies which Geoprompt tools currently need more checking, stronger documentation, or external reference parity before they should be treated as robust analytical implementations.

Current evidence snapshot:

- Full regression suite: `223 passed`
- Comparison and benchmark harness: `build_comparison_report(...)`
- Current benchmark coverage: `sample`, `benchmark`, and `stress` corpora

## Priority Order

### Priority 1: Stronger proof required

These are the tools that most need more checking before they should be presented as strong named algorithms.

| Tool | Why it needs more help | What proof is missing |
| --- | --- | --- |
| `spatial_regression` | current output now includes shared OLS inference fields with direct `statsmodels` parity across noisy, constant-response, rank-stress, larger 10-observation 3-predictor, near-singular design, and high-leverage point fixtures | broader parity only needed if we want to expose additional diagnostics beyond the current OLS scope |
| `weighted_local_summary` | current output provides local coefficients but not a full GWR model or diagnostics; now also proven reproducible, stable under sparse neighborhoods, and verified `local_r_squared` is intentionally absent; `geographically_weighted_summary()` remains as the compatibility alias | parity against a GWR baseline if we want to strengthen the claim beyond the current documented scope |

### Priority 2: Good operational tools, but document the approximation clearly

| Tool | Current issue |
| --- | --- |
| `thiessen_polygons` | exact Voronoi now exists when Shapely is present with duplicate-site handling and symmetric-area verification; fallback path now has explicit fixture proving grid_approximation mode and valid polygon output |
| `hotspot_getis_ord` | optional PySAL parity now has two layout fixtures (original and clustered), uniform-field not-significant fixture, and classification stability proof; the analytic fallback is still lighter-weight and should remain clearly documented |
| `contours` | depends on an interpolated grid rather than a surveyed raster surface; now has contour-level range-within-bounds fixture |
| `hillshade` | derived from IDW interpolation, not a DEM-backed raster engine; now has deterministic-output reproducibility fixture |
| `slope_aspect` | derived from IDW interpolation, not a DEM-backed raster engine; now has flat-surface zero-slope and tilted-surface positive-slope fixtures |
| `idw_interpolation` | useful interpolation, but still a lightweight grid sampler rather than a raster model stack |
| `kernel_density` | direct grid KDE is valid, but bandwidth selection and output interpretation need documentation |
| `local_outlier_factor_spatial` | uses a simplified spatial or hybrid-distance LOF formulation that should be described explicitly |
| `route_sequence_optimize` | now improved by a `2-opt` pass and backed by multi-case tiny-graph brute-force parity, plus non-collinear adversarial, equal-cost multi-optima, and mixed-reachability metadata fixtures, but still remains a heuristic rather than a globally optimal route solver on larger graphs |
| `spatiotemporal_cube` | regular-grid aggregation cube with exact-boundary timestamp, sparse-bin, and sum-equals-input fixtures; not a sparse cube engine or interpolation model |
| `trajectory_staypoint_detection` | clear rule-based method, but sensitive to `max_radius` and `min_duration` assumptions |

### Priority 3: Currently in good shape for their stated scope

These tools now look reasonably well aligned with their claimed scope after the latest tests and hardening work:

- `snap_to_network_nodes`
- `origin_destination_matrix`
- `k_shortest_paths`
- `network_trace`
- `trajectory_simplify`
- `geohash_encode`
- direct geometry transformation and cleanup tools such as `simplify`, `densify`, `smooth_geometry`, `erase`, and `identity_overlay`

## Current Benchmark Snapshot

Median timings gathered from `build_comparison_report(...)` using the built-in corpora:

| Tool | sample | benchmark | stress |
| --- | ---: | ---: | ---: |
| `kriging_surface` | `0.004585s` | `0.009272s` | `0.466831s` |
| `thiessen_polygons` | `0.003406s` | `0.010440s` | `0.384719s` |
| `hotspot_getis_ord` | `0.003248s` | `0.001701s` | `0.010856s` |
| `spatial_regression` | `0.000094s` | `0.000129s` | `0.003138s` |
| `geographically_weighted_summary` | `0.000148s` | `0.000290s` | `0.012226s` |
| `route_sequence_optimize` | `0.000176s` | `0.000203s` | `0.000071s` |
| `trajectory_staypoint_detection` | `0.000026s` | `0.000022s` | `0.000022s` |
| `trajectory_simplify` | `0.000023s` | `0.000018s` | `0.000019s` |
| `spatiotemporal_cube` | `0.000085s` | `0.000130s` | `0.000666s` |

These timings are encouraging for small and medium workloads, but they are performance evidence, not correctness proof.

The main change in this snapshot is `thiessen_polygons`: the exact Shapely path is materially slower on the stress corpus than the old rectangle approximation, which is an expected tradeoff for geometric correctness.

The other notable shift is `kriging_surface`: the ordinary-kriging solve remains substantially more expensive on the stress corpus than the older weighted smoother, which is expected given the matrix solve now performed for each grid point.

## What Was Recently Tightened

- trajectory tools now honor chronological ordering when `time_column` is supplied
- route sequencing now retains unreachable stops and marks them with reachability metadata instead of silently dropping them
- route sequencing now applies an open-path `2-opt` improvement pass after the greedy seed route
- route sequencing now has a tiny-graph brute-force parity test for exact open-path optimality on a fixed fixture
- route sequencing now has a broader tiny-graph brute-force parity battery instead of a single fixed fixture
- Thiessen polygons now use exact Voronoi cells when Shapely is available
- Getis-Ord hotspot output now matches PySAL `esda.G_Local` on the parity fixture when the optional comparison stack is installed
- kriging surface generation now solves an ordinary-kriging system and reproduces source values exactly when the nugget is zero
- kriging surface output now matches multiple PyKrige reference fixtures for both predictions and variance across spherical, exponential, gaussian, and hole-effect parameter regimes, including nonzero-nugget behavior, irregular five-point layouts, and denser point-layout fixtures; nugget-heavy smoothing, short-range isolation, and sill–variance monotonicity behavioral fixtures are also in place
- spatial regression output now matches `statsmodels.OLS` fixtures for coefficients, fitted values, residuals, $R^2$, adjusted $R^2$, residual degrees of freedom, residual scale, RMSE, standard errors, t-statistics, and p-values across noisy, constant-response, rank-stress, larger 10-observation 3-predictor, near-singular design, and high-leverage point cases
- spatiotemporal cube output now has explicit time-bin and grid-boundary fixtures, exact-boundary timestamp assignment, sparse-bin non-empty, and sum-equals-input-total proofs
- weighted local summary now has reproducibility, sparse-neighborhood stability, and `local_r_squared` intentional-absence fixtures
- hotspot Getis-Ord now has two PySAL parity layouts, a uniform-field not-significant fixture, and a classification stability fixture
- Thiessen polygons now have duplicate-site handling, four-corner symmetric area, and explicit fallback-mode fixtures
- contours, hillshade, and slope_aspect now have analytical behavior fixtures (level range, deterministic output, flat/tilted slope)
- route sequencing now has non-collinear adversarial, equal-cost multi-optima, and mixed-reachability metadata fixtures
- optional dependency import checks are now in place for Shapely, PySAL, PyKrige, and statsmodels
- `weighted_local_summary` export accessibility is now verified; legacy `geographically_weighted_summary` alias produces identical output

Those changes reduce behavioral ambiguity and make the tools easier to defend.

## Recommended Proof Plan

### Statistical tools

- Keep parity fixtures against PySAL for local Gi* and any future Moran-style derivatives.
- Expand the `statsmodels` OLS parity fixtures only if we decide to expose additional diagnostics beyond the current OLS scope; the current fixture family (noisy, constant-response, rank-stress, larger 10-observation, near-singular, high-leverage) is now broad.
- Decide whether the current weighted-local-summary behavior should become a real GWR implementation or remain documented under the clearer `weighted_local_summary()` naming with the legacy method retained for compatibility; reproducibility and intentional-absence proofs are now in place.

### Interpolation and partition tools

- Expand `kriging_surface` parity beyond the current regular-grid, irregular five-point, and denser PyKrige fixtures only if additional variogram models or anisotropy support are added.
- Keep the exact Voronoi path as the primary implementation and preserve the fallback only as a clearly documented degraded mode.

### Optimization tools

- Expand `route_sequence_optimize` brute-force optimal-tour checks beyond the current battery (which now includes non-collinear adversarial, equal-cost, and mixed-reachability fixtures) only if larger exact cases are still cheap enough to keep in CI.
- Keep the `2-opt` post-pass and document that the tool is still heuristic.

### Aggregation tools

- Keep adding reference fixtures for `spatiotemporal_cube` around time-bin boundaries, empty bins, and grid boundary assignment; the current exact-boundary, sparse-bin, and sum-totals fixtures cover the core invariants.
- The `contours`, `hillshade`, and `slope_aspect` tools now have analytical behavior fixtures explaining that they operate on interpolated point surfaces; add DEM-backed parity only if a raster source path is implemented.

## Repro Steps

Run the regression suite:

```bash
pytest
```

Generate the comparison and timing snapshot:

```bash
geoprompt-compare
```

For targeted benchmarks, use `build_comparison_report(benchmark_filter=...)` from `src/geoprompt/compare.py`.