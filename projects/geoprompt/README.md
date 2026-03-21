# Geoprompt

Custom spatial analysis package for point, line, and polygon workflows, GeoPandas-style frame access, GeoJSON-compatible inputs and outputs, CRS-aware reprojection, spatial joins, geographic distance options, and GeoPrompt-specific equations for influence, interaction, corridor strength, and neighborhood pressure.

![Generated neighborhood pressure plot from the GeoPrompt demo](assets/neighborhood-pressure-review-live.png)

## Accuracy Posture

GeoPrompt aims to make strong claims only where tests justify them. Deterministic geometry tools are being checked against trusted reference behavior such as Shapely, and statistical or interpolation tools are only described as parity-backed when they have direct fixture coverage against external references such as PySAL or PyKrige.

Use these documents to see what is validated today and what still needs deeper proof:

- `docs/tool-methodology.md` explains each tool's method and maturity level.
- `docs/tool-validation-audit.md` records current evidence, risks, and benchmark status.
- `docs/parity-roadmap.md` tracks remaining reference-parity work.

## Snapshot

- Lane: Spatial package design
- Domain: Reusable custom spatial analysis
- Stack: Python, JSON fixtures, lightweight geometry frame, custom equations
- Includes: GeoPromptFrame object, mixed-geometry helpers, GeoJSON I/O, CRS metadata and reprojection, Euclidean and haversine distance tools, bounding-box queries, radius queries, within-distance predicates, spatial joins, proximity joins, nearest joins, nearest assignment workflows, assignment summaries, catchment competition summaries, fishnet and hexbin grids, hotspot summaries, topology snapping, line splitting, topology cleanup, network build, shortest path, service areas with optional partial-edge output, network location allocation, corridor reach with scoring, anchor-aware network distance, and diagnostics, zone fit scoring with grouped rankings and callbacks, centroid clustering with diagnostics and rollups, buffer, buffer joins, coverage summaries, overlay summaries with grouping and comparison helpers, overlay union with face lineage, dissolve, clip and overlay intersections, nearest-neighbor analysis, gravity model, accessibility index, convex hull, envelope, frame utilities, comparison report tooling, custom influence equations, benchmark corpus, demo report, tests

## Overview

This project starts a reusable spatial package lane instead of another one-off analysis repo. The goal is to build a custom package that users can import directly, similar to how they would reach for GeoPandas, but focused first on a small and clear set of spatial equations that can grow over time.

The initial version still stays intentionally simple, but it now goes beyond points: the frame can work with points, lines, and polygons represented through a small GeoJSON-like geometry mapping. That keeps the package small enough to iterate on while still showing a real package design direction.

## What It Demonstrates

