# Packaging Guide

Notes on distributing the environmental monitoring analytics package.

## Installation

```bash
pip install -e .[dev]
```

The only runtime dependency is `duckdb`. The `[dev]` extra adds `pytest`.

## Building a Distribution

```bash
python -m pip install --upgrade build twine
python -m build
python -m twine check dist/*
```

This produces `dist/environmental_monitoring_analytics-0.1.0.tar.gz` and a wheel.

## Running Reports

Generate the default markdown and HTML operations brief:

```bash
python -m environmental_monitoring_analytics.reporting
```

Generate from an API-derived snapshot bundle:

```bash
python -m environmental_monitoring_analytics.reporting --input data/api_observation_snapshot.json
```

Generate a date-windowed comparison:

```bash
python -m environmental_monitoring_analytics.reporting --start-date 2026-03-18 --end-date 2026-03-18
```

## Output Artifacts

The reporting module produces:
- A markdown operations brief (printed to stdout)
- An HTML summary brief in `docs/sample-operations-brief.html`
- Date-window trend comparisons when `--start-date` and `--end-date` are provided

## Data Contract

The CSV sample uses these columns:
- `station_id`, `station_name`, `category`, `region`, `observed_at`, `status`, `alert_score`, `reading_value`

The JSON snapshot input follows the contract documented in `docs/api-snapshot-contract.md`.

## Version Pinning

For dependent projects:

```
environmental-monitoring-analytics==0.1.0
```

## CI Notes

The CI workflow in `.github/workflows/ci.yml` runs `pytest` and verifies the reporting module produces valid output.
