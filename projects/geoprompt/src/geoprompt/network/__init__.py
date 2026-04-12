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
]
