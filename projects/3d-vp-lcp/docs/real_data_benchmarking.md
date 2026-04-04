# Real Data Benchmarking

This guide adds a repeatable path for testing connectivity quality and runtime performance on public LiDAR tiles.

## 1. Create a tile manifest

Copy and edit [data/public_lidar_tile.example.json](../data/public_lidar_tile.example.json), or use one of the included USGS manifests.

Additional included manifests for cross-site testing:
- [data/public_lidar_tile.ca_orangeco_ept_node.json](../data/public_lidar_tile.ca_orangeco_ept_node.json)
- [data/public_lidar_tile.al_northal_ept_node.json](../data/public_lidar_tile.al_northal_ept_node.json)

Preferred strict-gate baseline dataset set:
- [data/public_lidar_tile.ia_eastern_1_2019_ept_node.json](../data/public_lidar_tile.ia_eastern_1_2019_ept_node.json)
- [data/public_lidar_tile.ca_alamedaco_1_2021_ept_node.json](../data/public_lidar_tile.ca_alamedaco_1_2021_ept_node.json)
- [data/public_lidar_tile.al_northal_ept_node.json](../data/public_lidar_tile.al_northal_ept_node.json)

Required fields:
- `name`: friendly label for the tile.
- `url`: direct download URL to a LAS or LAZ file.
- `output_file`: output filename to save under `data/`.
- `sha256`: optional checksum. Keep `null` when unknown.

## 2. Download the real tile

Run:

```bash
python -m vp_lcp.scripts.fetch_public_tile \
  --manifest data/public_lidar_tile.ia_fullstate_ept_node.json \
  --data-dir data
```

If the file exists and checksum matches, it is reused.

## 3. Run quality/performance benchmark matrix

Run:

```bash
python -m vp_lcp.scripts.benchmark_real_tile \
  --tile data/IA_FullState_ept_0-0-0-0.laz \
  --output-root outputs/real-data-benchmark \
  --voxel-sizes 1.0,2.0 \
  --neighbours 6,18,26 \
  --algorithms dijkstra,astar \
  --normalize-options false,true \
  --min-height 0.0 \
  --species-h-min 0.0 \
  --species-h-max 60.0 \
  --vegetation-classes 2,3,4,5
```

Outputs:
- `outputs/real-data-benchmark/benchmark_results.csv`
- `outputs/real-data-benchmark/benchmark_results.json` with run summary and best successful run
- One folder per run configuration with corridor outputs and run report.

## 4. Interpreting the score

The benchmark stores two derived metrics:
- `connectivity_efficiency = path_voxel_count / path_cost`
- `runtime_penalized_score = connectivity_efficiency / runtime_seconds`

A larger `runtime_penalized_score` means the run produced an efficient corridor with lower runtime.

## 5. Recommended first pass for high accuracy and performance

- Start with `voxel_size=1.0` and `voxel_size=2.0` only.
- Compare `neighbours=18` and `neighbours=26` for richer connectivity topology.
- Keep both `dijkstra` and `astar` in the sweep.
- Enable resistance normalization in one half of the sweep to test metric stability across tiles.

After selecting the best configuration, rerun the same tile with only that setup and archive the output report as your baseline.

The current robust default candidate from strict-gate cross-site ranking is stored in [configs/robust_default_candidate.json](../configs/robust_default_candidate.json).

Current recommended strict-gate baseline config:
- `voxel_size = 3.0`
- `neighbours = 26`
- `algorithm = dijkstra`
- `normalize_resistance = true`
- `species_h_max = 80.0`

## 6. Cross-site robust default selection

After running benchmarks on multiple tiles, aggregate site outputs and choose the best full-coverage config:

```bash
python -m vp_lcp.scripts.benchmark_cross_site \
  --site ia=outputs/real-data-benchmark-ia/benchmark_results.csv \
  --site ca=outputs/real-data-benchmark-ca/benchmark_results.csv \
  --site al=outputs/real-data-benchmark-al/benchmark_results.csv \
  --output-root outputs/real-data-cross-site
```

Outputs:
- `outputs/real-data-cross-site/cross_site_summary.csv`
- `outputs/real-data-cross-site/cross_site_summary.json`

The selected robust default is the full-coverage configuration with the best mean site rank, then best worst-site rank, then fastest mean runtime.

Current best strict-gate full-coverage result:
- `voxel_size = 3.0`
- `neighbours = 26`
- `algorithm = dijkstra`
- `normalize_resistance = true`
- `mean_site_rank = 2.333`
- `worst_site_rank = 4`
- `mean_runtime_seconds = 2.470`

## 7. 3D interpretability summary artifacts

For run folders that contain `corridor.csv` and `run_report.json`, generate a compact 3D summary:

```bash
python -m vp_lcp.scripts.summarize_3d_runs --root outputs/baseline-stress
```

## 8. One-command recommended baseline reproduction

To fetch the preferred baseline tiles, run the recommended config on each site, and generate per-site plus cross-site summaries:

```bash
python -m vp_lcp.scripts.reproduce_recommended_baseline --output-root outputs/recommended-baseline-repro
```

Main artifacts:
- `outputs/recommended-baseline-repro/{ia,ca,al}/benchmark_results.csv`
- `outputs/recommended-baseline-repro/{ia,ca,al}/three_d_summary.md`
- `outputs/recommended-baseline-repro/cross-site/cross_site_summary.json`
- `outputs/recommended-baseline-repro/baseline_reproduction_report.json`

## 9. Performance regression threshold checks

After generating `benchmark_results.json` and `three_d_summary.json`, enforce runtime and quality floors with:

```bash
python -m vp_lcp.scripts.check_performance_thresholds --benchmark-json outputs/smoke-benchmark/benchmark_results.json --summary-json outputs/smoke-benchmark/three_d_summary.json --thresholds configs/smoke_performance_thresholds.json
```

The default threshold profile in `configs/smoke_performance_thresholds.json` checks:
- max runtime ceiling
- minimum path voxel count
- minimum graph node count
- informative 3D requirement
- minimum informative run count

Outputs:
- `three_d_summary.csv` with runtime, corridor z-statistics, XY footprint span, and height-band counts
- `three_d_summary.md` for quick review in GitHub/VS Code
- `three_d_summary.json` with explicit informative vs non-informative run lists

See [docs/recommended_baseline.md](recommended_baseline.md) for the current recommended strict-gate default and [docs/future_work_and_outputs.md](future_work_and_outputs.md) for the next-stage backlog.

Default 3D quality gate thresholds:
- `path_voxel_count >= 2`
- `z_std >= 0.05`
- `unique_xy_columns >= 2`

You can change thresholds per analysis run, for example:

```bash
python -m vp_lcp.scripts.summarize_3d_runs --root outputs/baseline-stress --min-path-voxels 3 --min-z-std 0.1 --min-unique-xy-columns 3
```
