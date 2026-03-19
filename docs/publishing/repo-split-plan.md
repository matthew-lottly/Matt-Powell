# Repo Split Plan

Use this when you are ready to move project folders into their own public repositories.

## Recommended Split Order

1. `environmental-monitoring-api`
2. `environmental-monitoring-analytics`
3. `monitoring-data-warehouse`
4. `experience-builder-station-brief-widget`
5. `qgis-operations-workbench`
6. `postgis-service-blueprint`
7. `open-web-map-operations-dashboard`
8. `raster-monitoring-pipeline`

## Why This Order

- The API project is the strongest flagship repo and should anchor your pinned set first.
- The analytics project is lightweight and fast to publish once the API repo is visible.
- The warehouse project rounds out the portfolio by showing database-engineering depth.
- The widget project closes the loop by showing the frontend GIS interaction layer that complements the backend and data work.
- The QGIS workbench extends the portfolio into desktop GIS and open-stack analyst workflows.
- The PostGIS service blueprint adds a distinct open spatial publishing lane between raw GIS data and delivery endpoints.
- The open web map dashboard adds the open-stack frontend consumer for those spatial services.
- The raster monitoring pipeline rounds out the portfolio with a public-safe raster analysis lane.

## Proposed Repo Names

- `environmental-monitoring-api`
- `environmental-monitoring-analytics`
- `monitoring-data-warehouse`
- `experience-builder-station-brief-widget`
- `qgis-operations-workbench`
- `postgis-service-blueprint`
- `open-web-map-operations-dashboard`
- `raster-monitoring-pipeline`

## Shared Publication Checklist

- Move the project folder contents to the new repository root
- Keep the README concise and role-oriented
- Add one preview asset or screenshot near the top
- Add About description and topics on GitHub
- Verify the setup instructions from a clean checkout
- Enable the repo-specific workflow if CI is present

## Helper Scripts

- [extract-environmental-monitoring-api.ps1](extract-environmental-monitoring-api.ps1)
- [extract-environmental-monitoring-analytics.ps1](extract-environmental-monitoring-analytics.ps1)
- [extract-monitoring-data-warehouse.ps1](extract-monitoring-data-warehouse.ps1)
- [extract-experience-builder-station-brief-widget.ps1](extract-experience-builder-station-brief-widget.ps1)
- [extract-all-projects.ps1](extract-all-projects.ps1)

## Publish Command Guides

- [commands/publish-environmental-monitoring-api.md](commands/publish-environmental-monitoring-api.md)
- [commands/publish-environmental-monitoring-analytics.md](commands/publish-environmental-monitoring-analytics.md)
- [commands/publish-monitoring-data-warehouse.md](commands/publish-monitoring-data-warehouse.md)
- [commands/publish-experience-builder-station-brief-widget.md](commands/publish-experience-builder-station-brief-widget.md)

## Launch Checklist

- [standalone-launch-checklist.md](standalone-launch-checklist.md)
- [publish-main-portfolio.md](publish-main-portfolio.md)