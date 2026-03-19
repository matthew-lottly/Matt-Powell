# Next GIS Repo Sequence

This plan keeps the existing Esri-oriented portfolio work in place while making the next repo wave visibly broader.

## Goals

- Keep the current Experience Builder-inspired widget as a public-safe frontend prototype.
- Add stronger proof of desktop GIS depth outside Esri.
- Show open geospatial tooling across data preparation, services, mapping, and analysis.
- Build a sequence that reads as one coherent GIS engineering portfolio rather than unrelated demos.

## Recommended Order

### 1. QGIS Operations Workbench

Purpose: demonstrate desktop GIS strength with repeatable analyst workflows.

- Stack: QGIS, PyQGIS, Python, GeoPackage, GDAL
- Deliverables: processing scripts, layout export automation, project packaging, and reviewable sample data
- Why first: it reinforces workstation-grade GIS fundamentals and broadens the portfolio immediately beyond Esri
- Status: started in the portfolio and published as a standalone repo

### 2. PostGIS Service and Data Publishing Repo

Purpose: show how cleaned spatial data becomes reusable services.

- Stack: PostgreSQL, PostGIS, FastAPI or PostgREST, Docker
- Deliverables: service-ready schemas, API endpoints or SQL-first service exposure, seed data, and spatial QA checks
- Why second: it extends the existing backend lane while moving into a more open spatial platform story
- Status: started in the portfolio and published as `postgis-service-blueprint`

### 3. Open Web Map Client

Purpose: replace vendor-specific UI framing with a clearly owned frontend mapping implementation.

- Stack: MapLibre GL JS or OpenLayers, TypeScript, Vite, vector tiles or GeoJSON
- Deliverables: interactive web map, layer toggles, feature inspection, filtering, and operational overlays
- Why third: it gives the portfolio a real open-stack web map surface to pair with the API and service repos
- Status: started in the portfolio and published as `open-web-map-operations-dashboard`

### 4. Raster and Remote Sensing Pipeline

Purpose: show analytical depth beyond vector workflows.

- Stack: GDAL, rasterio, xarray, Python, DuckDB or parquet outputs
- Deliverables: tiling or clipping workflows, derived raster metrics, change summaries, and publishable preview assets
- Why fourth: it rounds out the portfolio with a strong analysis lane that is distinct from backend and frontend work
- Status: started in the portfolio as `raster-monitoring-pipeline`

## Suggested Naming Direction

- `qgis-operations-workbench`
- `postgis-service-blueprint`
- `open-web-map-operations-dashboard`
- `raster-monitoring-pipeline`

## Portfolio Positioning

Use the current widget repo as an Experience Builder-inspired concept project.

Use the next repo wave to say:

- desktop GIS fundamentals: QGIS and automation
- spatial backend and services: PostGIS-first delivery
- frontend mapping: MapLibre or OpenLayers
- analysis depth: raster and monitoring pipelines

That combination preserves the Esri-relevant work already present, but makes the broader GIS toolchain unmistakable.