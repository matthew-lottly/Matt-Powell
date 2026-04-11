# API Stability Guide

This page distinguishes stable APIs from advanced/experimental APIs.

## Stable APIs

These are intended for long-term use with backward compatibility within minor releases.

- IO core: `read_data`, `iter_data`, `write_data`, `read_table`
- IO convenience: `read_csv_points`, `iter_csv_points`, `read_data_with_preset`, `iter_data_with_preset`
- Core frame access and geometry helpers in `geoprompt` package root
- Core network routing: `build_network_graph`, `shortest_path`, `service_area`, `od_cost_matrix`

## Advanced APIs

These APIs are powerful but may evolve faster.

- Network streaming/batch tuning: `iter_od_cost_matrix_batches`, `utility_bottlenecks_stream`
- Network preset wrappers: `od_cost_matrix_with_preset`, `utility_bottlenecks_with_preset`
- Domain-specific utility routines with planning heuristics
- Progress callback payload schemas (event fields may expand)

## Versioning Expectations

- Patch releases: bug fixes and compatibility-safe improvements.
- Minor releases: additive features and occasional advanced-API adjustments.
- Major releases: breaking changes when needed.

## Guidance

- Build long-lived production pipelines on stable APIs.
- Use advanced APIs when scale/performance controls are required.
- Pin versions in production if using advanced APIs heavily.
