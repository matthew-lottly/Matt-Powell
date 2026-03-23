# Tool Roadmap

## Current Direction

Geoprompt is strongest when a tool does one of these well:

- turns a repeated GIS workflow into a compact frame method
- stays lightweight without forcing pandas-style table machinery
- composes with the current nearest, predicate, buffer, and coverage primitives
- remains easy to validate against Shapely and GeoPandas when reference behavior exists

The next phase should not be a loose list of GIS verbs. It should be an engine-first roadmap that grows Geoprompt into a serious analysis package with its own algorithms, predictable performance, and clear diagnostics.

## Build Standard

Every new tool in this roadmap should ship with all of the following:

- an owned candidate-generation strategy such as a grid index, graph adjacency, or neighborhood cache
- an owned ranking or scoring step that explains why a result won
- deterministic output ordering and tie-breaking
- regression coverage for edge cases and degenerate geometry
- benchmark coverage on sample, benchmark, and stress corpora
- reference comparison against Shapely, GeoPandas, PySAL, NetworkX, or a documented analytical baseline when one exists

## Performance Standard

Geoprompt should optimize for both small and large datasets instead of treating one as a special case.

- Small datasets should stay fast by avoiding heavy setup costs and dependency overhead.
- Large datasets should avoid brute-force pairwise scans through reusable indexes, graph structures, and cached geometry summaries.
- Tools should prefer bounded candidate sets, not full cross products.
- Expensive derived structures should be reusable across methods when practical.
- Output should stay row-oriented and explainable even when internal execution uses indexes or graphs.

## Engine Foundations

These are the four shared engines that make most of the roadmap possible.

### 1. Spatial Index Engine

- Proposed tools: `spatial_index(...)`, indexed query helpers, reusable candidate caches
- Core algorithm: start with a hashed uniform grid for points, segments, and bounds; add optional hierarchical buckets later
- Why it matters: this is the main way to beat repeated `O(n*m)` scans on joins, overlays, snapping, and density workflows

### 2. Topology Engine

- Proposed tools: noding, snapping, splitting, union, difference, sliver cleanup
- Core algorithm: segment intersection discovery, ordered noding, ring reconstruction, face labeling
- Why it matters: serious overlay and geometry-repair tools require owned topology, not just wrapper methods

### 3. Network Engine

- Proposed tools: graph build, shortest path, service area, allocation, trajectory matching
- Core algorithm: endpoint and intersection extraction, edge segmentation, adjacency lists, weighted path search
- Why it matters: network analysis is one of the highest-value gaps between lightweight geometry packages and full GIS platforms

### 4. Neighborhood Weights Engine

- Proposed tools: spatial lag, autocorrelation, hotspot metrics, neighbor summaries
- Core algorithm: k-nearest, distance-band, and contiguity weights with reusable sparse neighborhood structures
- Why it matters: this unlocks a full class of spatial statistics without forcing a pandas-first design

## The Next 20 Tools

### Foundation And Performance

#### 1. `spatial_index(...)`

- Purpose: build and reuse a lightweight spatial index across repeated operations
- Core algorithm: hashed grid cells keyed by geometry bounds and segment envelopes
- Why Geoprompt can be better: lower setup cost than heavier stacks on operational workloads and more direct reuse across frame methods

#### 2. `hexbin(...)`

- Purpose: generate deterministic hexagonal analysis cells in projected space
- Core algorithm: axial-coordinate lattice generation clipped to frame bounds or a mask
- Why Geoprompt can be better: compact row output with stable ids, not just plotting-oriented bins

#### 3. `fishnet(...)`

- Purpose: generate rectangular analysis grids with stable indexing
- Core algorithm: projected extent tiling with deterministic row and column identifiers
- Why Geoprompt can be better: simpler operational workflows and direct compatibility with coverage, overlay, and hotspot tools

#### 4. `hotspot_grid(...)`

- Purpose: summarize density or weighted intensity into generated bins
- Core algorithm: indexed point-in-cell assignment with optional kernel smoothing pass
- Why Geoprompt can be better: fast, explainable hotspot summaries without bringing in a raster engine first

### Topology And Geometry Repair

#### 5. `snap_geometries(...)`

- Purpose: snap nearby vertices and segments within a tolerance before overlay or dissolve
- Core algorithm: indexed nearest vertex or segment lookup with stable snap ordering and tolerance guards
- Why Geoprompt can be better: workflow-oriented tolerance controls and deterministic repairs instead of opaque validity fixes

#### 6. `clean_topology(...)`

- Purpose: repair gaps, spikes, slivers, duplicate vertices, and dangling artifacts
- Core algorithm: tolerance-driven ring cleanup, short-edge pruning, sliver face detection, and optional ring orientation normalization
- Why Geoprompt can be better: explicit QA outputs that say what was repaired and why

#### 7. `line_split(...)`

- Purpose: split line features by points, intersections, or measures along the line
- Core algorithm: projected cut positions along each line followed by ordered segment reconstruction
- Why Geoprompt can be better: direct support for utility, routing, and corridor workflows with stable part ids

#### 8. `polygon_split(...)`

- Purpose: split polygon features by lines or other polygon boundaries
- Core algorithm: noding plus face extraction with inside or outside labeling against the source polygon
- Why Geoprompt can be better: reproducible polygon part lineage and post-split metrics in one method

