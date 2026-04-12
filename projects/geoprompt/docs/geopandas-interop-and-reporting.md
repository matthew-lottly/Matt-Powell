# GeoPandas Interop And Reporting

This workflow is the shortest path from GeoPrompt analysis to GeoPandas-style inspection and exportable scenario outputs.

## Install

Use the IO or full extras when you want GeoPandas interop:

```bash
pip install geoprompt[io]
```

or:

```bash
pip install geoprompt[all]
```

## Round-trip A GeoPromptFrame Through GeoPandas

```python
import geoprompt as gp

frame = gp.GeoPromptFrame.from_records(
    [
        {"site_id": "a", "geometry": {"type": "Point", "coordinates": (-111.9, 40.7)}},
        {"site_id": "b", "geometry": {"type": "Point", "coordinates": (-112.0, 40.8)}},
    ],
    crs="EPSG:4326",
)

geodataframe = gp.to_geopandas(frame)
restored = gp.from_geopandas(geodataframe)
print(len(restored), restored.crs)
```

## Export Scenario Reports

`build_scenario_report(...)` creates the machine-friendly report object. `export_scenario_report(...)` writes it to disk as JSON, CSV, Markdown, or HTML.

```python
import geoprompt as gp

report = gp.build_scenario_report(
    baseline_metrics={"served_load": 180.0, "deficit": 0.12},
    candidate_metrics={"served_load": 205.0, "deficit": 0.05},
    baseline_name="existing network",
    candidate_name="reinforced network",
    higher_is_better=["served_load"],
    metadata={"scenario_id": "network-reinforcement-demo"},
)

gp.export_scenario_report(report, "outputs/scenario-report.json")
gp.export_scenario_report(report, "outputs/scenario-report.csv")
gp.export_scenario_report(report, "outputs/scenario-report.md")
gp.export_scenario_report(report, "outputs/scenario-report.html")
```

The JSON export preserves the full structure. The CSV export flattens metric comparisons into one row per metric. The Markdown export is useful for issues, PRs, and docs. The HTML export now includes an inline metric delta chart for quick review and sharing.

If you want a dataframe-like table object instead of a raw dict, convert the report directly:

```python
import geoprompt as gp

report = gp.build_scenario_report(
    baseline_metrics={"served_load": 180.0, "deficit": 0.12},
    candidate_metrics={"served_load": 205.0, "deficit": 0.05},
    higher_is_better=["served_load"],
)

table = gp.scenario_report_table(report)
print(table.columns)
print(table.to_markdown())
print(table.summarize("direction", {"delta_percent": "mean"}).to_markdown())
```

## Batch Equation Helpers

GeoPrompt now includes broader NumPy-backed batch helpers for repeated modeling workloads:

- `vectorized_decay(...)`
- `vectorized_gravity_interaction(...)`
- `vectorized_service_probability(...)`
- `batch_accessibility_scores(...)`

`GeoPromptFrame` also exposes row-wise wrappers when your values already live in columns:

- `frame.batch_accessibility_scores(...)`
- `frame.batch_accessibility_table(...)`
- `frame.gravity_interaction_series(...)`
- `frame.gravity_interaction_table(...)`
- `frame.service_probability_series(...)`
- `frame.service_probability_table(...)`

The package-level batch helpers also have table-returning companions:

- `batch_accessibility_table(...)`
- `gravity_interaction_table(...)`
- `service_probability_table(...)`

`PromptTable` also supports lightweight grouped summaries for reporting workflows:

```python
import geoprompt as gp

table = gp.batch_accessibility_table(
    supply_rows=[[200.0], [180.0], [75.0]],
    travel_cost_rows=[[0.5], [0.6], [1.1]],
    row_ids=["north", "north", "south"],
)

summary = table.summarize("row_id", {"accessibility_score": "mean"})
print(summary.to_markdown())
```

## Indexed Bounds Queries

For repeated bounding-box filters, build a reusable spatial index once and pass it back into the frame.

```python
import geoprompt as gp

frame = gp.read_features("data/sample_features.json", crs="EPSG:4326")
index = frame.build_spatial_index()

window = frame.query_bounds_indexed(
    min_x=-111.97,
    min_y=40.68,
    max_x=-111.84,
    max_y=40.79,
    mode="intersects",
    spatial_index=index,
)

print(len(window))
```

The same index-backed path now supports repeated Euclidean join workflows such as `nearest_join(...)`, `proximity_join(...)`, and `spatial_join(...)` without changing their public API.

When benchmarking or validating baseline behavior, you can disable index acceleration explicitly:

```python
joined = frame.nearest_join(targets, k=2, use_spatial_index=False)
indexed = frame.nearest_join(targets, k=2, use_spatial_index=True)
```

## Multi-Scenario Pages

Use the multi-scenario helpers for portfolio-style comparisons against a baseline:

```python
import geoprompt as gp

report = gp.build_multi_scenario_report(
    {
        "baseline": {"deficit": 0.20, "served": 100.0},
        "scenario_a": {"deficit": 0.11, "served": 108.0},
        "scenario_b": {"deficit": 0.08, "served": 112.0},
    },
    baseline_name="baseline",
    higher_is_better=["served"],
)

gp.export_multi_scenario_report(report, "outputs/multi-scenario.html")
gp.export_multi_scenario_report(report, "outputs/multi-scenario.csv")
```

## PromptTable Operations

`PromptTable` now supports lightweight filtering, joining, pivoting, and grouped summaries:

```python
table = gp.batch_accessibility_table(
    supply_rows=[[200.0], [180.0], [75.0]],
    travel_cost_rows=[[0.5], [0.6], [1.1]],
    row_ids=["north", "north", "south"],
)

north = table.where(row_id="north")
summary = table.summarize("row_id", {"accessibility_score": "mean"})
pivot = table.pivot(index="row_id", columns="decay_method", values="accessibility_score", agg="mean")
```

Example:

```python
import geoprompt as gp

scores = gp.batch_accessibility_scores(
    supply_rows=[[200.0, 100.0, 30.0], [150.0, 90.0, 25.0]],
    travel_cost_rows=[[0.5, 1.0, 2.5], [0.4, 0.8, 1.8]],
    decay_method="exponential",
    rate=0.6,
)

flows = gp.vectorized_gravity_interaction(
    origin_masses=[100.0, 120.0],
    destination_masses=[40.0, 60.0],
    generalized_costs=[1.2, 2.4],
    gamma=1.3,
)
```

For a runnable end-to-end example, see `examples/geopandas_roundtrip_report.py`.