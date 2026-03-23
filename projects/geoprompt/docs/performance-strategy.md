# Performance Strategy

## Goal

Geoprompt should feel fast on small datasets and remain tractable on very large datasets without abandoning its row-oriented design.

That requires performance to be a first-class architectural concern, not a cleanup phase after new tools ship.

## Dataset Tiers

Use the same mental model when designing every tool.

- Small: tens to low thousands of features. Setup cost matters more than asymptotic wins.
- Medium: thousands to low hundreds of thousands of features. Candidate pruning becomes essential.
- Large: hundreds of thousands to millions of features or segments. Reusable indexes, sparse structures, streaming, and chunked execution matter more than convenience.

## Core Performance Rules

### 1. Avoid Full Cross Products

- Do not scan every left feature against every right feature unless the dataset is tiny.
- Prefer bounds-first candidate pruning.
- Reuse candidate structures across repeated operations.

### 2. Cache Cheap Geometry Summaries

- bounds
- centroids
- lengths
- areas
- segment envelopes

These should be computed once per execution path when possible.

### 3. Build Reusable Engines

The package should converge on four reusable internal engines:

- spatial index engine
- topology or noding engine
- network engine
- neighborhood weights engine

New tools should depend on these engines rather than re-implementing candidate search each time.

### 4. Optimize For Both Ends

- Small data path: low setup overhead, direct loops, no expensive preprocessing unless the payoff is immediate.
- Large data path: index build once, then reuse across joins, overlays, snapping, and summary passes.

### 5. Keep Outputs Explainable

Internal acceleration is fine. Output should still expose:

- candidate counts when useful
- selected match or path rationale
- summary diagnostics
- deterministic result ordering

## Complexity Targets

These are directional targets, not guarantees.

- bounds query: near `O(k)` after index lookup instead of `O(n)` scan
- spatial join candidate generation: near `O(n + c)` where `c` is surviving candidates, not `O(n*m)`
- nearest-neighbor lookup: indexed local search instead of global sort for every row
- overlay preparation: segment-level candidate pruning before full topology work
- network analysis: `O((V + E) log V)` style path search instead of repeated geometric rescans

## Memory Strategy

- Avoid copying full row dicts more than necessary in hot loops.
- Keep geometry normalization compact and reuse normalized rows.
- Prefer sparse neighborhood and graph structures over dense matrices.
- Add chunked processing options for tools that can stream or summarize incrementally.

## Benchmark Strategy

Every new major tool should be benchmarked on:

- sample corpus for setup overhead and sanity
- benchmark corpus for realistic operational scale
- stress corpus for poor-case or large-case behavior

Every benchmark should answer these questions:

- how many candidates were examined
- where time was spent: index build, candidate pruning, exact evaluation, aggregation
- whether the tool is faster than the naive baseline
- whether the tool remains deterministic across runs

## Validation Strategy

- Compare final outputs to Shapely, GeoPandas, PySAL, or NetworkX where applicable.
- Compare candidate counts and timings to a naive implementation for internal performance validation.
- Keep hand-built edge fixtures for collinearity, coincident edges, narrow gaps, invalid rings, and mixed geometry types.

## Recommended Internal Milestones

1. Add a reusable spatial index layer.
2. Refactor candidate-heavy tools to use it.
3. Add benchmark reporting for candidate counts and pruning ratios.
4. Build network and neighborhood engines on top of the same indexing ideas.
5. Build a topology engine only after snapping and segment indexing are in place.

## What Strong Looks Like

Geoprompt is on the right track if it can do the following consistently:

- beat naive pure-Python scans by large margins on benchmark and stress corpora
- stay competitive on small datasets by avoiding heavy startup costs
- expose diagnostics instead of hiding algorithm behavior
- reuse its internal engines across multiple tools instead of growing one-off implementations