- A package-first project structure rather than a single lab script
- A `GeoPromptFrame` object that behaves like a lightweight spatial table wrapper
- GeoJSON FeatureCollection support so callers can use standard spatial data without reshaping it first
- Custom equations for spatial decay, influence, interaction, corridor strength, and area similarity scoring
- Basic nearest-neighbor analysis for point, line, and polygon centroids
- Bounding-box queries for quick map-window style filtering
- Radius queries for fast proximity filtering around a feature or coordinate anchor
- Within-distance predicates for scoring or filtering without materializing a join
- CRS assignment and reprojection through `GeoPromptFrame.to_crs(...)`
- Spatial joins with `intersects`, `within`, and `contains` predicates
- Proximity joins for distance-based matching without needing an overlay engine
- Nearest joins for `k` closest matches when you want ranked association instead of a fixed distance cutoff
- Nearest assignment for allocating each target feature to a single closest origin
- Assignment summaries for rolling nearest assignments into per-origin counts, ids, and aggregate metrics
- Catchment competition summaries for service-radius overlap analysis with exclusive, shared, won, and unserved targets
- Buffer generation for point, line, and polygon geometries through the overlay engine
- Buffer joins for service-area style matching against surrounding features
- Coverage summaries for fast count and aggregate rollups per service geometry
- Overlay summaries for overlap metrics when you need counts and shares instead of derived geometry outputs
- Topology snapping with `GeoPromptFrame.snap_geometries(...)` for deterministic tolerance-based vertex alignment
- Topology cleanup with `GeoPromptFrame.clean_topology(...)` for duplicate-vertex removal and short-segment pruning
- Line segmentation with `GeoPromptFrame.line_split(...)` for point-driven and intersection-driven corridor splitting
- Dissolve workflows with `GeoPromptFrame.dissolve(...)`
- Overlay operations with `GeoPromptFrame.clip(...)` and `GeoPromptFrame.overlay_intersections(...)`
- Overlay union with `GeoPromptFrame.overlay_union(...)` for polygon face partitioning and lineage-aware outputs
- Network build with `GeoPromptFrame.network_build(...)` for splitting corridors into reusable graph edges and nodes
- Shortest-path routing with `GeoPromptFrame.shortest_path(...)` plus optional route diagnostics
- Service-area analysis with `GeoPromptFrame.service_area(...)` for reachable-edge extraction and optional partial-edge coverage output
- Location allocation with `GeoPromptFrame.location_allocate(...)` for network-cost demand assignment with optional capacity limits
- Corridor reach analysis with `GeoPromptFrame.corridor_reach(...)` for route-proximity screening, scoring, direct or network-style corridor distance, and path-anchor-aware ranking
- Corridor diagnostics with `GeoPromptFrame.corridor_diagnostics(...)` for per-corridor served-feature, score, and anchor-distance rollups
- Zone fit scoring with `GeoPromptFrame.zone_fit_score(...)` for configurable multi-factor zone matching, grouped zone rankings, and workflow-specific score callbacks
- Centroid clustering with `GeoPromptFrame.centroid_cluster(...)` for deterministic spatial grouping plus cluster quality metrics and cluster-count diagnostics
- Cluster rollups with `GeoPromptFrame.summarize_clusters(...)` for per-cluster member counts, dominant groups, and aggregate summaries
- Spatial lag and local autocorrelation with `GeoPromptFrame.spatial_lag(...)` and `GeoPromptFrame.spatial_autocorrelation(...)`
- Autocorrelation reporting with `GeoPromptFrame.summarize_autocorrelation(...)` and `GeoPromptFrame.report_autocorrelation_patterns(...)`
- Overlay group comparison with `GeoPromptFrame.overlay_group_comparison(...)` for top-group and runner-up overlap gaps
- Trajectory matching with `GeoPromptFrame.trajectory_match(...)`, segment summaries, and segment scoring for review queues
- Change detection with event extraction and event-to-event comparison through `GeoPromptFrame.change_detection(...)`, `extract_change_events()`, and `compare_change_events(...)`
- Gravity model and accessibility index equations for interaction and access scoring
- Geometry helpers: `geometry_convex_hull(...)`, `geometry_envelope(...)`, `GeoPromptFrame.envelopes()`, `GeoPromptFrame.convex_hulls()`
- Frame utilities: `select(...)`, `rename_columns(...)`, `filter(...)`, `sort(...)`, `describe()`, `__repr__`, `__getitem__`
- Flat record export with `frame_to_records_flat(...)`, `write_flat_csv(...)`, `write_records_json(...)`, and in-memory GeoJSON loading with `read_geojson(dict)`
- Geographic distance support for longitude/latitude point workflows through haversine distance
- Pairwise interaction analysis without requiring pandas or geopandas
- A demo CLI that exports a real review plot and JSON report from checked-in mixed geometry features
- A comparison CLI that checks Geoprompt outputs against Shapely and GeoPandas across a built-in corpus and records timing data

## Example Usage

```python
import geoprompt as gp

frame = gp.read_points("data/sample_points.json")
scored = frame.assign(
    neighborhood_pressure=lambda current: current.neighborhood_pressure(
        weight_column="demand_index",
        scale=0.14,
        power=1.6,
    )
)

print(scored.head(2))
print(scored.centroid())
print(scored.nearest_neighbors())
```

