# Geoprompt Improvement Backlog (50 Items)

This backlog is organized as concrete, issue-ready improvements.

## Reliability and Contracts

1. Add strict JSON schema validation for every CLI output artifact.
2. Add manifest schema version migration tests for backward compatibility.
3. Add cross-platform float-tolerance policy docs with explicit thresholds.
4. Add contract tests for every analysis tool output column set.
5. Add deterministic ordering checks for all table-returning methods.

## Performance and Scale

6. Add streaming GeoJSON reader for very large FeatureCollections.
7. Add optional multiprocessing mode for pairwise-heavy analyses.
8. Add benchmark datasets at 10k and 50k feature scales.
9. Add memory usage benchmarks and fail thresholds in CI.
10. Add adaptive chunk-size auto-tuning based on available memory.

## CLI and Pipeline UX

11. Add pipeline step-level timeout controls.
12. Add pipeline-level fail-fast and fail-at-end execution modes.
13. Add pipeline variable templating for reuse across environments.
14. Add pipeline dry-run validator with full step expansion preview.
15. Add pipeline output index file linking every produced artifact.

## Spatial Methods

16. Add weighted nearest-neighbor with configurable tie logic.
17. Add network-constrained distance mode for path-based travel time.
18. Add spatial autocorrelation tools (Moran's I and Geary's C).
19. Add hex-bin aggregation utilities for regional summarization.
20. Add kernel density estimation with bandwidth controls.

## Data Quality and Validation

21. Add null-geometry repair helpers and diagnostics report.
22. Add duplicate-feature detection and optional deduplication strategy.
23. Add coordinate-range sanity checks per CRS family.
24. Add invalid polygon ring orientation detection and warnings.
25. Add row-level validation report with severity categories.

## Interoperability

26. Add Parquet/GeoParquet read and write support.
27. Add PostGIS export helper with schema and SRID controls.
28. Add Arrow table export for fast downstream analytics.
29. Add direct conversion helpers to GeoPandas and Shapely objects.
30. Add optional pyogrio-backed IO path for speed improvements.

## Visualization and Reporting

31. Add map legend templates for common analysis outputs.
32. Add static report generator for HTML summary pages.
33. Add small-multiple chart export for scenario comparisons.
34. Add cartographic scale bar and north-arrow rendering option.
35. Add style validation to prevent invalid colormap/style combinations.

## Developer Experience

36. Add typed protocol interfaces for plugin extension points.
37. Add mkdocs site with versioned API and how-to guides.
38. Add command to print effective runtime config and defaults.
39. Add pre-commit hooks for lint, format, and test quick checks.
40. Add contributor checklist for adding new analysis tools.

## CI, Release, and Governance

41. Add release-candidate workflow with smoke tests on tagged builds.
42. Add dependency update policy with automated weekly PRs.
43. Add changelog category enforcement in PR templates.
44. Add signed artifact verification in release workflow.
45. Add coverage floor gate per module, not only global coverage.

## Security and Operational Safety

46. Add input file size guardrails with override switches.
47. Add CLI safe-mode that blocks overwrite unless explicitly allowed.
48. Add provenance chain field linking derived artifacts to sources.
49. Add optional checksum verification for external benchmark fixtures.
50. Add security review checklist for every minor release.
