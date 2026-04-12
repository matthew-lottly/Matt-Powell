"""Network analysis: graph construction, routing, demand allocation, and utility simulations.

This package provides comprehensive network analysis tools including shortest path
routing, origin-destination matrices, demand allocation, and domain-specific utility
simulations (electric, water, gas, telecom, stormwater).

All public functions and classes are re-exported at the package level for backward
compatibility with code that imported from the original `geoprompt.network` module.
"""

from .core import (
    NETWORK_WORKLOAD_PRESETS,
    NetworkEdge,
    NetworkGraph,
    Traversal,
    get_network_workload_preset,
)
from .routing import (
    build_landmark_index,
    build_network_graph,
    edge_impedance_cost,
    landmark_lower_bound,
    multi_criteria_shortest_path,
    shortest_path,
    service_area,
    NetworkRouter,
)
from .demand import (
    allocate_demand_to_supply,
    iter_od_cost_matrix_batches,
    od_cost_matrix,
    od_cost_matrix_with_preset,
    utility_bottlenecks,
    utility_bottlenecks_stream,
    utility_bottlenecks_with_preset,
)
from .allocation import (
    capacity_constrained_od_assignment,
    constrained_flow_assignment,
)
from .topology import (
    analyze_network_topology,
    co_location_conflict_scan,
)
from .utility import (
    crew_dispatch_optimizer,
    critical_customer_coverage_audit,
    criticality_ranking_by_node_removal,
    detention_basin_overflow_trace,
    feeder_reconfiguration_optimizer,
    fiber_cut_impact_matrix,
    fiber_splice_node_trace,
    fire_flow_demand_check,
    gas_odorization_zone_trace,
    gas_pressure_drop_trace,
    gas_regulator_station_isolation,
    gas_shutdown_impact,
    inflow_infiltration_scan,
    infrastructure_age_risk_weighted_routing,
    interdependency_cascade_simulation,
    load_transfer_feasibility,
    n_minus_k_edge_contingency_screen,
    n_minus_one_edge_contingency_screen,
    outage_restoration_tie_options,
    pipe_break_isolation_zones,
    pressure_zone_reconfiguration_planner,
    pump_station_failure_cascade,
    resilience_capex_prioritization,
    ring_redundancy_check,
    run_utility_scenarios,
    stormwater_flow_accumulation,
    trace_electric_feeder,
    trace_water_pressure_zones,
    utility_outage_isolation,
)

__all__ = [
    # Core types and utilities
    "NETWORK_WORKLOAD_PRESETS",
    "NetworkEdge",
    "NetworkGraph",
    "Traversal",
    "get_network_workload_preset",
    # Routing functions
    "build_landmark_index",
    "build_network_graph",
    "edge_impedance_cost",
    "landmark_lower_bound",
    "multi_criteria_shortest_path",
    "shortest_path",
    "service_area",
    "NetworkRouter",
    # Demand functions
    "allocate_demand_to_supply",
    "iter_od_cost_matrix_batches",
    "od_cost_matrix",
    "od_cost_matrix_with_preset",
    "utility_bottlenecks",
    "utility_bottlenecks_stream",
    "utility_bottlenecks_with_preset",
    # Allocation functions
    "capacity_constrained_od_assignment",
    "constrained_flow_assignment",
    # Topology and cross-network diagnostics
    "analyze_network_topology",
    "co_location_conflict_scan",
    # Utility domain analysis
    "crew_dispatch_optimizer",
    "critical_customer_coverage_audit",
    "criticality_ranking_by_node_removal",
    "detention_basin_overflow_trace",
    "feeder_reconfiguration_optimizer",
    "fiber_cut_impact_matrix",
    "fiber_splice_node_trace",
    "fire_flow_demand_check",
    "gas_odorization_zone_trace",
    "gas_pressure_drop_trace",
    "gas_regulator_station_isolation",
    "gas_shutdown_impact",
    "inflow_infiltration_scan",
    "infrastructure_age_risk_weighted_routing",
    "interdependency_cascade_simulation",
    "load_transfer_feasibility",
    "n_minus_k_edge_contingency_screen",
    "n_minus_one_edge_contingency_screen",
    "outage_restoration_tie_options",
    "pipe_break_isolation_zones",
    "pressure_zone_reconfiguration_planner",
    "pump_station_failure_cascade",
    "resilience_capex_prioritization",
    "ring_redundancy_check",
    "run_utility_scenarios",
    "stormwater_flow_accumulation",
    "trace_electric_feeder",
    "trace_water_pressure_zones",
    "utility_outage_isolation",
]
