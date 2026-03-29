# GEE Runbook

## Purpose

Use this runbook to reproduce the Gulf Coast inundation workflow inside the Google Earth Engine Code Editor and then summarize the exported validation tables locally.

## Step 1: Open the Main Script

- Copy `earthengine/gulf_coast_inundation_frequency.js` into the Earth Engine Code Editor.
- Confirm the date range, cloud threshold, AWEIsh threshold, and export folder values at the top of the file.
- Run the script to inspect the study area, observation counts, and inundation-frequency layers.

## Step 2: Export the Inundation Layers

- Set `exportToDrive` to `true`.
- Run the script again.
- Export the stacked image that includes raw inundation frequency, episodic inundation frequency, and observation support.

## Step 3: Prepare Validation AOIs

- Start from `data/gauge_validation_manifest.geojson`.
- Upload that file into Earth Engine as a table asset.
- Buffer the points or replace them with final AOI polygons if you want custom reach extents.
- Keep at least these properties on each feature:
  - `gaugeId`
  - `gaugeName`
- Update `validationAssetId` in `earthengine/gauge_validation_export.js` to point to your uploaded asset.

## Step 4: Export Gauge Validation Tables

- Run `earthengine/gauge_validation_export.js`.
- Export the resulting CSV from Drive.
- Join it with NWIS stage-height records outside Earth Engine so each row contains:
  - `gaugeId`
  - `gaugeName`
  - `date`
  - `stageFt`
  - `percentInundated`

## Step 5: Summarize Locally

- Save the merged CSV locally.
- Run the CLI:

```bash
gulf-coast-validation --input-path data/your_merged_validation.csv
```

- Inspect `outputs/gulf_coast_validation_summary.json`.

## Notes

- The scripts intentionally suppress near-permanent water in the episodic layer so the Gulf itself does not dominate the visualization.
- Observation-support counts matter. Low-scene areas should be treated cautiously before drawing strong validation conclusions.
- The checked-in manifest is a candidate validation set, not a claim that all ten gauges will validate equally well.