Mixed geometry example:

```python
import geoprompt as gp

features = gp.read_features("data/sample_features.json")
print(features.geometry_types())
print(features.geometry_lengths())
print(features.geometry_areas())
print(features.query_bounds(-111.97, 40.68, -111.84, 40.79).head())
projected = features.set_crs("EPSG:4326").to_crs("EPSG:3857")
print(projected.bounds())
print(features.nearest_neighbors(k=2)[:4])
```

Spatial join example:

```python
import geoprompt as gp

regions = gp.read_features("data/benchmark_regions.json", crs="EPSG:4326")
assets = gp.read_features("data/benchmark_features.json", crs="EPSG:4326")
joined = regions.spatial_join(assets, predicate="contains")

print(joined.head(3))
```

Proximity query and join example:

```python
import geoprompt as gp

assets = gp.read_features("data/benchmark_features.json", crs="EPSG:4326")
regions = gp.read_features("data/benchmark_regions.json", crs="EPSG:4326")

nearby = assets.query_radius(anchor="alpha-point", max_distance=0.06)
proximity = regions.proximity_join(assets, max_distance=0.08)

print(nearby.head(3))
print(proximity.head(3))
```

Nearest-join example:

```python
import geoprompt as gp

origins = gp.read_features("data/sample_features.json", crs="EPSG:4326")
targets = gp.read_features("data/benchmark_features.json", crs="EPSG:4326")

nearest = origins.nearest_join(targets, k=2, max_distance=0.08, how="left")

print(nearest.head(4))
```

Nearest-assignment example:

```python
import geoprompt as gp

origins = gp.read_features("data/sample_features.json", crs="EPSG:4326")
targets = gp.read_features("data/benchmark_features.json", crs="EPSG:4326")

assigned = origins.assign_nearest(targets, max_distance=0.08, how="left")

print(assigned.head(4))
```

Assignment-summary example:

```python
import geoprompt as gp

origins = gp.read_features("data/sample_features.json", crs="EPSG:4326")
targets = gp.read_features("data/benchmark_features.json", crs="EPSG:4326")

summary = origins.summarize_assignments(
    targets,
    aggregations={"demand_index": "sum"},
    max_distance=0.08,
)

print(summary.head(4))
```

Catchment-competition example:

```python
import geoprompt as gp

origins = gp.read_features("data/sample_features.json", crs="EPSG:4326")
targets = gp.read_features("data/benchmark_features.json", crs="EPSG:4326")

competition = origins.catchment_competition(
    targets,
    max_distance=0.08,
    aggregations={"demand_index": "sum"},
)

print(competition.head(4))
```

Buffer and within-distance example:

```python
import geoprompt as gp

assets = gp.read_features("data/sample_features.json", crs="EPSG:4326")

mask = assets.within_distance(anchor="north-hub-point", max_distance=0.08)
buffers = assets.buffer(distance=0.01)

print(mask)
print(buffers.head(2))
```

Service-area example:

```python
import geoprompt as gp

origins = gp.read_features("data/sample_features.json", crs="EPSG:4326")
targets = gp.read_features("data/benchmark_features.json", crs="EPSG:4326")

service_matches = origins.buffer_join(targets, distance=0.03)
coverage = origins.buffer(distance=0.03).coverage_summary(
    targets,
    aggregations={"demand_index": "sum"},
)

print(service_matches.head(3))
print(coverage.head(3))
```

Overlay example:

```python
import geoprompt as gp

regions = gp.read_features("data/benchmark_regions.json", crs="EPSG:4326")
assets = gp.read_features("data/benchmark_features.json", crs="EPSG:4326")

clipped = assets.clip(regions)
intersections = regions.overlay_intersections(assets)

print(clipped.head(3))
print(intersections.head(3))
```

Overlay-summary example:

