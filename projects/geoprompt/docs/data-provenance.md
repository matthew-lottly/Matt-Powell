# Data Provenance

This document records the origin, license, and transformation history
of all datasets distributed with geoprompt.

## Synthetic Data

All datasets in `data/` are **synthetic** — they do not represent real
geographic features, populations, or infrastructure.

### sample_points.json

- **Origin**: Hand-authored by package maintainer
- **License**: MIT (same as this package)
- **Contents**: 5 labeled point features with demand, capacity, and priority indices
- **CRS**: EPSG:4326 (WGS 84)
- **Purpose**: Unit tests, tutorial examples, demo report

### sample_features.json

- **Origin**: Auto-generated from sample_points.json with mixed geometry types
- **License**: MIT
- **Contents**: 5 features — mix of Point, LineString, and Polygon
- **CRS**: EPSG:4326
- **Purpose**: Multi-geometry tests, enrichment demos

### benchmark_regions.json

- **Origin**: Hand-authored
- **License**: MIT
- **Contents**: 2 bounding-box polygons used for spatial join tests
- **CRS**: EPSG:4326
- **Purpose**: Spatial join and overlay benchmarks

## Third-Party Data

No third-party data is distributed with this package.

If you add external data in the future:
1. Record the source URL and access date
2. Record the license
3. Note any transformations applied
4. Add an entry to this file

## Coordinate Reference Systems

All distributed data uses **EPSG:4326** (WGS 84 geographic coordinates).
Tests that involve reprojection use EPSG:3857 (Web Mercator) as a target.

## Data Integrity

JSON fixtures are validated on CI via `check-json` pre-commit hook and
by `test_io.py` round-trip tests.
