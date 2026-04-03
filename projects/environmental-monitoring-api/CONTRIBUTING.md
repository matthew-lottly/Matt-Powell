# Contributing to environmental-monitoring-api

## Scope

Use this repository for service behavior, dashboard integration, deployment workflow, and API-level validation changes tied to environmental monitoring operations.

## Development Setup

```bash
pip install -e .[dev]
pytest
```

## Pull Request Expectations

1. Keep API contract changes explicit in the pull request summary.
2. Update tests for startup, health, and endpoint behavior when the service surface changes.
3. Refresh the runbook or review artifacts when deployment or operator workflows change.
4. Do not commit generated caches, local-only data files, or secrets.

## Issue Reports

Include the endpoint, filter combination, or startup path involved, along with the expected result and the observed behavior.