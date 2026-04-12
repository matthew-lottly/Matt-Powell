# API Stability Guide

This page distinguishes stable APIs from advanced/experimental APIs.

## Stable APIs

These are intended for long-term use with backward compatibility within minor releases.

- IO core: `read_data`, `iter_data`, `write_data`, `read_table`
- IO convenience: `read_csv_points`, `iter_csv_points`, `read_data_with_preset`, `iter_data_with_preset`
- Core frame access and geometry helpers in `geoprompt` package root
- Core network routing: `build_network_graph`, `shortest_path`, `service_area`, `od_cost_matrix`

## Network Module Stable APIs

Core routing and analysis functions suitable for production use:

- `built_network_graph()` — graph construction and validation
- `shortest_path()` — single-origin, single-destination routing
- `service_area()` — reachable nodes within cost threshold
- `od_cost_matrix()` — origin-destination distance matrix
- `allocate_demand_to_supply()` — assignment with capacity constraints
- `analyze_network_topology()` — connectivity and centrality metrics

## Network Module Advanced APIs

Domain-specific utility functions subject to faster evolution:

- Domain routing: `trace_electric_feeder()`, `trace_water_pressure_zones()`, `gas_shutdown_impact()` (utility-specific)
- Catastrophic analysis: `criticality_ranking_by_node_removal()`, `n_minus_one_edge_contingency_screen()`, `pipe_break_isolation_zones()`
- Infrastructure planning: `infrastructure_age_risk_weighted_routing()`, `co_location_conflict_scan()`, `interdependency_cascade_simulation()`
- Streaming/batching: `iter_od_cost_matrix_batches()`, `utility_bottlenecks_stream()` (performance tuning patterns)
- Presets: `od_cost_matrix_with_preset()`, `utility_bottlenecks_with_preset()` (convenience wrappers)

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
