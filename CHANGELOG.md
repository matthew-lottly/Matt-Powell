# Changelog

## 2026-04-02 (todo-100 execution pass)

### Added
- API request/response examples for spatial-data-api and environmental-monitoring-api.
- Rollback guides for spatial-data-api, environmental-monitoring-api, and postgis-service-blueprint.
- Invalid-query and edge-case validation tests for spatial-data-api.
- Startup and health-check validation tests for environmental-monitoring-api.
- Schema walkthrough artifact for monitoring-data-warehouse.
- Analyst workflow guide for qgis-operations-workbench.
- Packaging guides for qgis-operations-workbench and environmental-monitoring-analytics.
- Screenshot guides for qgis-operations-workbench and open-web-map-operations-dashboard.
- Accessibility checklist for open-web-map-operations-dashboard and experience-builder-station-brief-widget.
- CI workflow for causal-lens.
- Deployment guide for strata.
- Deployment assumptions doc for tsuan.
- Benchmark and evaluation docs for arroyo-flood-forecasting-lab, environmental-time-series-lab, monitoring-anomaly-detection, raster-monitoring-pipeline, station-forecasting-workbench, station-risk-classification-lab, and gulf-coast-inundation-lab.
- Deployment examples for postgis-service-blueprint.
- Ruff formatting baselines in pyproject.toml for 15 Python projects.
- Publication and Repository Notes sections to 4 READMEs that were missing them.
- 100-item portfolio backlog in docs/todo-100.md.
- Issue submission pack, filing tracker, batch helper, mark-filed helper, and VS Code tasks.

### Changed
- Updated portfolio matrix Next Move column to reflect completed improvements.
- Tightened monitoring-data-warehouse README (fixed duplicate Includes line, added schema walkthrough link).
- Linked new docs from spatial-data-api, environmental-monitoring-api, qgis-operations-workbench, and open-web-map-operations-dashboard READMEs.

### Removed
- 295 tracked __pycache__, .pyc, and .pytest_cache files from git index.

## 2026-04-02

### Added
- Portfolio-wide review artifacts for the tracked local project set.
- Per-project data-flow documentation.
- Service runbooks for the operational project set.
- Smoke and OpenAPI-style tests across the active projects.
- Portfolio operating docs including roadmap, matrix, contributor onboarding, and scoped todo lists.
- Issue templates, pull request template, and code ownership baseline for the portfolio hub.

### Changed
- Replaced the stale sports-sim-oriented backlog with a portfolio-hub execution plan.
- Marked the current showcase-priority project set.

### Removed
- Old sports-sim content and stale references from the branch history leading into this planning pass.