```python
import geoprompt as gp

regions = gp.read_features("data/benchmark_regions.json", crs="EPSG:4326")
assets = gp.read_features("data/benchmark_features.json", crs="EPSG:4326")

summary = assets.overlay_summary(
    regions,
    right_id_column="region_id",
    aggregations={"region_name": "count"},
)

print(summary.head(3))
```

Grouped overlay example:

```python
import geoprompt as gp

regions = gp.read_features("data/benchmark_regions.json", crs="EPSG:4326")
assets = gp.read_features("data/benchmark_features.json", crs="EPSG:4326")

summary = assets.overlay_summary(
    regions,
    right_id_column="region_id",
    group_by="region_band",
    normalize_by="both",
    top_n_groups=2,
)

print(summary.head(3))
```

Dissolve example:

```python
import geoprompt as gp

regions = gp.read_features("data/benchmark_regions.json", crs="EPSG:4326")
dissolved = regions.dissolve(by="region_band", aggregations={"region_name": "count"})

print(dissolved.head())
```

Corridor-reach example:

```python
import geoprompt as gp

assets = gp.read_features("data/benchmark_features.json", crs="EPSG:4326")
corridors = assets.filter(lambda r: r["geometry"]["type"] == "LineString")

reach = assets.corridor_reach(
    corridors,
    max_distance=0.05,
    aggregations={"capacity_index": "sum"},
    distance_method="euclidean",
    distance_mode="network",
    path_anchor="nearest",
    score_mode="combined",
    weight_column="capacity_index",
    preferred_bearing=90.0,
)

print(reach.head(3))
```

Corridor-diagnostics example:

```python
import geoprompt as gp

assets = gp.read_features("data/benchmark_features.json", crs="EPSG:4326")
corridors = assets.filter(lambda r: r["geometry"]["type"] == "LineString")

diagnostics = assets.corridor_diagnostics(
    corridors,
    max_distance=0.05,
    corridor_id_column="site_id",
    path_anchor="end",
    score_mode="combined",
)

print(diagnostics.head(3))
```

Autocorrelation reporting example:

```python
import geoprompt as gp

assets = gp.read_features("data/benchmark_features.json", crs="EPSG:4326")

autocorr = assets.spatial_autocorrelation(
    "demand_index",
    mode="distance_band",
    max_distance=0.05,
    permutations=24,
)
report = autocorr.report_autocorrelation_patterns("demand_index")

print(report.head(3))
```

Trajectory scoring example:

```python
import geoprompt as gp

corridors = gp.read_features("data/benchmark_features.json", crs="EPSG:4326").filter(
    lambda row: row["geometry"]["type"] == "LineString"
)
network = corridors.network_build()
observations = gp.GeoPromptFrame.from_records(
    [
        {"site_id": "obs-1", "track_id": "track-a", "sequence": 1, "geometry": {"type": "Point", "coordinates": [-111.95, 40.71]}},
        {"site_id": "obs-2", "track_id": "track-a", "sequence": 2, "geometry": {"type": "Point", "coordinates": [-111.93, 40.72]}},
    ],
    crs="EPSG:4326",
)

scored = network.trajectory_match(observations, candidate_k=3, max_distance=0.05).summarize_trajectory_segments().score_trajectory_segments()

print(scored.head(3))
```

Change-event comparison example:

```python
import geoprompt as gp

baseline = gp.read_features("data/sample_features.json", crs="EPSG:4326")
current = baseline.assign(priority_index=lambda frame: [value + 0.1 for value in frame["priority_index"]])
next_current = baseline.assign(priority_index=lambda frame: [value + 0.2 for value in frame["priority_index"]])

baseline_events = baseline.change_detection(current, max_distance=0.05).extract_change_events()
current_events = baseline.change_detection(next_current, max_distance=0.05).extract_change_events()
event_diff = baseline_events.compare_change_events(current_events, match_mode="equivalent")

print(event_diff.head(3))
```

Tabular export example:

