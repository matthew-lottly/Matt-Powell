# Standalone Launch Checklist

Use this file when you are ready to publish the extracted repositories under [standalone-repos](standalone-repos).

## Publish Order

1. `environmental-monitoring-api`
2. `environmental-monitoring-analytics`
3. `monitoring-data-warehouse`
4. `experience-builder-station-brief-widget`
5. `qgis-operations-workbench`
6. `postgis-service-blueprint`
7. `open-web-map-operations-dashboard`
8. `raster-monitoring-pipeline`
9. `monitoring-anomaly-detection`
10. `environmental-time-series-lab`
11. `station-forecasting-workbench`

This order puts the strongest flagship repo live first, adds analytics depth, closes the backend/data story with warehouse modeling, adds the frontend GIS lane, broadens the public stack with a desktop QGIS workflow repo, adds an open spatial publishing repo, adds an open web map client, rounds out the GIS set with a raster analysis lane, and then adds explicit data science repos for anomaly detection, time-series analysis, and forecasting.

## Before You Start

For each repository:

1. Create a new empty GitHub repository under `matthew-lottly`.
2. Do not add a README, `.gitignore`, or license during GitHub repo creation.
3. Keep the repository public.
4. After pushing, fill in the GitHub About section using the description, website, and topics below.

Before starting the standalone repositories, push the portfolio hub using [publish-main-portfolio.md](publish-main-portfolio.md).

## Repository 1: environmental-monitoring-api

### Create On GitHub

- Name: `environmental-monitoring-api`
- Visibility: Public

### About Box

- Description: FastAPI backend for environmental monitoring with optional PostGIS, Docker support, and a browser dashboard.
- Website: `https://lottly-ai.com/`
- Topics: `fastapi`, `python`, `postgis`, `postgresql`, `gis`, `geospatial`, `docker`, `api`

### Push Commands

```powershell
Set-Location d:\GitHub\standalone-repos\environmental-monitoring-api
git init
git add .
git commit -m "Initial standalone release"
git branch -M main
git remote add origin https://github.com/matthew-lottly/environmental-monitoring-api.git
git push -u origin main
```

### After Push

1. Confirm the README renders correctly.
2. Confirm the workflow appears under Actions.
3. Pin this repo first on your GitHub profile.

## Repository 2: environmental-monitoring-analytics

### Create On GitHub

- Name: `environmental-monitoring-analytics`
- Visibility: Public

### About Box

- Description: DuckDB reporting pipeline for environmental monitoring alerts, regional metrics, and operational briefs.
- Website: `https://lottly-ai.com/`
- Topics: `duckdb`, `analytics`, `python`, `sql`, `data-engineering`, `reporting`, `geospatial`

### Push Commands

```powershell
Set-Location d:\GitHub\standalone-repos\environmental-monitoring-analytics
git init
git add .
git commit -m "Initial standalone release"
git branch -M main
git remote add origin https://github.com/matthew-lottly/environmental-monitoring-analytics.git
git push -u origin main
```

### After Push

1. Confirm the preview asset renders in the README.
2. Confirm the workflow appears under Actions.
3. Pin this repo second on your GitHub profile.

## Repository 3: monitoring-data-warehouse

### Create On GitHub

- Name: `monitoring-data-warehouse`
- Visibility: Public

### About Box

- Description: DuckDB warehouse project for dimensional modeling, SQL transforms, and monitoring data quality checks.
- Website: `https://lottly-ai.com/`
- Topics: `duckdb`, `data-warehouse`, `dimensional-modeling`, `sql`, `python`, `data-engineering`, `etl`

### Push Commands

```powershell
Set-Location d:\GitHub\standalone-repos\monitoring-data-warehouse
git init
git add .
git commit -m "Initial standalone release"
git branch -M main
git remote add origin https://github.com/matthew-lottly/monitoring-data-warehouse.git
git push -u origin main
```

### After Push

1. Confirm the README renders the warehouse preview correctly.
2. Confirm the workflow appears under Actions.
3. Pin this repo third on your GitHub profile.

