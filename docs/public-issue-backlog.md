# Public Issue Backlog

This file tracks the initial public issue backlog created across the standalone repositories.

## Recommended Delivery Order

1. environmental-monitoring-api
2. environmental-monitoring-analytics
3. experience-builder-station-brief-widget
4. monitoring-data-warehouse

This order keeps the flagship backend moving first, then strengthens the analytics story, then improves the frontend demo depth, and finally expands warehouse sophistication.

## environmental-monitoring-api

Completed recently:

- [#1 Highlight recent alert observations and status changes in the dashboard](https://github.com/matthew-lottly/environmental-monitoring-api/issues/1)
- [#2 Publish a container image from CI](https://github.com/matthew-lottly/environmental-monitoring-api/issues/2)

## environmental-monitoring-analytics

Completed recently:

- [#1 Add time-window trend analysis to the operations brief](https://github.com/matthew-lottly/environmental-monitoring-analytics/issues/1)
- [#2 Support API-derived input snapshots for reporting](https://github.com/matthew-lottly/environmental-monitoring-analytics/issues/2)

## monitoring-data-warehouse

Completed recently:

- [#1 Add a slowly changing dimension example for station attributes](https://github.com/matthew-lottly/monitoring-data-warehouse/issues/1)
- [#2 Document PostgreSQL partitioning and retention strategy for migration](https://github.com/matthew-lottly/monitoring-data-warehouse/issues/2)

## experience-builder-station-brief-widget

Completed recently:

- [#1 Persist mock widget configuration across reloads](https://github.com/matthew-lottly/experience-builder-station-brief-widget/issues/1)
- [#2 Add an interaction walkthrough asset for the widget demo](https://github.com/matthew-lottly/experience-builder-station-brief-widget/issues/2)

## Current State

- Repository About metadata is set for all five public repositories.
- The standalone repositories now each have an initial issue backlog.
- The API lane now ships filtered observation rollup summaries in the observation endpoints, a dashboard that highlights recent alert readings and recent status changes, and a CI workflow that publishes a public container image. Issues `environmental-monitoring-api#1` and `environmental-monitoring-api#2` are closed.
- The analytics lane now ships rolling recent-vs-previous window trend analysis and API-derived snapshot input support, and issues `environmental-monitoring-analytics#1` and `environmental-monitoring-analytics#2` are closed.
- The widget lane now persists mock configuration across reloads and includes an interaction walkthrough asset, and issues `experience-builder-station-brief-widget#1` and `experience-builder-station-brief-widget#2` are closed.
- The warehouse lane now includes a Type 2 station-attribute history example plus concrete PostgreSQL migration notes, and issues `monitoring-data-warehouse#1` and `monitoring-data-warehouse#2` are closed.
- GitHub profile pinning still needs to be set manually in the GitHub UI.