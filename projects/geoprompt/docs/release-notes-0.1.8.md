# Geoprompt 0.1.8 Release Notes

## Highlights

- Expanded equation-powered analysis tooling with 10 new callable maps.
- Added a new 40-equation extension set with dedicated tests.
- Strengthened validation with open-source parity checks and full CLI matrix coverage.
- Cleaned generated artifacts from version control and tightened output hygiene.
- Refreshed docs with clearer markdown graphs and updated release guidance.

## New Analysis Tools

- `drought_stress_map(...)`
- `heat_island_map(...)`
- `school_access_map(...)`
- `healthcare_access_map(...)`
- `food_desert_map(...)`
- `digital_divide_map(...)`
- `wildfire_risk_map(...)`
- `emergency_response_map(...)`
- `infrastructure_lifecycle_map(...)`
- `adaptive_capacity_map(...)`

## Equation Expansion

- Added 40 new equations for resilience, risk, access, equity, performance, uncertainty, and lifecycle scoring.
- New catalog: [equations-extended-catalog.md](equations-extended-catalog.md)

## Validation and Correctness

- Equations: `pytest tests/test_equations.py tests/test_new_equations.py`
- Tools: `pytest tests/test_analysis_tools.py tests/test_tools_open_source_parity.py`
- CLI matrix: `pytest tests/test_cli.py`
- Full suite: `pytest`
- Open-source comparison: `python -m geoprompt.compare --output-dir outputs`

## Documentation and Cleanup

- Updated system and data-flow graphs in:
  - [architecture.md](architecture.md)
  - [data-flow.md](data-flow.md)
  - [../README.md](../README.md)
- Removed stale generated files from tracking and ignored runtime output artifacts.

## Network and Utilities Analysis (Post-0.1.8 Additions)

- Added a dedicated network engine in `src/geoprompt/network.py` with:
  - shortest-path routing
  - service-area tracing
  - OD least-cost matrix generation
  - demand-to-supply utility allocation
  - bottleneck stress scanning on loaded edges
  - topology QA (isolates, dangling nodes, components, duplicate links)
  - multi-criteria impedance routing
  - constrained capacity-aware assignment with iterative rerouting penalties
  - capacity-spill OD assignment with partial demand service tracking
  - cached router support and landmark lower-bound helpers
  - electric feeder trace, outage isolation, water pressure-zone trace, and gas shutdown impact
  - device-state propagation by device type/state (open/closed/unknown)
  - scenario runner for baseline/outage/restoration with critical edge/node rankings
- Added new utility equations in `src/geoprompt/equations.py`:
  - `utility_capacity_stress_index(...)`
  - `utility_headloss_hazen_williams(...)`
  - `utility_reliability_score(...)`
  - `utility_service_deficit(...)`
- Added callable analysis methods in `GeoPromptFrame.analysis` and matching frame wrappers:
  - `network_shortest_path(...)`
  - `network_service_area(...)`
  - `network_od_matrix(...)`
  - `utility_supply_allocation(...)`
  - `utility_bottleneck_scan(...)`

## 19 New Utility Network Analysis Functions

### Electric Domain
- **`criticality_ranking_by_node_removal(...)`** — Ranks nodes by outage impact; removes each node and re-runs routing to score the downstream reachability loss.
- **`load_transfer_feasibility(...)`** — Checks if a tie edge can absorb combined feeder load during transfers; validates capacity constraints.
- **`feeder_load_balance_swap(...)`** — Discovers boundary edges between over-loaded and under-loaded feeders and suggests optimal transfer shifts.

### Water Domain  
- **`pipe_break_isolation_zones(...)`** — BFS from break endpoints to identify affected service zones, stopping at isolation valves.
- **`pressure_reducing_valve_trace(...)`** — Dijkstra-based headloss profiling from a PRV; accumulates residual head and flags low-pressure nodes.
- **`fire_flow_demand_check(...)`** — Validates hydrant flow adequacy; compares residual capacity (`capacity - flow`) against demand thresholds per hydrant.

### Gas Domain
- **`gas_pressure_drop_trace(...)`** — Weymouth-style resistance proxy (`cost × flow / diameter²`) to model pressure drop through distribution network.
- **`gas_odorization_zone_trace(...)`** — Multi-source Dijkstra per odorizer node; detects zones served by >1 odorizer (overlap detection).
- **`gas_regulator_station_isolation(...)`** — Blocks regulator-incident edges and finds isolated downstream nodes using reachability from supply nodes.

### Cross-Utility Domain
- **`co_location_conflict_scan(...)`** — Detects shared node pairs and shared corridors across multi-utility graphs (e.g., electric + water co-location).
- **`interdependency_cascade_simulation(...)`** — Iterative cascade: failed primary nodes → dependent failures → re-check primary isolation; returns iteration count and final failed set.
- **`infrastructure_age_risk_weighted_routing(...)`** — Risk-weighted edge cost: `base_cost × (1 + min(age/design_life, 1.0))`; routes via lowest-risk path.
- **`critical_customer_coverage_audit(...)`** — For each critical customer, identifies SPOF edges on supply path via edge-removal probing.

### Stormwater Domain
- **`stormwater_flow_accumulation(...)`** — Topological sort with cumulative downstream flow; detects capacity exceeded per node.
- **`detention_basin_overflow_trace(...)`** — Routes excess inflow when basin capacity exceeded; traces lowest-cost overflow path to terminal.
- **`inflow_infiltration_scan(...)`** — Flags edges where observed/dry-weather ratio exceeds threshold; special-case handling for edges with no baseline.

### Telecom Domain
- **`fiber_splice_node_trace(...)`** — With circuit endpoints: checks if circuit paths traverse splice node. Without: returns incident edge IDs.
- **`ring_redundancy_check(...)`** — Validates ring topology; for each node, blocks each primary path edge and probes for alternate route to hub.
- **`fiber_cut_impact_matrix(...)`** — Ranks cut-candidate edges by circuits impacted; returns impact matrix sorted descending.

### Testing
- **22 comprehensive test cases** covering all 19 functions with linear graph, ring graph, and multi-utility fixtures; tests verify isolation zones, load transfers, pressure profiles, redundancy validation, cascade propagation, and impact rankings.

## Type System Hardening

- Refactored `NetworkEdge` from `dict[str, object]` to a typed `TypedDict` with 30+ documented fields (edge_id, from_node, to_node, capacity, flow, load, device_type, state, cost, length, congestion, slope, failure_risk, condition, diameter, age, design_life, pressure, headloss, customers, etc.).
- Removed all `# type: ignore` comments from network.py; type checker now validates dictionary field accesses without suppressions.
- Frame.py updated: imported `DistanceMethod` type from equations; all distance methods now use `DistanceMethod` (Literal["euclidean", "haversine"]) instead of generic `str`.

## Versioning

- Package version updated to `0.1.8` in `pyproject.toml`.
- CLI runtime version marker updated to `0.1.8` in `src/geoprompt/demo.py`.
