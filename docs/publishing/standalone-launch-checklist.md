# Standalone Launch Checklist

Use this file when you are ready to publish the extracted repositories under [standalone-repos](standalone-repos).

## Publish Order

1. `environmental-monitoring-api`
2. `environmental-monitoring-analytics`
3. `monitoring-data-warehouse`

This order puts the strongest flagship repo live first, then adds analytics depth, then closes with warehouse and data-modeling depth.

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

## After All Three Are Live

1. Pin repositories in this order:
   - `environmental-monitoring-api`
   - `environmental-monitoring-analytics`
   - `monitoring-data-warehouse`
   - `Matt-Powell`
2. Set the About section for `Matt-Powell`:
   - Description: `Portfolio repository for backend, GIS, database, and analytics engineering work.`
   - Website: `https://lottly-ai.com/`
   - Topics: `portfolio`, `software-engineering`, `gis`, `geospatial`, `python`, `sql`, `data-engineering`, `backend`
3. Review your pinned repos from the perspective of someone who knows nothing about your background and check that the order reads as one coherent story.

## If A Remote Already Exists

If a standalone folder already has a configured `origin`, replace the remote before pushing:

```powershell
git remote remove origin
git remote add origin https://github.com/matthew-lottly/<repo-name>.git
```