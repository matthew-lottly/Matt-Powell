# Public Issue Backlog

This file tracks the initial public issue backlog created across the standalone repositories.

## Recommended Delivery Order

No open public backlog items remain from the current issue wave.

This order keeps the flagship backend moving first, then deepens the analytics story, then adds richer widget interactions, and finally expands warehouse engineering discipline.

## environmental-monitoring-api

Completed recently:

- [#1 Highlight recent alert observations and status changes in the dashboard](https://github.com/matthew-lottly/environmental-monitoring-api/issues/1)
- [#2 Publish a container image from CI](https://github.com/matthew-lottly/environmental-monitoring-api/issues/2)
- [#5 Add station threshold configuration and derived alert logic](https://github.com/matthew-lottly/environmental-monitoring-api/issues/5)
- [#6 Add an operations summary endpoint](https://github.com/matthew-lottly/environmental-monitoring-api/issues/6)

## environmental-monitoring-analytics

Completed recently:

- [#1 Add time-window trend analysis to the operations brief](https://github.com/matthew-lottly/environmental-monitoring-analytics/issues/1)
- [#2 Support API-derived input snapshots for reporting](https://github.com/matthew-lottly/environmental-monitoring-analytics/issues/2)
- [#5 Add parameterized report windows for custom comparisons](https://github.com/matthew-lottly/environmental-monitoring-analytics/issues/5)
- [#6 Add category deep-dive insights to HTML exports](https://github.com/matthew-lottly/environmental-monitoring-analytics/issues/6)

## monitoring-data-warehouse

Completed recently:

- [#1 Add a slowly changing dimension example for station attributes](https://github.com/matthew-lottly/monitoring-data-warehouse/issues/1)
- [#2 Document PostgreSQL partitioning and retention strategy for migration](https://github.com/matthew-lottly/monitoring-data-warehouse/issues/2)
- [#5 Add dbt-style dependency metadata and model docs](https://github.com/matthew-lottly/monitoring-data-warehouse/issues/5)
- [#6 Add data contract checks for warehouse quality gates](https://github.com/matthew-lottly/monitoring-data-warehouse/issues/6)

## experience-builder-station-brief-widget

Completed recently:

- [#1 Persist mock widget configuration across reloads](https://github.com/matthew-lottly/experience-builder-station-brief-widget/issues/1)
- [#2 Add an interaction walkthrough asset for the widget demo](https://github.com/matthew-lottly/experience-builder-station-brief-widget/issues/2)
- [#5 Add a station detail modal with observation history](https://github.com/matthew-lottly/experience-builder-station-brief-widget/issues/5)
- [#6 Add a multi-select status filter to the widget](https://github.com/matthew-lottly/experience-builder-station-brief-widget/issues/6)

## Current State

- Repository About metadata is set for all five public repositories.
- The standalone repositories now each have an initial issue backlog.
- The API lane now ships filtered observation rollup summaries in the observation endpoints, a dashboard that highlights recent alert readings and recent status changes, threshold-driven derived alert logic, an operations summary endpoint, and a CI workflow that publishes a public container image. Issues `environmental-monitoring-api#1`, `environmental-monitoring-api#2`, `environmental-monitoring-api#5`, and `environmental-monitoring-api#6` are closed.
- The analytics lane now ships rolling recent-vs-previous window trend analysis, parameterized date-window comparisons, category-level deep dives in markdown and HTML output, and API-derived snapshot input support. Issues `environmental-monitoring-analytics#1`, `environmental-monitoring-analytics#2`, `environmental-monitoring-analytics#5`, and `environmental-monitoring-analytics#6` are closed.
- The widget lane now persists mock configuration across reloads, includes an interaction walkthrough asset, supports persistent multi-select status filters, and ships a station observation history modal. Issues `experience-builder-station-brief-widget#1`, `experience-builder-station-brief-widget#2`, `experience-builder-station-brief-widget#5`, and `experience-builder-station-brief-widget#6` are closed.
- The warehouse lane now includes a Type 2 station-attribute history example, concrete PostgreSQL migration notes, dbt-style model metadata, and manifest-driven contract checks. Issues `monitoring-data-warehouse#1`, `monitoring-data-warehouse#2`, `monitoring-data-warehouse#5`, and `monitoring-data-warehouse#6` are closed.
- The second backlog wave is complete across all four standalone repos.
- GitHub profile pinning still needs to be set manually in the GitHub UI.