#### 9. `overlay_union(...)`

- Purpose: full overlay union with attribute lineage
- Core algorithm: shared topology graph, face reconstruction, and parity-based inclusion rules
- Why Geoprompt can be better: cleaner lineage fields, easier diagnostics, and a direct path to summary outputs

#### 10. `overlay_difference(...)`

- Purpose: subtract one frame's geometry from another
- Core algorithm: shared noding kernel plus left-side face retention rules
- Why Geoprompt can be better: predictable left-side attribute retention and explainable removed-area metrics

#### 11. `overlay_symmetric_difference(...)`

- Purpose: extract geometry covered by exactly one side of an overlay pair
- Core algorithm: face reconstruction with odd-parity membership classification
- Why Geoprompt can be better: cleaner comparison workflows and built-in changed-area summaries

### Network And Accessibility

#### 12. `network_build(...)`

- Purpose: convert line geometry into a reusable edge-node graph
- Core algorithm: endpoint extraction, intersection noding, segmented edge creation, adjacency list assembly
- Why Geoprompt can be better: no need to leave the frame model to build a routing-ready graph

#### 13. `shortest_path(...)`

- Purpose: compute least-cost paths between origins and destinations
- Core algorithm: Dijkstra first, then A* for projected heuristic cases
- Why Geoprompt can be better: lighter operational routing with domain-specific cost fields and deterministic alternatives

#### 14. `service_area(...)`

- Purpose: compute network-constrained reachable coverage from facilities
- Core algorithm: multi-source shortest path with optional polygonization or served-edge summaries
- Why Geoprompt can be better: a stronger analysis primitive than Euclidean buffers while staying explainable

#### 15. `location_allocate(...)`

- Purpose: assign demand to facilities under distance, capacity, or score constraints
- Core algorithm: greedy baseline with optional local-improvement or min-cost-flow refinement
- Why Geoprompt can be better: transparent tradeoffs and custom scoring instead of a fixed black-box allocation model

#### 16. `trajectory_match(...)`

- Purpose: match sequential points to corridor or network edges
- Core algorithm: indexed candidate-edge pruning, transition scoring, and optional hidden-Markov refinement later
- Why Geoprompt can be better: practical field-operations analysis without requiring a full external routing stack

### Spatial Statistics And Analytical Weights

#### 17. `spatial_lag(...)`

- Purpose: compute neighbor-weighted attribute summaries
- Core algorithm: sparse neighborhood weights from k-nearest, distance-band, or contiguity definitions
- Why Geoprompt can be better: reusable building block for many analytical tools with a smaller footprint than table-heavy libraries

#### 18. `spatial_autocorrelation(...)`

- Purpose: compute Moran's I, Geary's C, and local indicators
- Core algorithm: reusable sparse weights engine plus global and local statistic evaluation
- Why Geoprompt can be better: better integration with frame-native neighbor definitions and deterministic local outputs

#### 19. `flow_desire_lines(...)`

- Purpose: turn origin-destination tables into directional geometry and summaries
- Core algorithm: centroid or anchor linking, weighted line generation, and directional aggregation
- Why Geoprompt can be better: stronger planning and operations workflows than a generic line-construction helper

### Temporal And QA Analysis

#### 20. `change_detection(...)`

- Purpose: compare two vintages of features and classify additions, removals, moves, splits, merges, and modified geometry
- Core algorithm: indexed candidate matching, geometry similarity scoring, attribute diff scoring, and change class assignment
- Why Geoprompt can be better: row-level diagnostics and audit-ready outputs, not just overlay results

## Recommended Implementation Order

This order focuses on platform strength, not just feature count.

1. `spatial_index(...)`
2. `hexbin(...)`
3. `fishnet(...)`
4. `hotspot_grid(...)`
5. `network_build(...)`
6. `shortest_path(...)`
7. `service_area(...)`
8. `location_allocate(...)`
9. `snap_geometries(...)`
10. `clean_topology(...)`
11. `line_split(...)`
12. `polygon_split(...)`
13. `overlay_union(...)`
14. `overlay_difference(...)`
15. `overlay_symmetric_difference(...)`
16. `spatial_lag(...)`
17. `spatial_autocorrelation(...)`
18. `flow_desire_lines(...)`
19. `trajectory_match(...)`
20. `change_detection(...)`

## Validation Strategy

- Index-driven tools should prove they reduce candidate counts materially on the benchmark and stress corpora.
- Overlay and topology tools should be compared against Shapely or GEOS-derived expectations on curated fixtures.
- Network tools should be checked against hand-built shortest-path fixtures and NetworkX parity cases where appropriate.
- Statistical tools should be compared against PySAL-style reference values on known small datasets.
- Every tool should publish benchmark timings for sample, benchmark, and stress workloads.

## Definition Of Better

Geoprompt does not need to mimic every API in ArcPy or GeoPandas to compete. It needs to be better in the places where users feel friction today.

- lighter execution on small and medium operational datasets
- reusable internal indexes for repeated analysis
- deterministic output order and tie handling
- richer row-level diagnostics and explainable scores
- stronger built-in planning, siting, routing, QA, and change-analysis workflows
- less dependency overhead for analysis pipelines that do not need a full dataframe stack