```python
import geoprompt as gp

assets = gp.read_features("data/benchmark_features.json", crs="EPSG:4326")
autocorr = assets.spatial_autocorrelation("demand_index", mode="distance_band", max_distance=0.05)
report = autocorr.report_autocorrelation_patterns("demand_index")

gp.write_records_json("outputs/autocorr-report.records.json", report)
gp.write_flat_csv("outputs/autocorr-report.flat.csv", report)
```

Zone-fit-score example:

```python
import geoprompt as gp

features = gp.read_features("data/benchmark_features.json", crs="EPSG:4326")
zones = gp.read_features("data/benchmark_regions.json", crs="EPSG:4326")

scored = features.zone_fit_score(zones, zone_id_column="region_id")

print(scored.head(3))
```

Weighted zone-fit example:

```python
import geoprompt as gp

features = gp.read_features("data/benchmark_features.json", crs="EPSG:4326")
zones = gp.read_features("data/benchmark_regions.json", crs="EPSG:4326")

scored = features.zone_fit_score(
    zones,
    zone_id_column="region_id",
    score_weights={
        "containment": 0.3,
        "overlap": 0.2,
        "size": 0.2,
        "access": 0.2,
        "alignment": 0.1,
    },
    preferred_bearing=90.0,
    group_by="region_band",
    group_aggregation="max",
    top_n=3,
    score_callback=lambda feature, zone, components, score: score + (0.1 if zone["region_band"] == "north" else 0.0),
)

print(scored.head(3))
```

Clustering example:

```python
import geoprompt as gp

features = gp.read_features("data/benchmark_features.json", crs="EPSG:4326")

clustered = features.centroid_cluster(k=3)

print(clustered.head(5))
```

Clustered output now includes `cluster_size`, `cluster_sse`, `cluster_silhouette`, and `cluster_silhouette_mean`.

Cluster-diagnostics example:

```python
import geoprompt as gp

features = gp.read_features("data/benchmark_features.json", crs="EPSG:4326")

diagnostics = features.cluster_diagnostics([2, 3, 4, 5])
recommended = features.recommend_cluster_count([2, 3, 4, 5], metric="silhouette")

print(diagnostics)
print(recommended)
```

Cluster-summary example:

```python
import geoprompt as gp

features = gp.read_features("data/benchmark_features.json", crs="EPSG:4326")

clustered = features.centroid_cluster(k=3)
summary = clustered.summarize_clusters(group_by="site_type", aggregations={"capacity_index": "sum"})

print(summary.head(3))
```

Overlay-group comparison example:

```python
import geoprompt as gp

regions = gp.read_features("data/benchmark_regions.json", crs="EPSG:4326")
assets = gp.read_features("data/benchmark_features.json", crs="EPSG:4326")

comparison = assets.overlay_group_comparison(
    regions,
    group_by="region_band",
    right_id_column="region_id",
)

print(comparison.head(3))
```

Frame utilities example:

```python
import geoprompt as gp

features = gp.read_features("data/benchmark_features.json", crs="EPSG:4326")

high_demand = features.filter(lambda r: r["demand_index"] > 0.8)
sorted_features = features.sort("demand_index", descending=True)
selected = features.select("site_id", "demand_index")

print(repr(features))
print(features["demand_index"])
print(features.describe())
```

GeoJSON example:

```python
import geoprompt as gp

frame = gp.read_geojson("service-zones.geojson")
nearest = frame.nearest_neighbors(k=1)
nearest_km = frame.nearest_neighbors(k=1, distance_method="haversine")
gp.write_geojson("service-zones-scored.geojson", frame)

print(nearest)
print(nearest_km)
```

## Project Structure

```text
geoprompt/
|-- data/
|   |-- benchmark_features.json
|   |-- benchmark_regions.json
|   |-- sample_features.json
|   `-- sample_points.json
|-- assets/
|   `-- neighborhood-pressure-review-live.png
|-- .github/
|   `-- workflows/
|       `-- geoprompt-ci.yml
|-- src/geoprompt/
|   |-- __init__.py
|   |-- compare.py
|   |-- demo.py
|   |-- geometry.py
|   |-- overlay.py
|   |-- equations.py
|   |-- frame.py
|   `-- io.py
|-- tests/
|   `-- test_geoprompt.py
|-- docs/
|   |-- architecture.md
|   `-- demo-storyboard.md
|-- outputs/
|   |-- charts/
|   |   `-- .gitkeep
|   `-- .gitkeep
|-- pyproject.toml
`-- README.md
```

