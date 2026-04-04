# Roadmap

Extended backlog: see [next-50-improvements.md](next-50-improvements.md).

## Labels

Use these GitHub labels to categorize issues and PRs:

| Label | Description |
|---|---|
| `core-engine` | Changes to frame.py, geometry.py, equations.py |
| `analytics` | New or improved analytics (sensitivity, normalization, plugins) |
| `cli` | Demo CLI changes or new subcommands |
| `testing` | New tests, coverage improvements, benchmark updates |
| `docs` | Documentation, tutorials, architecture updates |
| `ci-infra` | CI workflows, pre-commit, build configuration |
| `data-quality` | Input validation, data provenance, schema changes |
| `performance` | Caching, profiling, memory optimization |
| `visualization` | Plotting, chart export, colormaps, styles |
| `breaking` | Breaking API changes |
| `good-first-issue` | Suitable for new contributors |

## Milestones

### v0.2.0 — Validation & Robustness
- Custom exception hierarchy
- Input validation guards for all public APIs
- Schema versioning for output JSON
- Multi-geometry support (MultiPoint, MultiLineString, MultiPolygon)

### v0.3.0 — Analytics Expansion
- Plugin system for decay functions and influence kernels
- Sensitivity analysis and parameter sweep
- Normalization strategies (min-max, z-score, robust)
- Extended analytics (Jaccard similarity, directional corridors)

### v0.4.0 — CLI & Visualization
- Full CLI with subcommands (report, plot, export)
- TOML configuration file support
- Colorblind-safe palettes and style presets
- Multi-format chart export (PNG, SVG, PDF)

### v0.5.0 — Testing & CI
- ≥ 80% code coverage
- Platform matrix (Ubuntu, Windows, macOS)
- Regression test suite with snapshot validation
- Performance benchmarking with regression thresholds
- Configurable benchmark thresholds in `benchmarks/thresholds.json`

### v1.0.0 — Stable Release
- Stable public API
- Complete documentation and tutorials
- Published to PyPI with full metadata
- CITATION.cff with DOI
