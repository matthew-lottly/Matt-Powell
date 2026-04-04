# Packaging Guide

Notes for packaging and distributing the QGIS Operations Workbench.

## Installation

The workbench installs as a standard Python package:

```bash
pip install -e .[dev]
```

It does not require QGIS to be installed. The builder generates output artifacts (JSON pack, GeoPackage) that can be opened in QGIS afterward.

## Dependencies

The core workbench has minimal dependencies. The `[dev]` extras include:
- `pytest` for test execution
- `fiona` and `geopandas` for GeoPackage export (optional)

If GeoPackage export is not needed, the core package runs with no external dependencies beyond the Python standard library.

## Distribution

For standalone repository publishing:

1. Verify the `pyproject.toml` metadata is current (name, version, description, license)
2. Build the distribution:

```bash
python -m build
```

3. Validate the package:

```bash
python -m twine check dist/*
```

4. The package is not currently published to PyPI. It is distributed as a source repository.

## GeoPackage Output

The `--export-geopackage` flag requires `fiona` or `geopandas`. If neither is installed, the builder falls back to JSON-only output with a warning.

To install GeoPackage support:

```bash
pip install -e .[dev]
```

## QGIS Plugin Path

The current workbench is a standalone Python package, not a QGIS plugin. The path to QGIS plugin integration:

1. The JSON pack format is designed to be consumable by a future PyQGIS automation script
2. The GeoPackage output opens directly in QGIS via drag-and-drop
3. A future PyQGIS wrapper could read the JSON pack and auto-configure layers, themes, and bookmarks

## Version Pinning

For reproducible builds, pin the workbench version in dependent environments:

```
qgis-operations-workbench==0.1.0
```

## CI Notes

The CI workflow in `.github/workflows/ci.yml` runs `pytest` and verifies the builder produces valid output artifacts.
