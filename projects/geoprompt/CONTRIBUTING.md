# Contributing to Geoprompt

## Scope

Use this repository for package API behavior, spatial operations, benchmark comparisons, and reviewer-facing package documentation.

## Development Setup

```bash
pip install -e .[dev]
pytest
```

Run the comparison workflow when changes affect core spatial behavior:

```bash
pip install -e .[compare]
python -m geoprompt.compare
```

## Pull Request Expectations

1. Keep API changes explicit and documented.
2. Add or update tests for geometry behavior, joins, overlays, or benchmarking output.
3. Refresh benchmark or comparison docs when public claims change.
4. Avoid committing generated caches or machine-specific artifacts.

## Issue Reports

Include the geometry type, operation, CRS assumptions, and the expected versus observed result.