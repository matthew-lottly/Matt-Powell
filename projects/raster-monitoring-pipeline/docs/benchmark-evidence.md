# Benchmark Evidence

Evaluation context for the raster monitoring pipeline.

## Change Detection Framework

The pipeline compares two raster snapshots (baseline and later) to identify spatial change:

| Step | Method | Output |
| --- | --- | --- |
| Cell delta | Per-cell difference (later - baseline) | Delta grid |
| Absolute change | Magnitude of delta values | Change magnitude grid |
| Hotspot flagging | Threshold on absolute change | Binary hotspot mask |
| Regional summary | Aggregation by spatial zone | Change report |

## Evaluation Metrics

- **Changed cells**: count and percentage of cells exceeding the change threshold
- **Mean change magnitude**: average absolute delta across all cells
- **Hotspot density**: fraction of cells flagged as hotspots
- **Regional change ranking**: zones sorted by total change magnitude

## Expected Outputs on Sample Data

Using the built-in grid fixtures:

| Metric | Value | Notes |
| --- | --- | --- |
| Grid size | Small demonstration grid | Not representative of satellite resolution |
| Change threshold | Configurable | Default set for clear demonstration |
| Hotspot fraction | Varies by threshold | Lower threshold = more hotspots |

## Downstream Integration

The change report can feed into:
- Dashboard alert systems (high-change zones trigger notifications)
- Time-series tracking (run the pipeline on sequential snapshots)
- Analyst triage workflows (prioritize field visits by change severity)

## Limitations

- Sample data uses small synthetic grids, not real satellite imagery
- No atmospheric correction or radiometric normalization
- Single-band comparison only (no spectral index workflows)
- The pipeline demonstrates the pattern, not production-scale raster processing
