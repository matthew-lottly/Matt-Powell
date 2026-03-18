# Environmental Monitoring Analytics

Analytics project for turning monitoring station observations into concise operational reporting.

## Overview

This project complements the Environmental Monitoring API by focusing on the analytics lane of the portfolio. It uses DuckDB to query a flat observation dataset, calculate alert-oriented metrics, and generate a markdown operations brief.

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

## Next Steps

- Add trend analysis over time windows
- Add charts or exported HTML reporting
- Connect the analytics dataset to the API project as a downstream consumer