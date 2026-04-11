# Geoprompt 0.1.7 Release Notes

## Highlights

- Added workload preset wrappers to simplify large-data workflows for both IO and network analysis.
- Added progress callback support and stronger input validation for chunked and batched processing APIs.
- Added optional gated CI checks for geospatial integration and benchmark regression coverage.

## What Changed

- Added IO preset and wrapper APIs:
  - `get_workload_preset(...)`
  - `read_data_with_preset(...)`
  - `iter_data_with_preset(...)`
  - `read_csv_points(...)`
  - `iter_csv_points(...)`
- Added network preset and wrapper APIs:
  - `get_network_workload_preset(...)`
  - `od_cost_matrix_with_preset(...)`
  - `utility_bottlenecks_with_preset(...)`
- Added callback progress payloads for:
  - `iter_data(...)`
  - `iter_od_cost_matrix_batches(...)`
  - `utility_bottlenecks_stream(...)`
- Added contract tests to lock callback event key schemas.
- Added optional benchmark regression tests in `tests/test_benchmark_regression.py`.
- Added optional geospatial parquet integration test gate in `tests/test_geoprompt.py`.
- Added new docs:
  - `docs/quickstart-cookbook.md`
  - `docs/api-stability.md`

## Why This Matters

- Users can adopt large-data workflows with fewer tuning decisions via named presets.
- Progress callbacks make long-running operations easier to track and integrate into UIs or logs.
- Optional gates improve confidence that advanced IO and performance-sensitive paths remain stable over time.

## Validation

- Core suite: `pytest` passed.
- Optional geospatial gate: `GEOPROMPT_RUN_GEO_IO=1` passed.
- Optional benchmark gate: `GEOPROMPT_RUN_BENCHMARKS=1` passed.
- Lint: `ruff check src tests` passed.

## Remaining Focus

- Expand geospatial integration coverage to include additional file-based formats where CI runners can support reliable fixtures.
- Continue tuning hotspot methods and larger benchmark corpus coverage for long-term performance tracking.
