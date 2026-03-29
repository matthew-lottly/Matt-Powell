# Architecture

## Overview

This project models Geoprompt as a reusable package rather than a single spatial lab.

## Flow

1. JSON feature records or GeoJSON FeatureCollections are loaded into a `GeoPromptFrame`, optionally with CRS metadata.
2. The frame normalizes point, line, and polygon geometry into a small internal geometry mapping.
3. Geometry helpers provide bounds, centroid, distance, length, area, predicate logic, coordinate transforms, and bounding-box relationship behavior.
4. Frame methods expose reusable spatial analysis primitives such as nearest neighbors, nearest joins, nearest assignment workflows, assignment summaries, map-window queries, radius queries, within-distance predicates, reprojection, spatial joins, proximity joins, buffer generation, buffer joins, coverage summaries, dissolve, clip operations, overlay intersections, interaction tables, area similarity tables, and corridor accessibility.
5. Custom GeoPrompt equations score decay, influence, corridor strength, area similarity, and pairwise interaction.
6. The demo CLI exports a JSON report, GeoJSON feature export, and a real review plot from the same package code.
7. The comparison CLI checks core Geoprompt outputs against Shapely and GeoPandas across a built-in corpus and records timing snapshots.

## Package Shape

- `geometry.py` contains normalization and mixed-geometry helper functions.
- `equations.py` contains the reusable spatial math primitives.
- `frame.py` wraps point records with geometry-aware methods, CRS state, nearest and proximity join logic, assignment summary workflows, predicate joins, service-area helpers, nearest-assignment workflows, and dissolve behavior.
- `io.py` provides lightweight package entry points for reading raw JSON records, GeoJSON FeatureCollections, and writing GeoJSON output with CRS metadata.
- `demo.py` proves the package can drive a real output artifact, not just library internals.
- `compare.py` validates metric parity and runtime against external spatial libraries over multiple fixtures.
- `overlay.py` isolates the Shapely-backed overlay adapters used for buffer, dissolve, clip, and intersection behavior, including cached Shapely loading and direct geometry conversion for the hot overlay path.

## First Deliberate Constraints

- GeoJSON-like point, line, and polygon support only
- CRS strings are supported, but full CRS objects and metadata models are not
- No pandas dependency yet
- Overlay support currently depends on Shapely and covers dissolve, clip, and pairwise intersections first
- GeoPandas and Shapely remain the reference engines for validation until Geoprompt covers more spatial operations

Those constraints are intentional. They keep the package easy to reason about while leaving room for later expansion into richer geometry and table behavior.