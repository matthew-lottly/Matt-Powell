# Standalone Repo Issue Checklists

Use these as issue-ready checklists in the matching standalone repositories.

## spatial-data-api

- [ ] Add sample request and response examples to the review artifacts.
- [ ] Add rollback guidance to the runbook.
- [ ] Add failure-path coverage for invalid spatial query parameters.

## environmental-monitoring-api

- [ ] Add richer API payload examples and expected operational scenarios.
- [ ] Add health-check and startup-failure tests.
- [ ] Add rollback notes to the runbook.

## monitoring-data-warehouse

- [ ] Add a schema walkthrough artifact that explains the core marts.
- [ ] Add a clearer warehouse architecture summary in the README.
- [ ] Audit tracked generated artifacts and remove any that should not live in git.

## qgis-operations-workbench

- [ ] Add screenshots of the packaged review workspace.
- [ ] Add a short analyst workflow note to the README.
- [ ] Review packaging guidance for public clarity.

## open-web-map-operations-dashboard

- [ ] Add screenshots or a short GIF for visual review.
- [ ] Expand smoke coverage into browser-level flows.
- [ ] Add accessibility checks and fixes.

## geoprompt

- [ ] Add or align project CI with the current package expectations.
- [ ] Strengthen README positioning around outcomes and reusable spatial workflows.
- [ ] Audit dependency sprawl and packaging metadata.

## environmental-monitoring-analytics

- [ ] Add stronger packaging and reproducibility guidance.
- [ ] Add a clearer explanation of report value and intended audience.
- [ ] Review dependency looseness in `pyproject.toml`.

## arroyo-flood-forecasting-lab

- [ ] Add benchmark summary tables to complement the example output.
- [ ] Tighten README outcome framing.

## causal-lens

- [ ] Add CI in the standalone repo.
- [ ] Tighten public framing around benchmark outcomes and diagnostics.

## environmental-time-series-lab

- [ ] Add benchmark tables or leaderboard summaries.
- [ ] Tighten README claims around evaluation and intended use.

## experience-builder-station-brief-widget

- [ ] Add screenshots or a short GIF.
- [ ] Add browser-level tests beyond the current render smoke.
- [ ] Add accessibility checks.

## gulf-coast-inundation-lab

- [ ] Add smoke coverage for the main evaluation path.
- [ ] Improve the evaluation artifact so the validation signal is clearer.

## monitoring-anomaly-detection

- [ ] Add benchmark context for detector comparison.
- [ ] Improve model-evaluation framing in the README.

## postgis-service-blueprint

- [ ] Add rollback guidance to the runbook.
- [ ] Add deployment-oriented examples for promotion into a live service.

## raster-monitoring-pipeline

- [ ] Add benchmark evidence or performance notes.
- [ ] Tighten pipeline evaluation framing in the README.

## station-forecasting-workbench

- [ ] Add clearer holdout metrics in the review narrative.
- [ ] Tighten summary framing around model-selection value.

## station-risk-classification-lab

- [ ] Add confusion-matrix or classification-evaluation evidence.
- [ ] Tighten explainability framing in the README.

## strata

- [ ] Tighten deployment guidance and API assumptions.
- [ ] Strengthen public positioning for the uncertainty and calibration story.

## tsuan

- [ ] Tighten deployment assumptions and export guidance.
- [ ] Add stronger benchmark framing for reconstruction and uncertainty quality.

## Cross-Repo Maintenance

- [ ] Remove tracked cache artifacts where they still exist.
- [ ] Standardize README ordering and maturity positioning.
- [ ] Audit dependency sprawl and Python version support.