## Quick Start

```bash
pip install -e .[dev]
geoprompt-demo
```

Install the optional comparison stack when you want to validate against Shapely and GeoPandas:

```bash
pip install -e .[compare]
geoprompt-compare
```

Install only projection support if you want CRS transforms without the full comparison stack:

```bash
pip install -e .[projection]
```

Install only overlay support if you want clip and intersection operations without the full comparison stack:

```bash
pip install -e .[overlay]
```

Install the published package from PyPI with:

```bash
pip install geoprompt
```

Run tests:

```bash
pytest
```

## Current Output

The default demo command writes `outputs/geoprompt_demo_report.json` and `outputs/charts/neighborhood-pressure-review.png` with:

- a frame-level centroid and bounds summary
- CRS and projected Web Mercator bounds metadata
- mixed geometry type summaries, line lengths, and polygon areas
- nearest-neighbor rows for each feature in planar and geographic modes
- per-site neighborhood pressure scores
- anchor influence scores from a selected source node
- corridor accessibility scores for line-style features
- top pairwise interaction rows ranked by the GeoPrompt interaction equation
- top area-similarity rows ranked across polygon-like features
- a bounding-box query count for the default valley review window
- a GeoJSON export in `outputs/geoprompt_demo_features.geojson`
- a committed pressure plot in `assets/neighborhood-pressure-review-live.png`

CI validation is defined in `.github/workflows/geoprompt-ci.yml` and runs tests, demo generation, comparison validation, and package builds.
It also runs `python -m twine check dist/*` so distribution metadata is validated before release.

See [docs/architecture.md](docs/architecture.md) for the package design notes.
See [docs/demo-storyboard.md](docs/demo-storyboard.md) for the reviewer walkthrough.
See [docs/tool-methodology.md](docs/tool-methodology.md) for the current algorithm and maturity classification of the toolset.
See [docs/tool-validation-audit.md](docs/tool-validation-audit.md) for the current validation gaps, benchmark snapshot, and proof plan.
See [docs/parity-roadmap.md](docs/parity-roadmap.md) for the ordered parity and algorithm-hardening plan.

## Custom Equations

- Prompt decay: `1 / (1 + distance / scale) ^ power`
- Prompt influence: `weight * prompt_decay(distance, scale, power)`
- Prompt interaction: `origin_weight * destination_weight * prompt_decay(distance, scale, power)`
- Corridor strength: `weight * log(1 + corridor_length) * prompt_decay(distance, scale, power)`
- Area similarity: `min(area_a, area_b) / max(area_a, area_b) * prompt_decay(distance, scale, power)`

These are intentionally simple first equations. The package now supports two distance modes:

- `euclidean` for planar coordinate space and direct comparison with Shapely and GeoPandas raw-coordinate results
- `haversine` for geographic point-to-point distances in kilometers when your coordinates are longitude/latitude

The package now supports CRS tagging and reprojection, but it is still designed so richer CRS handling, overlays, and additional operators can be layered in later.

## Package Interface

The main package entry points are:

