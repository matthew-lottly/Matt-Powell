# Issue Filing Tracker

Track issue filing as an operational queue, not just a yes or no list.

Status values
- `Ready`: submission exists and can be opened now.
- `Filed`: issue has been opened in the target repository.
- `Blocked`: do not open yet because the repo, labels, or scope need attention first.

Update workflow
1. Run `scripts/show-next-issue.ps1` or `scripts/show-next-batch.ps1`.
2. Open the matching issue in GitHub.
3. Run `scripts/mark-issue-filed.ps1 -Queue <nn> -IssueReference <url-or-number>`.
4. Add `-Owner` or `-Notes` when useful.

| Queue | Repository | Issue title | Priority | Status | Owner | Filed on | Issue URL or number | Submission file | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 01 | spatial-data-api | richer API examples, rollback notes, and invalid-query coverage | First 10 | Ready | | | | docs/issue-submissions/01-spatial-data-api.md | |
| 02 | environmental-monitoring-api | operational examples, startup validation, and rollback guidance | First 10 | Ready | | | | docs/issue-submissions/02-environmental-monitoring-api.md | |
| 03 | open-web-map-operations-dashboard | screenshots, accessibility checks, and browser-level flow coverage | First 10 | Ready | | | | docs/issue-submissions/03-open-web-map-operations-dashboard.md | |
| 04 | monitoring-data-warehouse | schema walkthrough artifact and stronger warehouse narrative | First 10 | Ready | | | | docs/issue-submissions/04-monitoring-data-warehouse.md | |
| 05 | qgis-operations-workbench | screenshots and analyst workflow guidance | First 10 | Ready | | | | docs/issue-submissions/05-qgis-operations-workbench.md | |
| 06 | geoprompt | CI alignment and sharper package positioning | First 10 | Ready | | | | docs/issue-submissions/06-geoprompt.md | |
| 07 | environmental-monitoring-analytics | packaging guidance and reporting-value framing | First 10 | Ready | | | | docs/issue-submissions/07-environmental-monitoring-analytics.md | |
| 08 | cross-repo maintenance | remove tracked caches and normalize README maturity framing | First 10 | Ready | | | | docs/issue-submissions/08-cross-repo-maintenance.md | Multi-repo cleanup wave. |
| 09 | causal-lens | add CI and sharpen benchmark framing | First 10 | Ready | | | | docs/issue-submissions/09-causal-lens.md | |
| 10 | experience-builder-station-brief-widget | screenshots, browser-level tests, and accessibility checks | First 10 | Ready | | | | docs/issue-submissions/10-experience-builder-station-brief-widget.md | |
| 11 | postgis-service-blueprint | rollback notes and deployment-oriented examples | Next 10 | Ready | | | | docs/issue-submissions/11-postgis-service-blueprint.md | |
| 12 | gulf-coast-inundation-lab | main-path smoke coverage and clearer evaluation artifact | Next 10 | Ready | | | | docs/issue-submissions/12-gulf-coast-inundation-lab.md | |
| 13 | monitoring-anomaly-detection | benchmark context and model-evaluation framing | Next 10 | Ready | | | | docs/issue-submissions/13-monitoring-anomaly-detection.md | |
| 14 | environmental-time-series-lab | benchmark tables and tighter evaluation framing | Next 10 | Ready | | | | docs/issue-submissions/14-environmental-time-series-lab.md | |
| 15 | arroyo-flood-forecasting-lab | benchmark summaries and tighter README outcome framing | Next 10 | Ready | | | | docs/issue-submissions/15-arroyo-flood-forecasting-lab.md | |
| 16 | raster-monitoring-pipeline | benchmark evidence and tighter evaluation narrative | Next 10 | Ready | | | | docs/issue-submissions/16-raster-monitoring-pipeline.md | |
| 17 | station-forecasting-workbench | clearer holdout metrics and stronger selection narrative | Next 10 | Ready | | | | docs/issue-submissions/17-station-forecasting-workbench.md | |
| 18 | station-risk-classification-lab | classification evaluation evidence and explainability framing | Next 10 | Ready | | | | docs/issue-submissions/18-station-risk-classification-lab.md | |
| 19 | strata | deployment guidance and public uncertainty-story framing | Next 10 | Ready | | | | docs/issue-submissions/19-strata.md | |
| 20 | tsuan | deployment assumptions and benchmark framing | Next 10 | Ready | | | | docs/issue-submissions/20-tsuan.md | |