# Architecture

## Overview

This project models Geoprompt as a reusable package rather than a single spatial lab.

## Flow

1. JSON feature records or GeoJSON FeatureCollections are loaded into a `GeoPromptFrame`, optionally with CRS metadata.
2. The frame normalizes point, line, and polygon geometry into a small internal geometry mapping.
3. Geometry helpers provide bounds, centroid, distance, length, area, predicate logic, coordinate transforms, and bounding-box relationship behavior.
4. Frame methods expose reusable spatial analysis primitives such as nearest neighbors, nearest joins, nearest assignment workflows, assignment summaries, catchment competition summaries, corridor reach in Euclidean or haversine mode with direct or network-style scoring, configurable zone fit scoring with grouped rankings, centroid clustering with quality metrics and cluster-count diagnostics, map-window queries, radius queries, within-distance predicates, reprojection, spatial joins, proximity joins, buffer generation, buffer joins, coverage summaries, grouped overlay summaries, dissolve, clip operations, overlay intersections, interaction tables, gravity tables, accessibility scores, area similarity tables, corridor accessibility, frame utilities, envelope and convex hull transforms.
5. Custom GeoPrompt equations score decay, influence, corridor strength, area similarity, gravity model, accessibility index, and pairwise interaction.
6. The demo CLI exports a JSON report, GeoJSON feature export, and a real review plot from the same package code.
7. The comparison CLI checks core Geoprompt outputs against Shapely and GeoPandas across a built-in corpus and records timing snapshots.

## Package Shape

- `geometry.py` contains normalization, mixed-geometry helper functions, convex hull, and envelope operations.
- `equations.py` contains the reusable spatial math primitives including gravity model and accessibility index.
- `frame.py` wraps point records with geometry-aware methods, CRS state, nearest and proximity join logic, assignment, catchment, corridor reach with scoring and network-style distance, configurable zone fit scoring and grouped rankings, centroid clustering with quality metrics and cluster-count diagnostics, overlay summary workflows with grouped outputs, predicate joins, service-area helpers, nearest-assignment workflows, gravity and accessibility scoring, frame utilities, and dissolve behavior.
- `io.py` provides lightweight package entry points for reading raw JSON records, GeoJSON FeatureCollections (from file or dict), writing GeoJSON output with CRS metadata, and flat record export.
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