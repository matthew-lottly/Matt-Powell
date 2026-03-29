# Demo Storyboard

Reference asset: `assets/workbench-preview.svg`

## 1. Frame the use case

Show the project as the preparation step before a desktop GIS analyst opens QGIS for the day.

## 2. Explain the data inputs

Point out that the repository includes a checked-in station point layer and route definitions that drive the review pack.

## 3. Run the workbench builder

Generate `outputs/qgis_workbench_pack.json` and show the summary, bookmarks, themes, and layout jobs.

Then rerun with `--export-geopackage` and show that the repo also produces a QGIS-loadable `outputs/qgis_review_bundle.gpkg` file for the same review session.

## 4. Highlight analyst value

Walk through how the review tasks help an analyst prioritize alert stations, offline devices, and route-specific map exports.

## 5. Explain the roadmap

Close by noting that this scaffold is ready for future PyQGIS and GDAL automation without changing the public-safe project shape.
