# GeoPrompt Tutorial

This tutorial walks through a complete geoprompt workflow from loading data
to generating enriched reports and review charts.

## 1. Installation

```bash
pip install geoprompt
# Or for full development:
pip install -e ".[dev,overlay,projection]"
```

## 2. Loading Features

```python
from geoprompt import read_features

frame = read_features("data/sample_features.json", crs="EPSG:4326")
print(f"Loaded {len(frame)} features")
print(f"Geometry types: {sorted(set(frame.geometry_types()))}")
print(f"Bounds: {frame.bounds()}")
```

## 3. Computing Spatial Metrics

### Neighborhood Pressure
```python
pressure = frame.neighborhood_pressure(
    weight_column="demand_index",
    scale=0.14,
    power=1.6,
)
```

### Anchor Influence
```python
influence = frame.anchor_influence(
    weight_column="priority_index",
    anchor="north-hub-point",
    scale=0.14,
    power=1.4,
)
```

### Corridor Accessibility
```python
corridor = frame.corridor_accessibility(
    weight_column="capacity_index",
    anchor="north-hub-point",
    scale=0.18,
    power=1.4,
)
```

## 4. Enriching the Frame

```python
enriched = frame.assign(
    neighborhood_pressure=pressure,
    anchor_influence=influence,
    corridor_accessibility=corridor,
    geometry_type=frame.geometry_types(),
    geometry_length=frame.geometry_lengths(),
    geometry_area=frame.geometry_areas(),
)
```

## 5. Interaction Tables

```python
interactions = enriched.interaction_table(
    origin_weight="capacity_index",
    destination_weight="demand_index",
    scale=0.16,
    power=1.5,
    preferred_bearing=135.0,
)
top_5 = sorted(interactions, key=lambda x: float(x["interaction"]), reverse=True)[:5]
```

## 6. Spatial Joins

```python
regions = read_features("data/benchmark_regions.json", crs="EPSG:4326")
joined = regions.spatial_join(enriched, predicate="intersects")
```

## 7. CRS Reprojection

```python
projected = frame.to_crs("EPSG:3857")
print(f"Projected bounds: {projected.bounds()}")
```

## 8. Exporting Results

```python
from geoprompt import write_geojson
from geoprompt.io import write_json

write_geojson("outputs/enriched.geojson", enriched)
write_json("outputs/report.json", {"records": enriched.to_records()})
```

## 9. Generating Charts

```python
from geoprompt.demo import export_pressure_plot

export_pressure_plot(
    enriched.to_records(),
    Path("outputs/charts/pressure.png"),
    colormap="colorblind_safe",
    style_preset="publication",
    export_formats=["png", "svg"],
)
```

## 10. CLI Usage

```bash
# Full report
geoprompt-demo

# Dry run (validate only)
geoprompt-demo --dry-run --verbose

# Skip expensive computations
geoprompt-demo --skip-expensive --no-asset-copy

# Custom chart settings
geoprompt-demo --colormap viridis --style-preset dark --chart-title "My Analysis"

# CSV export
geoprompt-demo --format csv
```

## 11. Configuration File

Create `geoprompt.toml` in your project root:

```toml
[geoprompt]
scale = 0.14
power = 1.6
top_n = 10
colormap = "colorblind_safe"
verbose = true
```

## 12. Sensitivity Analysis

```python
from geoprompt.sensitivity import parameter_sweep

results = parameter_sweep(
    lambda scale, power: frame.neighborhood_pressure("demand_index", scale=scale, power=power),
    parameter_grid={"scale": [0.1, 0.14, 0.2], "power": [1.0, 1.6, 2.0]},
)
for r in results:
    print(f"scale={r.parameters['scale']}, power={r.parameters['power']}: mean={r.metric_summary['mean']:.4f}")
```

## 13. Custom Decay Functions

```python
from geoprompt.plugins import register_decay, get_decay

def my_custom_decay(distance, scale=1.0, power=2.0):
    return max(0, 1 - (distance / scale) ** power)

register_decay("custom", my_custom_decay)
fn = get_decay("custom")
```
