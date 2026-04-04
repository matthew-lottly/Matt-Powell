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
```

## CLI commands

```powershell
python -m geoprompt.demo accessibility --format csv --output-dir outputs
python -m geoprompt.demo gravity-flow --format json --output-dir outputs
python -m geoprompt.demo suitability --format geojson --output-dir outputs
```
