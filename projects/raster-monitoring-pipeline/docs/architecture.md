# Architecture

## Overview

This project models a raster monitoring workflow that compares two snapshots and exports a structured change report.

## Flow

1. Baseline and latest raster grids are loaded from checked-in fixtures.
2. Cell deltas are calculated across the full grid.
3. High-change cells are flagged as hotspots.
4. A tile manifest and summary report are exported for downstream use.

## Why It Works Publicly

- Demonstrates raster analysis thinking without requiring proprietary data.
- Keeps the core workflow runnable in a normal Python environment.
- Leaves a clear extension path toward rasterio, GDAL, xarray, and larger tiling pipelines.
