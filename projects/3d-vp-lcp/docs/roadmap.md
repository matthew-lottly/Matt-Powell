# Roadmap

This checklist tracks the next 50 tasks required to move 3D-VP-LCP from a research prototype to a usable, testable workflow on real LiDAR data.

## Near Term

- [x] Add a real CLI command that runs the full pipeline from LAS/LAZ input to corridor output.
- [x] Define a stable config schema for weights, voxel size, species traits, and output paths.
- [x] Replace percentile-based height normalization with a DTM-based normalization path.
- [x] Add real habitat patch source and target selection instead of the placeholder path endpoints.
- [x] Add corridor export as CSV.
- [x] Add corridor export as GeoJSON-ready point output.
- [x] Add a reproducible benchmark script that reports runtime on the sample dataset.
- [x] Add a smoke test that runs the full pipeline from input to least-cost path.
- [ ] Run the tutorial notebook end to end and lock in a reproducible execution path.
- [x] Add a real public LiDAR tile example beyond the synthetic sample.
- [x] Add parameterized tests that vary voxel size and confirm valid outputs.
- [x] Support filtering LAS classifications explicitly for vegetation and non-vegetation classes.
- [x] Add bounds checking and clear errors for empty or invalid point clouds.
- [x] Add metadata reporting for point count, extent, elevation range, and class counts.
- [x] Document expected LAS classification assumptions in the README.

## Data and Voxel Pipeline

- [x] Add tile-based loading for large LAS/LAZ files to avoid full-file reads.
- [x] Add support for clipping by polygon instead of only bounding box.
- [ ] Add optional input for an external DTM raster.
- [x] Add optional input for slope rasters.
- [x] Add optional input for land-cover rasters.
- [ ] Add tests for clipped input, empty tiles, and malformed files.
- [ ] Define a small real-data fixture strategy for integration tests without bloating the repo.
- [ ] Add tests for voxelization at voxel boundaries and explicit origin offsets.
- [x] Add support for non-cubic voxel dimensions.
- [x] Rework VGF so the implementation matches the intended per-column and per-height definition more directly.
- [ ] Add tests that confirm VGF responds correctly to canopy-density changes.
- [ ] Add sparse-array or chunked representations to reduce memory pressure on larger scenes.
- [x] Add a diagnostic summary of occupied voxels by height band.
- [x] Add export of occupancy and VGF grids for inspection.
- [x] Add tests for voxel-size sensitivity using the same scene at multiple resolutions.
- [x] Add timing and profiling hooks for voxelization separate from graph construction.
- [ ] Add notebook visuals for occupancy and VGF distributions before routing.

## Resistance and Species Logic

- [x] Add species profiles stored as JSON or YAML instead of hard-coded notebook parameters.
- [x] Add support for stratum-preference weighting instead of only hard height cutoffs.
- [x] Replace the simple width filter with a stronger local corridor-width measure.
- [ ] Add tests for vertical-clearance logic using controlled synthetic voxel stacks.
- [ ] Add tests that verify width filtering removes narrow corridors but preserves valid ones.
- [ ] Add species-specific land-cover penalties.
- [x] Add resistance normalization so weight combinations stay interpretable across datasets.
- [x] Add a sensitivity-analysis tool for sweeping alpha, beta, gamma, and delta.
- [x] Add summary metrics showing how many voxels are removed by each filter stage.
- [ ] Add visual comparisons of pre-filter and post-filter resistance fields.

## Routing, Performance, and Validation

- [x] Add A* routing as an option alongside Dijkstra.
- [ ] Add 18-neighbor and 26-neighbor routing to the CLI and notebook.
- [x] Add accumulated-cost volume output, not just a single least-cost path.
- [x] Add optional corridor ensembles from multiple parameter sets.
- [ ] Add performance tests on larger synthetic scenes to identify graph bottlenecks.
- [ ] Add a faster large-graph backend option if NetworkX becomes limiting.
- [x] Add tests for disconnected graphs and expected no-path behavior.
- [x] Add bottleneck analysis metrics such as highest-cost voxel and narrowest passage.
- [x] Add optional circuit-theory mode behind a separate dependency path.
- [x] Add a run report artifact with runtime, path cost, path length, mean corridor height, and filter counts.
