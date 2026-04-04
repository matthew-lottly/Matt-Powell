# Contributing to qgis-operations-workbench

## Scope

Use this repository for desktop GIS packaging logic, review-bundle generation, GeoPackage export behavior, and analyst-facing workflow docs.

## Development Setup

```bash
pip install -e .[dev]
python -m qgis_operations_workbench.workbench
pytest
```

## Pull Request Expectations

1. Keep changes focused on packaging, export, or analyst workflow behavior.
2. Update example artifacts or screenshots guidance when the review bundle changes.
3. Preserve public-safe sample data and avoid local QGIS caches or machine-specific files.
4. Add tests for packaging logic or GeoPackage structure changes.

## Issue Reports

Include the command used, the expected output artifact, and whether the issue affects the JSON workbench pack, the GeoPackage export, or both.