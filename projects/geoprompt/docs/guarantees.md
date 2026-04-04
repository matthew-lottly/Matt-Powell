# Geoprompt Guarantees

This document defines the current reliability contract for Geoprompt.

## Correctness Contract

- Geometry normalization supports Point, LineString, Polygon, MultiPoint, MultiLineString, and MultiPolygon.
- All distance-based operations are deterministic for the same input, parameters, and Python version.
- Ranked outputs must use deterministic tie-breaking when scores are equal.
- JSON outputs include `schema_version` so consumers can detect breaking changes.

## Approximation Contract

- Haversine calculations assume spherical Earth radius 6371.0088 km.
- Euclidean calculations use native coordinate units and require CRS-aware interpretation by callers.
- Pairwise large-data options (`max_distance`, `max_results`, `chunk_size`, `sample`) may trade completeness for runtime.

## Reproducibility Contract

- CLI commands that write analysis outputs also write a run manifest in `outputs/manifests/`.
- Manifest includes input hash, command args, platform, python version, and git commit (when available).
- Runs are reproducible when input file hash and args are unchanged.
- Pipeline steps support retry and `continue_on_error` policies, and every step status is recorded in manifest metadata.
- Batch pipeline mode writes per-input manifests plus a top-level batch summary artifact.

## Regression Contract

- Golden snapshot fixtures in `tests/golden/` are treated as compatibility references for key outputs.
- Changes to snapshot expectations must be intentional and reviewed with release notes.

## Stability Levels

- Stable: core frame methods, IO functions, schema version handling, and CLI command names.
- Beta: plugin extension interfaces and sensitivity utilities.
- Experimental: performance heuristics and benchmark thresholds.

Public API stability markers are exported in `geoprompt.API_STABILITY`.

## Non-Goals (Current)

- Bit-identical floating-point parity across all OS/CPU combinations.
- Full topology model beyond current geometric predicate set.
- Automatic CRS inference from arbitrary user data without explicit metadata.