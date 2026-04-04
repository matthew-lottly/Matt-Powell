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

## Pre-commit Hooks

Install pre-commit hooks before your first commit:

```bash
pip install pre-commit
pre-commit install
```

This runs ruff linting/formatting on every commit.

## Testing Guidelines

- Run the full suite with `pytest --cov=geoprompt`.
- Maintain ≥ 70% code coverage.
- Add regression tests for any new equation or spatial operation.
- Use fixtures from `tests/conftest.py` for standard test data.
- For geometry tests, cover Point, LineString, Polygon, and Multi* types.

## Spatial Analytics Conventions

1. **Distance units**: Use kilometers for Haversine distance, raw coordinate
   units for Euclidean distance. Document the unit in docstrings.
2. **CRS**: Always specify the CRS assumption. Default is EPSG:4326.
3. **Decay parameters**: `scale` and `power` must be positive floats.
4. **Weights**: Treat missing/null weights as 0.0 unless configured otherwise.
5. **Geometry centroids**: All distance computations use centroid-to-centroid.
6. **Determinism**: All operations producing ranked results must include a
   deterministic tie-breaker (alphabetical by label).

## Pull Request Expectations

1. Keep API changes explicit and documented.
2. Add or update tests for geometry behavior, joins, overlays, or benchmarking output.
3. Refresh benchmark or comparison docs when public claims change.
4. Avoid committing generated caches or machine-specific artifacts.
5. Ensure `ruff check .` and `pyright` pass.
6. Fill in the testing checklist in the PR template.

## Issue Reports

Include the geometry type, operation, CRS assumptions, and the expected versus observed result.