# 3D-VP-LCP

**3-D Vertical Permeability Least-Cost Path** — a LiDAR-driven framework for landscape connectivity analysis.

## What it does

Traditional connectivity models flatten the landscape into a 2-D resistance surface. 3D-VP-LCP preserves the full 3-D structure of vegetation captured by LiDAR point clouds:

1. **Voxelizes** the point cloud into a sparse 3-D grid.
2. Computes **vertical gap fraction (VGF)** per voxel — how open each height level is.
3. Builds a **resistance surface** that combines VGF, vegetation density, slope, and land-cover.
4. Applies **species-specific morphology filters** (height band, clearance, corridor width).
5. Constructs a **3-D graph** and routes a least-cost path (Dijkstra or A*) between habitat patches.

The output is a set of 3-D corridors that show exactly at which heights and through which gaps a species is most likely to travel.

## Why it matters

Many animals move through specific height bands — ground, understory, mid-story, or canopy — and require a minimum vertical gap and horizontal width to pass. Standard 2-D resistance surfaces ignore this vertical structure. 3D-VP-LCP is the first open-source tool to fuse full 3-D voxel LiDAR, vertical gap fraction resistance, organism morphology filters, and 3-D least-cost-path routing into a single framework.

## Quick start

```bash
pip install -e ".[dev,viz]"
```

Write a default config file:

```bash
vp-lcp init-config --output vp_lcp_config.json
```

Generate the sample LiDAR file:

```bash
python -m vp_lcp.scripts.generate_sample_data
```

Run the full pipeline on the sample data:

```bash
vp-lcp run --input data/sample_lidar.las --output-dir outputs/latest-run
```

Run the benchmark script:

```bash
python -m vp_lcp.scripts.benchmark_sample
```

Download a public LAS/LAZ tile from a manifest:

```bash
python -m vp_lcp.scripts.fetch_public_tile --manifest data/public_lidar_tile.ia_eastern_1_2019_ept_node.json --data-dir data
```

Run the real-data quality/performance benchmark sweep:

```bash
python -m vp_lcp.scripts.benchmark_real_tile --tile data/IA_Eastern_1_2019_ept_0-0-0-0.laz --output-root outputs/real-data-benchmark --min-height 0.0 --species-h-min 0.0 --species-h-max 80.0 --vegetation-classes 2,3,4,5
```

Aggregate multiple site benchmark outputs into one robust default ranking:

```bash
python -m vp_lcp.scripts.benchmark_cross_site --site ia=outputs/real-data-benchmark-ia/benchmark_results.csv --site ca=outputs/real-data-benchmark-ca/benchmark_results.csv --site al=outputs/real-data-benchmark-al/benchmark_results.csv --output-root outputs/real-data-cross-site
```

Generate an interpretable 3D corridor summary from run outputs:

```bash
python -m vp_lcp.scripts.summarize_3d_runs --root outputs/baseline-stress
```

Check benchmark outputs against performance thresholds:

```bash
python -m vp_lcp.scripts.check_performance_thresholds --benchmark-json outputs/smoke-benchmark/benchmark_results.json --summary-json outputs/smoke-benchmark/three_d_summary.json --thresholds configs/smoke_performance_thresholds.json
```

Run the full recommended baseline workflow in one command:

```bash
python -m vp_lcp.scripts.reproduce_recommended_baseline --output-root outputs/recommended-baseline-repro
```

Use the current robust default candidate config:

```bash
vp-lcp run --input data/IA_Eastern_1_2019_ept_0-0-0-0.laz --config configs/robust_default_candidate.json --output-dir outputs/robust-default-run
```

Run the test suite:

```bash
pytest -q
```

Open the tutorial notebook:

```
examples/tutorial.ipynb
```

## Project layout

```
src/vp_lcp/
  config.py            Run configuration models and JSON serialization
  lidar_io.py          LAS/LAZ loading, metadata, and height normalization
  voxelizer.py         Sparse voxelization of point clouds
  vertical_gap.py      Vertical gap fraction computation
  resistance.py        Multi-factor resistance surface
  species_filter.py    Height, clearance, and width filtering
  graph3d.py           3-D graph construction and routing
  pipeline.py          End-to-end pipeline runner and result reporting
  exports.py           Corridor and run-artifact export helpers
  visualization.py     2-D cost surface and corridor rendering
  cli.py               Command-line entry point
  scripts/
    generate_sample_data.py
    benchmark_sample.py
tests/
  test_pipeline.py     21 tests covering units, smoke runs, and CLI paths
examples/
  tutorial.ipynb       End-to-end walkthrough with sample data
data/
  sample_lidar.las     Synthetic 12 000-point LiDAR file
```

## Pipeline overview

```
LAS/LAZ → normalize heights → voxelize → VGF → resistance surface
  → species filter → 3-D graph → least-cost path → corridor output
```

### Resistance formula

$$R_{ijk} = \alpha \cdot (1 - \text{VGF}(z_k)) + \beta \cdot p_{ijk} + \gamma \cdot \text{Slope}_{ij} + \delta \cdot \text{LC}_{ij}$$

### Species filtering

- **Height band**: keep voxels where $h_{\min} \le z \le h_{\max}$.
- **Vertical clearance**: require $\lceil h_c / v \rceil$ consecutive low-density voxels above.
- **Horizontal width**: remove connected components smaller than $w_c \times w_c$.

## Data sources

Free LiDAR tiles can be downloaded from USGS 3DEP, OpenTopography, and NOAA. The sample data generator produces a synthetic tile for testing.

For a repeatable real-tile ingestion and benchmark workflow, see [docs/real_data_benchmarking.md](docs/real_data_benchmarking.md).
For the current recommended baseline details, see [docs/recommended_baseline.md](docs/recommended_baseline.md).

### LAS classification assumptions

- Ground points default to class `2`.
- Vegetation points default to classes `3`, `4`, and `5`.
- The pipeline records point-count, extent, elevation range, and class-count metadata for each run.
- These defaults are configurable through the pipeline config JSON.

## Status

Research prototype. The core pipeline is now runnable from the CLI, benchmarked on the bundled synthetic sample, and covered by unit, smoke, CLI, and routing tests. Planned extensions include circuit-theory integration, multi-scale LiDAR fusion, and temporal change analysis.

## Roadmap

See [docs/roadmap.md](docs/roadmap.md) for the 50-item implementation and testing checklist covering data ingest, voxel and VGF logic, species filtering, routing, validation, and performance work.

## License

MIT
