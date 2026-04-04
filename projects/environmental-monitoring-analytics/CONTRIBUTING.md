# Contributing to environmental-monitoring-analytics

## Scope

Use this repository for reporting logic, analytics output, DuckDB transformations, and review-oriented export behavior.

## Development Setup

```bash
pip install -e .[dev]
pytest
```

## Pull Request Expectations

1. Keep report logic and output-shape changes explicit.
2. Update tests or example outputs when report content changes.
3. Preserve reviewer-friendly artifacts and avoid committing local caches or transient files.
4. Refresh packaging or methodology docs when the analytics story changes.

## Issue Reports

Include the report mode, input snapshot or dataset, and the expected versus observed output.