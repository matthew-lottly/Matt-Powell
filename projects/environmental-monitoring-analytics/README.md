# Environmental Monitoring Analytics

Analytics project for turning monitoring station observations into concise operational reporting and shareable HTML summaries.

![Report preview](assets/report-preview.svg)

![HTML report screenshot](assets/report-live-screenshot.png)

## Overview

This project complements the Environmental Monitoring API by focusing on the analytics lane of the portfolio. It uses DuckDB to query a flat observation dataset, calculate alert-oriented metrics, and generate both a markdown operations brief and an HTML summary with visual regional alert bars.

It is intentionally small and fast to run so a reviewer can move from raw data to a presentable operations brief in a few minutes.

## What It Demonstrates

- SQL-first analytics with DuckDB
- Repeatable reporting from raw observation data
- Operational metrics for alert rates and regional coverage
- A second portfolio lane that emphasizes analysis instead of API design

## Dataset

The sample dataset models station observations with:

- station identifiers and names
- monitoring categories
- regions
- observation timestamps
- status values
- alert scores
- reading values

## Project Structure

```text
projects/environmental-monitoring-analytics/
|-- data/
|-- src/environmental_monitoring_analytics/
|   |-- __init__.py
|   `-- reporting.py
|-- tests/
|   `-- test_reporting.py
|-- pyproject.toml
`-- README.md
```

## Quick Start

```bash
pip install -e .[dev]
python -m environmental_monitoring_analytics.reporting
```

## Current Outputs

- Total observation count
- Alert rate
- Average alert score
- Regional alert breakdown
- Latest alert stations section in markdown
- Exportable HTML brief with visual summary blocks and regional alert bars

See [docs/sample-operations-brief.md](docs/sample-operations-brief.md) for a sample generated brief.
See [docs/sample-operations-brief.html](docs/sample-operations-brief.html) for a sample generated HTML brief.
See [docs/architecture.md](docs/architecture.md) for the reporting flow overview.

## Next Steps

- Add trend analysis over time windows
- Connect the analytics dataset to the API project as a downstream consumer

## Publication

See [PUBLISHING.md](PUBLISHING.md) for the standalone repository plan.