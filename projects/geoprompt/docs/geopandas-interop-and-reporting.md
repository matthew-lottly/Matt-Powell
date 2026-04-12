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

The JSON export preserves the full structure. The CSV export flattens metric comparisons into one row per metric. The Markdown export is useful for issues, PRs, and docs. The HTML export produces a lightweight report page for quick review and sharing.

## Batch Equation Helpers

GeoPrompt now includes broader NumPy-backed batch helpers for repeated modeling workloads:

- `vectorized_decay(...)`
- `vectorized_gravity_interaction(...)`
- `vectorized_service_probability(...)`
- `batch_accessibility_scores(...)`

`GeoPromptFrame` also exposes row-wise wrappers when your values already live in columns:

- `frame.batch_accessibility_scores(...)`
- `frame.gravity_interaction_series(...)`
- `frame.service_probability_series(...)`

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