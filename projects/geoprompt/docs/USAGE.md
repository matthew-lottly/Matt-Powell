# Network Utilities — Usage Guide

`geoprompt.network` provides a pure-Python graph engine with Dijkstra routing and
**35+** domain-specific utility analysis functions. No external graph library is
required.

---

## Quick Start

```python
from geoprompt.network import build_network_graph, shortest_path, service_area

edges = [
    {"edge_id": "e1", "from_node": "A", "to_node": "B", "cost": 3.0},
    {"edge_id": "e2", "from_node": "B", "to_node": "C", "cost": 2.0},
    {"edge_id": "e3", "from_node": "A", "to_node": "C", "cost": 7.0},
]
graph = build_network_graph(edges, directed=False)

result = shortest_path(graph, origin="A", destination="C")
# result["total_cost"]  -> 5.0  (A→B→C)
# result["path_nodes"]  -> ["A", "B", "C"]
```

---

## Core Routing

### `shortest_path`

Single-pair Dijkstra with optional blocked edges and cost overrides.

```python
result = shortest_path(graph, "A", "C", blocked_edges=["e3"])
```

### `service_area`

Multi-source reachability within a cost threshold.

```python
nodes = service_area(graph, origins=["A"], max_cost=5.0)
# Returns list of {"node", "cost", "source"} dicts
```

### `od_cost_matrix`

Origin-destination cost matrix for multiple pairs.

```python
rows = od_cost_matrix(graph, origins=["A", "B"], destinations=["C"])
```

### `NetworkRouter`

Cached routing helper — avoids recomputing Dijkstra trees from the same origin.

```python
from geoprompt.network import NetworkRouter

router = NetworkRouter(graph)
path = router.shortest_path("A", "C")
matrix = router.od_cost_matrix(["A"], ["C"])
```

---

## Electric

### `trace_electric_feeder`

Trace energised nodes from a feeder source, respecting device states.

```python
from geoprompt.network import trace_electric_feeder

result = trace_electric_feeder(graph, feeder_source="substation-1")
# result["energized_nodes"], result["deenergized_nodes"]
```

### `utility_outage_isolation`

Identify the isolation zone for a faulted edge — nodes that lose supply.

```python
from geoprompt.network import utility_outage_isolation

result = utility_outage_isolation(
    graph,
    faulted_edge="e2",
    supply_nodes=["substation-1"],
)
# result["isolated_nodes"], result["isolation_edge_ids"]
```

### `load_transfer_feasibility`

Check whether load from one feeder can be transferred to another via a tie switch.

```python
from geoprompt.network import load_transfer_feasibility

result = load_transfer_feasibility(
    graph,
    source_feeder_node="feeder-A",
    target_feeder_node="feeder-B",
    tie_switch_edge="tie-1",
)
```

### `feeder_load_balance_swap`

Suggest boundary-edge transfers to balance load between feeders.

```python
from geoprompt.network import feeder_load_balance_swap

result = feeder_load_balance_swap(
    graph,
    feeder_sources=["feeder-A", "feeder-B"],
    load_field="load_kw",
)
```

---

## Water

### `trace_water_pressure_zones`

Trace hydraulic head-loss from a source using a simplified Hazen-Williams model.

```python
from geoprompt.network import trace_water_pressure_zones

result = trace_water_pressure_zones(
    graph,
    source_node="pump-station",
    supply_head=120.0,
    min_residual_pressure=20.0,
)
# result["low_pressure_nodes"], result["zone_pressure_profile"]
```

### `pipe_break_isolation_zones`

BFS-based isolation zone determination bounded by valve locations.

```python
from geoprompt.network import pipe_break_isolation_zones

result = pipe_break_isolation_zones(
    graph,
    break_edge="main-42",
    valve_nodes=["v1", "v2", "v3"],
)
# result["isolated_nodes"], result["boundary_valve_nodes"]
```

### `pressure_reducing_valve_trace`

Trace the downstream zone of a PRV and flag low-pressure nodes.

```python
from geoprompt.network import pressure_reducing_valve_trace

result = pressure_reducing_valve_trace(
    graph,
    prv_node="prv-north",
    downstream_head_limit=60.0,
)
```

### `fire_flow_demand_check`

Check if pipes serving hydrant nodes support required fire flow.

```python
from geoprompt.network import fire_flow_demand_check

results = fire_flow_demand_check(
    graph,
    hydrant_nodes=["hydrant-1", "hydrant-2"],
    demand_gpm=1500.0,
)
```

---

## Gas

### `gas_pressure_drop_trace`

Trace gas pressure drop using a Weymouth-style resistance proxy.

