# Callable Analysis Tools Catalog

GeoPrompt now supports GeoPandas-style callable analysis from `GeoPromptFrame.analysis`.

## Primary callable tools

1. `accessibility(...)`
2. `gravity_flow(...)`
3. `suitability(...)`

## Additional callable tools

1. `catchment_competition(...)`
2. `hotspot_scan(...)`
3. `equity_gap(...)`
4. `network_reliability(...)`
5. `transit_service_gap(...)`
6. `congestion_hotspots(...)`
7. `walkability_audit(...)`
8. `gentrification_scan(...)`
9. `land_value_surface(...)`
10. `pollution_surface(...)`
11. `habitat_fragmentation_map(...)`
12. `climate_vulnerability_map(...)`
13. `migration_pull_map(...)`
14. `mortality_risk_map(...)`
15. `market_power_map(...)`
16. `trade_corridor_map(...)`
17. `community_cohesion_map(...)`
18. `cultural_similarity_matrix(...)`
19. `noise_impact_map(...)`
20. `visual_prominence_map(...)`
21. `drought_stress_map(...)`
22. `heat_island_map(...)`
23. `school_access_map(...)`
24. `healthcare_access_map(...)`
25. `food_desert_map(...)`
26. `digital_divide_map(...)`
27. `wildfire_risk_map(...)`
28. `emergency_response_map(...)`
29. `infrastructure_lifecycle_map(...)`
30. `adaptive_capacity_map(...)`
31. `network_shortest_path(...)`
32. `network_service_area(...)`
33. `network_od_matrix(...)`
34. `utility_supply_allocation(...)`
35. `utility_bottleneck_scan(...)`
36. `network_topology_audit(...)`
37. `network_multicriteria_path(...)`
38. `network_capacity_assignment(...)`
39. `electric_feeder_trace(...)`
40. `utility_outage_isolation(...)`
41. `water_pressure_zones(...)`
42. `gas_shutdown_impact(...)`
43. `network_capacity_spill_assignment(...)`
44. `utility_scenario_runner(...)`

## Usage examples

```python
from geoprompt import GeoPromptFrame
from geoprompt.io import read_features

frame = read_features("data/sample_features.json", crs="EPSG:4326")

access = frame.analysis.accessibility(opportunities="demand_index")
flows = frame.analysis.gravity_flow(origin_weight="capacity_index", destination_weight="demand_index")
suitability = frame.analysis.suitability(
    criteria_columns=["demand_index", "capacity_index", "priority_index"],
    criteria_weights=[0.4, 0.35, 0.25],
)

risk = frame.analysis.climate_vulnerability_map(
    exposure_column="priority_index",
    sensitivity_column="demand_index",
    adaptive_column="capacity_index",
)

route = frame.analysis.network_shortest_path(
    from_node_column="from_node",
    to_node_column="to_node",
    origin_node="substation-a",
    destination_node="service-zone-7",
    edge_id_column="edge_id",
    cost_column="travel_cost",
)

allocation = frame.analysis.utility_supply_allocation(
    from_node_column="from_node",
    to_node_column="to_node",
    node_column="node_id",
    supply_column="available_supply",
    demand_column="required_demand",
    edge_id_column="edge_id",
    cost_column="travel_cost",
)

spill = frame.analysis.network_capacity_spill_assignment(
    from_node_column="from_node",
    to_node_column="to_node",
    od_demands=[("plant-a", "zone-1", 120.0)],
    edge_id_column="edge_id",
    cost_column="travel_cost",
    capacity_column="pipe_capacity",
)

scenario = frame.analysis.utility_scenario_runner(
    from_node_column="from_node",
    to_node_column="to_node",
    source_nodes=["substation-a"],
    outage_edges=["line-17", "line-21"],
    restoration_edges=["line-21"],
    critical_nodes=["hospital-1", "pump-station-2"],
    edge_id_column="edge_id",
    cost_column="travel_cost",
)
```

## CLI commands

```powershell
python -m geoprompt.demo accessibility --format csv --output-dir outputs
python -m geoprompt.demo gravity-flow --format json --output-dir outputs
python -m geoprompt.demo suitability --format geojson --output-dir outputs
```
