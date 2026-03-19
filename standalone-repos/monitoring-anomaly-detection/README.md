# Monitoring Anomaly Detection

Data science portfolio project for detecting anomalous monitoring behavior, ranking sensor events, and packaging triage-ready anomaly reports.

![Monitoring anomaly detection preview](assets/anomaly-preview.svg)

## Snapshot

- Lane: Data science and anomaly detection
- Domain: Monitoring telemetry triage
- Stack: Python, CSV fixtures, statistical anomaly rules
- Includes: sample observations, anomaly ranking, station-level summaries, tests

## Overview

This project shows the operational side of data science: turning raw monitoring telemetry into anomaly candidates that an analyst or downstream alerting system can review quickly.

The current implementation stays public-safe and dependency-light. It uses checked-in observations, computes station baselines, scores deviations, and exports a ranked anomaly report without needing notebooks or external services.

## What It Demonstrates

- Repeatable anomaly scoring over environmental telemetry
- Station-level baselines and deviation analysis
- Severity ranking for operational review
- A clean handoff artifact for alerting, dashboards, or analyst queues

## Project Structure

```text
monitoring-anomaly-detection/
|-- data/
|   `-- station_observations.csv
|-- src/monitoring_anomaly_detection/
|   |-- __init__.py
|   `-- pipeline.py
|-- tests/
|   `-- test_pipeline.py
|-- assets/
|   `-- anomaly-preview.svg
|-- docs/
|   |-- architecture.md
|   `-- demo-storyboard.md
|-- outputs/
|   `-- .gitkeep
|-- pyproject.toml
`-- README.md
```

## Quick Start

```bash
pip install -e .[dev]
python -m monitoring_anomaly_detection.pipeline
```

Run tests:

```bash
pytest
```

## Current Output

The default command writes `outputs/anomaly_report.json` with:

- station baselines
- anomaly candidates ranked by deviation score
- per-station alert counts
- operational notes for triage

See [docs/architecture.md](docs/architecture.md) for the design notes.
See [docs/demo-storyboard.md](docs/demo-storyboard.md) for the reviewer walkthrough.