```python
from geoprompt.network import gas_pressure_drop_trace

result = gas_pressure_drop_trace(
    graph,
    source_node="regulator-A",
    inlet_pressure=60.0,
    min_delivery_pressure=0.25,
)
```

### `gas_shutdown_impact`

Quantify demand lost and customers affected when a gas segment is shut down.

```python
from geoprompt.network import gas_shutdown_impact

result = gas_shutdown_impact(
    graph,
    shutdown_edges=["main-7"],
    supply_nodes=["regulator-A"],
    demand_by_node={"c1": 10.0, "c2": 20.0},
)
```

### `gas_odorization_zone_trace`

Map the supply zone of each odorizer and detect overlapping zones.

```python
from geoprompt.network import gas_odorization_zone_trace

results = gas_odorization_zone_trace(graph, odorizer_nodes=["odorizer-1", "odorizer-2"])
```

### `gas_regulator_station_isolation`

Detect downstream segments isolated when a regulator is removed.

```python
from geoprompt.network import gas_regulator_station_isolation

result = gas_regulator_station_isolation(
    graph,
    regulator_node="reg-north",
    supply_nodes=["plant-A"],
)
```

---

## Cross-Utility / Infrastructure

### `co_location_conflict_scan`

Scan for edges from different utility types sharing the same corridor or node pair.

```python
from geoprompt.network import co_location_conflict_scan

conflicts = co_location_conflict_scan(
    {"electric": electric_graph, "water": water_graph}
)
```

### `interdependency_cascade_simulation`

Simulate cascading failures from a primary network into a dependent network.

```python
from geoprompt.network import interdependency_cascade_simulation

result = interdependency_cascade_simulation(
    primary_graph=electric_graph,
    dependent_graph=water_graph,
    dependency_map={"substation-1": ["pump-A", "pump-B"]},
    initial_failed_nodes=["substation-1"],
)
```

### `infrastructure_age_risk_weighted_routing`

Route between two nodes minimising cumulative infrastructure age-risk.

```python
from geoprompt.network import infrastructure_age_risk_weighted_routing

result = infrastructure_age_risk_weighted_routing(
    graph,
    origin="plant-A",
    destination="customer-Z",
    age_field="age_years",
    design_life_field="design_life_years",
)
```

### `critical_customer_coverage_audit`

Audit single points of failure on supply paths to critical customers.

```python
from geoprompt.network import critical_customer_coverage_audit

results = critical_customer_coverage_audit(
    graph,
    critical_customer_nodes=["hospital", "fire-station"],
    supply_nodes=["plant-A"],
)
```

---

## Stormwater / Drainage

### `stormwater_flow_accumulation`

