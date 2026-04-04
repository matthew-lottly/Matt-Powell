# Contributing to spatial-data-api

## Scope

Use this repository for changes that belong to the API service itself: request and response contracts, dashboard behavior, deployment notes, and service-level validation.

## Development Setup

```bash
pip install -e .[dev]
pytest
```

## Pull Request Expectations

1. Keep changes focused on one service concern at a time.
2. Add or update tests when behavior changes.
3. Update review artifacts, runbook notes, or API examples when the public surface changes.
4. Avoid committing generated caches, local databases, or environment-specific files.

## Issue Reports

When opening a bug or feature request, include the endpoint or workflow affected, expected behavior, and any request payloads or filter combinations needed to reproduce the issue.