- `geoprompt.read_points(...)`
- `geoprompt.read_features(...)`
- `geoprompt.read_geojson(...)`
- `geoprompt.write_geojson(...)`
- `geoprompt.haversine_distance(...)`
- `GeoPromptFrame.set_crs(...)`
- `GeoPromptFrame.to_crs(...)`
- `GeoPromptFrame.nearest_neighbors(...)`
- `GeoPromptFrame.query_bounds(...)`
- `GeoPromptFrame.query_radius(...)`
- `GeoPromptFrame.within_distance(...)`
- `GeoPromptFrame.spatial_join(...)`
- `GeoPromptFrame.proximity_join(...)`
- `GeoPromptFrame.nearest_join(...)`
- `GeoPromptFrame.assign_nearest(...)`
- `GeoPromptFrame.summarize_assignments(...)`
- `GeoPromptFrame.catchment_competition(...)`
- `GeoPromptFrame.buffer(...)`
- `GeoPromptFrame.buffer_join(...)`
- `GeoPromptFrame.coverage_summary(...)`
- `GeoPromptFrame.overlay_summary(...)`
- `GeoPromptFrame.dissolve(...)`
- `GeoPromptFrame.clip(...)`
- `GeoPromptFrame.overlay_intersections(...)`
- `GeoPromptFrame.neighborhood_pressure(...)`
- `GeoPromptFrame.anchor_influence(...)`
- `GeoPromptFrame.corridor_accessibility(...)`
- `GeoPromptFrame.interaction_table(...)`
- `GeoPromptFrame.area_similarity_table(...)`

## Comparison Workflow

Before calling Geoprompt production-ready, use the comparison CLI to verify results and get a timing snapshot against Shapely and GeoPandas:

```bash
geoprompt-compare
```

This writes `outputs/geoprompt_comparison_report.json` with:

- core metric agreement across the built-in sample and benchmark corpora
- core metric agreement across a generated stress corpus with 93 features and 16 join regions
- reprojection agreement against GeoPandas in EPSG:3857
- dissolve agreement against GeoPandas on the benchmark region corpus
- spatial-join agreement against Shapely and GeoPandas-style predicate behavior
- nearest-neighbor agreement against a Shapely centroid-distance reference
- bounding-box query agreement against GeoPandas
- timing summaries for geometry metrics, reprojection, bounds queries, nearest neighbors, dissolve, clip, and joins

Current validated snapshot from the built-in corpora:

- correctness parity flags are all `true` for bounds, nearest neighbors, bounds queries, geometry metrics, reprojection, clip, dissolve, and spatial join
- Geoprompt is consistently faster on geometry metrics, nearest-neighbor lookup, bounds queries, and dissolve
- the generated stress corpus now shows Geoprompt ahead on both spatial join and clip
- the smaller benchmark corpus now shows `spatial_join` ahead of the reference path in the latest snapshot, while `clip` remains close enough to keep watching in later passes

Representative relative speed ratios from the latest comparison report:

- `sample` corpus: geometry metrics `2.75x`, nearest neighbors `7.50x`, bounds query `61.59x`, reprojection `1.24x`
- `benchmark` corpus: geometry metrics `6.06x`, nearest neighbors `5.93x`, bounds query `24.51x`, reprojection `1.46x`, clip `0.72x`, spatial join `1.11x`, dissolve `18.74x`
- `stress` corpus: geometry metrics `3.35x`, nearest neighbors `6.04x`, bounds query `3.11x`, reprojection `0.98x`, clip `0.76x`, spatial join `3.18x`, dissolve `7.51x`

## Release Readiness

The project now includes:

- an MIT license in `LICENSE`
- a GitHub Actions workflow for repeatable validation
- a checked-in benchmark corpus for broader parity testing
- packaging extras for comparison, projection, and overlay support

## Publication

- License: [LICENSE](LICENSE)
- Standalone publishing notes: [PUBLISHING.md](PUBLISHING.md)
- Changelog: [CHANGELOG.md](CHANGELOG.md)
- Release notes: [docs/release-notes-0.1.8.md](docs/release-notes-0.1.8.md)
- Tool roadmap: [docs/tool-roadmap.md](docs/tool-roadmap.md)
- Tool methodology: [docs/tool-methodology.md](docs/tool-methodology.md)
- Tool validation audit: [docs/tool-validation-audit.md](docs/tool-validation-audit.md)
- Parity roadmap: [docs/parity-roadmap.md](docs/parity-roadmap.md)

## Repository Notes

This copy is intended to be publishable as its own repository.