## Repository 4: experience-builder-station-brief-widget

### Create On GitHub

- Name: `experience-builder-station-brief-widget`
- Visibility: Public

### About Box

- Description: React and TypeScript GIS widget prototype inspired by ArcGIS Experience Builder patterns for filtering, summaries, and station detail interaction.
- Website: `https://lottly-ai.com/`
- Topics: `react`, `typescript`, `arcgis`, `experience-builder`, `gis`, `frontend`, `geospatial`

### Push Commands

```powershell
Set-Location d:\GitHub\standalone-repos\experience-builder-station-brief-widget
git init
git add .
git commit -m "Initial standalone release"
git branch -M main
git remote add origin https://github.com/matthew-lottly/experience-builder-station-brief-widget.git
git push -u origin main
```

### After Push

1. Confirm the preview asset renders in the README.
2. Confirm the workflow appears under Actions.
3. Pin this repo fourth on your GitHub profile.

## Repository 5: qgis-operations-workbench

### Create On GitHub

- Name: `qgis-operations-workbench`
- Visibility: Public

### About Box

- Description: QGIS-oriented Python project for packaging desktop GIS review workflows, bookmarks, and route-based layout jobs.
- Website: `https://lottly-ai.com/`
- Topics: `qgis`, `pyqgis`, `python`, `gdal`, `geopackage`, `gis`, `geospatial`

### Push Commands

```powershell
Set-Location d:\GitHub\standalone-repos\qgis-operations-workbench
git init
git add .
git commit -m "Initial standalone release"
git branch -M main
git remote add origin https://github.com/matthew-lottly/qgis-operations-workbench.git
git push -u origin main
```

### After Push

1. Confirm the preview asset renders in the README.
2. Confirm the workflow appears under Actions.
3. Pin this repo after the widget or swap it into the top five once you want the desktop GIS lane visible.

## Repository 6: postgis-service-blueprint

### Create On GitHub

- Name: `postgis-service-blueprint`
- Visibility: Public

### About Box

- Description: Open spatial service blueprint for publishing PostGIS-backed layers with collection metadata and query patterns.
- Website: `https://lottly-ai.com/`
- Topics: `postgis`, `postgresql`, `sql`, `python`, `ogc-api-features`, `gis`, `geospatial`

### Push Commands

```powershell
Set-Location d:\GitHub\standalone-repos\postgis-service-blueprint
git init
git add .
git commit -m "Initial standalone release"
git branch -M main
git remote add origin https://github.com/matthew-lottly/postgis-service-blueprint.git
git push -u origin main
```

### After Push

1. Confirm the preview asset renders in the README.
2. Confirm the workflow appears under Actions.
3. Pin it when you want the open spatial publishing lane visible on the profile.

## Repository 7: open-web-map-operations-dashboard

### Create On GitHub

- Name: `open-web-map-operations-dashboard`
- Visibility: Public

### About Box

- Description: React and TypeScript open web map dashboard for operational layer review, map filtering, and feature inspection patterns.
- Website: `https://lottly-ai.com/`
- Topics: `react`, `typescript`, `maplibre`, `openlayers`, `gis`, `geospatial`, `frontend`

### Push Commands

```powershell
Set-Location d:\GitHub\standalone-repos\open-web-map-operations-dashboard
git init
git add .
git commit -m "Initial standalone release"
git branch -M main
git remote add origin https://github.com/matthew-lottly/open-web-map-operations-dashboard.git
git push -u origin main
```

### After Push

1. Confirm the preview asset renders in the README.
2. Confirm the workflow appears under Actions.
3. Pin it when you want the open web mapping lane visible on the profile.

## Repository 8: raster-monitoring-pipeline

### Create On GitHub

- Name: `raster-monitoring-pipeline`
- Visibility: Public

### About Box

- Description: Python raster change-detection pipeline for hotspot review, tile planning, and monitoring summaries.
- Website: `https://lottly-ai.com/`
- Topics: `rasterio`, `gdal`, `python`, `remote-sensing`, `gis`, `geospatial`, `analytics`

