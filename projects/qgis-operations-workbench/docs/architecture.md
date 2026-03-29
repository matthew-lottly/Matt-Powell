# Architecture

## Overview

This project models a desktop GIS preparation flow that can feed directly into a QGIS analyst session.

## Flow

1. Sample station features are read from checked-in GeoJSON.
2. Route metadata defines review packets and export-oriented layout jobs.
3. Python functions derive summary counts, map themes, bookmarks, and review tasks.
4. A JSON workbench pack is written for review or downstream PyQGIS automation.
5. An optional GeoPackage export writes a QGIS-loadable station layer plus route metadata for desktop review.

## Why It Works Publicly

- Demonstrates desktop GIS thinking without requiring proprietary software.
- Keeps the core workflow runnable in a normal Python environment.
- Leaves a clear extension path toward PyQGIS, layout export automation, and richer GeoPackage-backed data sources.
