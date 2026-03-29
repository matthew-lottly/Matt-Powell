# Demo Storyboard

## Reviewer Goal

Show a Gulf Coast flood-mapping workflow that combines Google Earth Engine image processing with a concrete gauge-validation summary artifact.

## Suggested Walkthrough

1. Start in the README to frame the repo as a recreation of a Gulf Coast inundation study rather than a generic remote-sensing demo.
2. Open the preview asset to show the study-area, heat-map, and gauge-validation concept at a glance.
3. Walk through `earthengine/gulf_coast_inundation_frequency.js` to show the Landsat stack, QA masking, AWEIsh calculation, and export settings.
4. Open `data/gauge_validation_manifest.geojson` to show the real ten-gauge spread across the Gulf Coast validation footprint.
5. Open `earthengine/gauge_validation_export.js` to show how AOI-level inundated area is exported for gauge comparison.
6. Use `docs/gee-runbook.md` to explain how the manifest, Earth Engine AOIs, and NWIS stage data fit into the workflow.
7. Run the local validation CLI and open `outputs/gulf_coast_validation_summary.json` to show the article-style $R^2$ summary.
8. Call out that the repo deliberately separates imagery processing from validation summarization so each step remains reviewable.

## Talking Points

- The Earth Engine scripts are organized around reproducibility, not around one-off Code Editor experimentation.
- The AWEIsh threshold is explicitly configurable because threshold choice is one of the most defensible discussion points in the article.
- The Python summary workflow turns Earth Engine exports into a clean validation report instead of leaving the reviewer with raw CSV files.