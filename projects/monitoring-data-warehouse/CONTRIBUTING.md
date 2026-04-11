# Contributing to monitoring-data-warehouse

## Scope

Use this repository for warehouse modeling, SQL transforms, build artifacts, and data-quality validation behavior.

## Development Setup

```bash
pip install -e .[dev]
python -m monitoring_data_warehouse.builder
pytest
```

## Pull Request Expectations

1. Keep schema and contract changes traceable in the pull request summary.
2. Update model notes, schema walkthroughs, or build artifacts when the warehouse shape changes.
3. Preserve reviewer-friendly outputs and avoid committing ephemeral local files.
4. Add or update tests when a transform, contract check, or build expectation changes.

## Issue Reports

Include the affected model, validation rule, or artifact output and describe the expected warehouse behavior.