### Push Commands

```powershell
Set-Location d:\GitHub\standalone-repos\raster-monitoring-pipeline
git init
git add .
git commit -m "Initial standalone release"
git branch -M main
git remote add origin https://github.com/matthew-lottly/raster-monitoring-pipeline.git
git push -u origin main
```

### After Push

1. Confirm the preview asset renders in the README.
2. Confirm the workflow appears under Actions.
3. Swap it into the pinned set when you want the raster analysis lane visible on the profile.

## Repository 9: monitoring-anomaly-detection

### Create On GitHub

- Name: `monitoring-anomaly-detection`
- Visibility: Public

### About Box

- Description: Python anomaly-detection pipeline for monitoring telemetry, sensor drift, and alert triage.
- Website: `https://lottly-ai.com/`
- Topics: `python`, `data-science`, `anomaly-detection`, `time-series`, `analytics`, `gis`, `monitoring`

### Push Commands

```powershell
Set-Location d:\GitHub\standalone-repos\monitoring-anomaly-detection
git init
git add .
git commit -m "Initial standalone release"
git branch -M main
git remote add origin https://github.com/matthew-lottly/monitoring-anomaly-detection.git
git push -u origin main
```

## Repository 10: environmental-time-series-lab

### Create On GitHub

- Name: `environmental-time-series-lab`
- Visibility: Public

### About Box

- Description: Python time-series analysis lab for trend profiling, rolling summaries, and monitoring signal review.
- Website: `https://lottly-ai.com/`
- Topics: `python`, `data-science`, `time-series`, `analytics`, `trend-analysis`, `monitoring`, `gis`

### Push Commands

```powershell
Set-Location d:\GitHub\standalone-repos\environmental-time-series-lab
git init
git add .
git commit -m "Initial standalone release"
git branch -M main
git remote add origin https://github.com/matthew-lottly/environmental-time-series-lab.git
git push -u origin main
```

## Repository 11: station-forecasting-workbench

### Create On GitHub

- Name: `station-forecasting-workbench`
- Visibility: Public

### About Box

- Description: Python forecasting workbench for station demand baselines, holdout evaluation, and next-step projections.
- Website: `https://lottly-ai.com/`
- Topics: `python`, `data-science`, `forecasting`, `time-series`, `analytics`, `monitoring`, `gis`

### Push Commands

```powershell
Set-Location d:\GitHub\standalone-repos\station-forecasting-workbench
git init
git add .
git commit -m "Initial standalone release"
git branch -M main
git remote add origin https://github.com/matthew-lottly/station-forecasting-workbench.git
git push -u origin main
```

## After All Eleven Are Live

1. Pin repositories in this order:
   - `environmental-monitoring-api`
   - `environmental-monitoring-analytics`
   - `monitoring-data-warehouse`
   - `qgis-operations-workbench`
   - `postgis-service-blueprint`
   - `open-web-map-operations-dashboard`
2. Use `experience-builder-station-brief-widget` as a swap-in when you want the Esri-adjacent frontend lane visible.
3. Use `Matt-Powell` as a swap-in when you want the umbrella portfolio repo visible.
4. Set the About section for `Matt-Powell`:
   - Description: `Portfolio repository for backend, GIS, frontend, database, and analytics engineering work.`
   - Website: `https://lottly-ai.com/`
   - Topics: `portfolio`, `software-engineering`, `gis`, `geospatial`, `frontend`, `python`, `sql`, `data-engineering`, `backend`
5. Review your pinned repos from the perspective of someone who knows nothing about your background and check that the order reads as one coherent story.
6. Use [github-profile-finish-checklist.md](github-profile-finish-checklist.md) to apply the final About box values and run the last GitHub smoke check.

## If A Remote Already Exists

If a standalone folder already has a configured `origin`, replace the remote before pushing:

```powershell
git remote remove origin
git remote add origin https://github.com/matthew-lottly/<repo-name>.git
```