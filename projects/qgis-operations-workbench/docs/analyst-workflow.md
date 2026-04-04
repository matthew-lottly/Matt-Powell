# Analyst Workflow

How an analyst uses the QGIS Operations Workbench to prepare and execute a desktop GIS review session.

## Before Opening QGIS

1. Run the workbench builder to generate the current review pack:

```bash
python -m qgis_operations_workbench.workbench --export-geopackage
```

This creates:
- `outputs/qgis_workbench_pack.json` — structured metadata for layers, routes, bookmarks, themes, and tasks
- `outputs/qgis_review_bundle.gpkg` — GeoPackage with station features and route data ready for QGIS

2. Open the GeoPackage in QGIS:
   - Drag `outputs/qgis_review_bundle.gpkg` into the QGIS Layers panel
   - Two layers load: `station_review_points` (features) and `inspection_routes` (routes)

## Setting Up the Review Session

1. **Apply region bookmarks**: The workbench pack defines region bookmarks with extents. Create QGIS spatial bookmarks matching each region so you can jump between areas during review.

2. **Set up map themes**: The pack defines theme groupings (alert stations, healthy stations, inspection routes). Create QGIS map themes to toggle visibility during review.

3. **Review layer styling**: Apply a categorized style to `station_review_points` using the `status` field. Recommended: red for critical/alert, yellow for warning, green for healthy.

## Running the Review

1. Start with the region bookmarks — zoom to each region and note station density and alert clustering
2. Switch to the alert theme to focus on stations with active alerts
3. Follow each inspection route: select routes from the attribute table and zoom to their extent
4. For each route stop, check the nearby station attributes in the identify tool
5. Export any flagged stations to a separate layer or CSV for follow-up

## Generating Print Layouts

The workbench pack defines layout job templates:
- `station_brief_a4` — single-station detail card
- `district_overview_a3` — full district view with route overlay

Use these as guides for creating QGIS print layouts with matching extents and layer combinations.

## After the Review

1. Save any new bookmarks or annotations back to the project file
2. Export flagged features using Processing > Export Selected Features
3. Update the workbench input data if station status or route assignments have changed
4. Re-run the builder to refresh the review pack for the next session

## Tips

- The GeoPackage can be shared with other analysts — it contains all features and metadata needed for review
- Use `--project-name` to label the pack for a specific review context
- The JSON pack is machine-readable — it can feed into automated report generation or dashboard ingestion later