Topological-order BFS (Kahn's algorithm) to accumulate runoff downstream.

```python
from geoprompt.network import stormwater_flow_accumulation

results = stormwater_flow_accumulation(
    graph,
    runoff_by_node={"inlet-1": 5.0, "inlet-2": 3.0},
)
```

### `detention_basin_overflow_trace`

Trace overflow conveyance when a basin exceeds storage capacity.

```python
from geoprompt.network import detention_basin_overflow_trace

result = detention_basin_overflow_trace(
    graph,
    basin_node="basin-A",
    basin_capacity=100.0,
    inflow=150.0,
)
```

### `inflow_infiltration_scan`

Flag pipe segments with observed flow exceeding dry-weather baselines.

```python
from geoprompt.network import inflow_infiltration_scan

results = inflow_infiltration_scan(graph, infiltration_threshold_ratio=1.25)
```

---

## Telecom / Fiber

### `fiber_splice_node_trace`

Enumerate circuits traversing a splice node.

```python
from geoprompt.network import fiber_splice_node_trace

result = fiber_splice_node_trace(
    graph,
    splice_node="splice-14",
    circuit_endpoints=[("co-A", "site-1"), ("co-A", "site-2")],
)
```

### `ring_redundancy_check`

Verify each ring node has at least two edge-independent paths to the hub.

```python
from geoprompt.network import ring_redundancy_check

results = ring_redundancy_check(
    graph,
    ring_nodes=["node-1", "node-2", "node-3"],
    hub_node="hub-central",
)
```

### `fiber_cut_impact_matrix`

Compute the number of circuits impacted by each candidate fiber cut.

```python
from geoprompt.network import fiber_cut_impact_matrix

results = fiber_cut_impact_matrix(
    graph,
    cut_candidate_edges=["span-1", "span-2"],
    circuit_endpoints=[("co-A", "site-1"), ("co-B", "site-2")],
)
```

---

## Analysis & Scenario Planning

### `run_utility_scenarios`

Comprehensive baseline → outage → restoration analysis with edge and node
criticality rankings.

```python
from geoprompt.network import run_utility_scenarios

result = run_utility_scenarios(
    graph,
    supply_by_node={"plant-A": 500.0},
    demand_by_node={"c1": 50.0, "c2": 30.0},
)
# result["baseline"], result["edge_criticality"], result["node_criticality"]
```

### `criticality_ranking_by_node_removal`

Rank nodes by the connectivity loss caused when each is removed.

```python
from geoprompt.network import criticality_ranking_by_node_removal

results = criticality_ranking_by_node_removal(graph)
```

### `analyze_network_topology`

Degree analysis, connected components, self-loops, and duplicate-edge detection.

```python
from geoprompt.network import analyze_network_topology

result = analyze_network_topology(graph)
# result["connected_components"], result["degree_distribution"]
```

### `build_landmark_index` / `landmark_lower_bound`

Pre-compute landmark distances for A*-style pruning.

```python
from geoprompt.network import build_landmark_index, landmark_lower_bound

index = build_landmark_index(graph, landmarks=["hub-A", "hub-B"])
lb = landmark_lower_bound(index, "node-X", "node-Y")
```

### `n_minus_one_edge_contingency_screen`

Run an N-1 screen that removes one edge at a time and ranks outage severity.

```python
from geoprompt.network import n_minus_one_edge_contingency_screen

rows = n_minus_one_edge_contingency_screen(
    graph,
    source_nodes=["substation-A"],
    demand_by_node={"cust-1": 25.0, "cust-2": 40.0},
    critical_nodes=["hospital-1"],
)
# rows[0] is the highest-impact single-edge failure.
```

### `outage_restoration_tie_options`

Evaluate normally-open tie edges and rank which one restores the most targets.

```python
from geoprompt.network import outage_restoration_tie_options

options = outage_restoration_tie_options(
    graph,
    source_nodes=["substation-A"],
    affected_nodes=["cust-5", "cust-9", "cust-11"],
)
# options sorted by restored_target_count descending.
```

### `n_minus_k_edge_contingency_screen`

Generalized N-k screening for simultaneous outages (for example N-2).

```python
from geoprompt.network import n_minus_k_edge_contingency_screen

rows = n_minus_k_edge_contingency_screen(
    graph,
    source_nodes=["substation-A"],
    k=2,
    critical_nodes=["hospital-1", "fire-station-1"],
)
```

### `crew_dispatch_optimizer`

Create a repair sequence that restores the most critical service per repair hour.

```python
from geoprompt.network import crew_dispatch_optimizer

plan = crew_dispatch_optimizer(
    graph,
    source_nodes=["substation-A"],
    failed_edges=["sw-12", "line-44", "line-51"],
    repair_time_by_edge={"sw-12": 1.5, "line-44": 3.0, "line-51": 2.0},
)
```

### `pressure_zone_reconfiguration_planner`

Evaluate valve operations and rank actions that improve pressure-band compliance.

```python
from geoprompt.network import pressure_zone_reconfiguration_planner

actions = pressure_zone_reconfiguration_planner(
    graph,
    source_nodes=["treatment-plant-A"],
    pressure_min=35.0,
    pressure_max=95.0,
)
```

### `pump_station_failure_cascade`

Simulate cascading pump failures through dependency links and optional isolation.

```python
from geoprompt.network import pump_station_failure_cascade

cascade = pump_station_failure_cascade(
    graph,
    pump_nodes=["pump-1", "pump-2", "pump-3"],
    initial_failed_pumps=["pump-1"],
    dependency_map={"pump-1": ["pump-2"], "pump-2": ["pump-3"]},
)
```

### `feeder_reconfiguration_optimizer`

Recommend a tie-switch closure sequence to recover the most customers/critical load.

```python
from geoprompt.network import feeder_reconfiguration_optimizer

result = feeder_reconfiguration_optimizer(
    graph,
    source_nodes=["substation-A"],
    tie_edge_ids=["tie-1", "tie-2", "tie-3"],
    max_switch_actions=2,
)
```

### `resilience_capex_prioritization`

Rank proposed capital projects by resilience gain per capex cost.

```python
from geoprompt.network import resilience_capex_prioritization

ranking = resilience_capex_prioritization(
    graph,
    source_nodes=["substation-A"],
    project_candidates=[
        {
            "project_id": "new-loop-tie",
            "capex_cost": 250000.0,
            "add_edges": [
                {"edge_id": "tie-new", "from_node": "n1", "to_node": "n9", "cost": 1.0}
            ],
        }
    ],
)
```
