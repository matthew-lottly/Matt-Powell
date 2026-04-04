# Recommended Baseline

This document records the current recommended strict-gate baseline for real-data 3D connectivity runs.

## Recommended config

Use [configs/robust_default_candidate.json](../configs/robust_default_candidate.json) as the baseline config.

Current values:

- `voxel_size = 3.0`
- `neighbours = 26`
- `algorithm = dijkstra`
- `normalize_resistance = true`
- `species_h_max = 80.0`

This is the current best strict-gate full-coverage configuration from cross-site ranking.

## Preferred baseline datasets

Use these public LiDAR manifests for baseline comparisons:

- Iowa: [data/public_lidar_tile.ia_eastern_1_2019_ept_node.json](../data/public_lidar_tile.ia_eastern_1_2019_ept_node.json)
- California: [data/public_lidar_tile.ca_alamedaco_1_2021_ept_node.json](../data/public_lidar_tile.ca_alamedaco_1_2021_ept_node.json)
- Alabama: [data/public_lidar_tile.al_northal_ept_node.json](../data/public_lidar_tile.al_northal_ept_node.json)

These three sites provide the current strict-gate baseline set because each can produce informative 3D corridors under the same configuration.

## Why this baseline won

Cross-site aggregation in [outputs/replacement-cross-site-strict/cross_site_summary.json](../outputs/replacement-cross-site-strict/cross_site_summary.json) selected this as the best full-coverage strict-gate result with:

- `site_count = 3`
- `mean_site_rank = 2.333`
- `worst_site_rank = 4`
- `mean_runtime_seconds = 2.470`

The main reason to prefer this configuration is not that it is the single best run on any one site. It is that it remains informative across Iowa, California, and Alabama while keeping runtime acceptable.

## Stress-set check

The expanded stress-set summary in [outputs/recommended-baseline/three_d_summary.md](../outputs/recommended-baseline/three_d_summary.md) and [outputs/recommended-baseline/three_d_summary.json](../outputs/recommended-baseline/three_d_summary.json) shows:

- `run_count = 7`
- `informative_count = 4`
- `non_informative_count = 3`

Informative runs:

- `ca_alameda_main`: `runtime=0.990s`, `path_voxels=24`, `mean_z=1.625`, `z_std=0.599`, `xy_columns=24`
- `al_17co2_main`: `runtime=1.134s`, `path_voxels=41`, `mean_z=2.817`, `z_std=1.880`, `xy_columns=41`
- `ia_eastern_main`: `runtime=1.196s`, `path_voxels=43`, `mean_z=1.570`, `z_std=0.452`, `xy_columns=43`
- `al_northal_main`: `runtime=1.450s`, `path_voxels=42`, `mean_z=1.643`, `z_std=0.639`, `xy_columns=42`

Non-informative runs:

- `ia_fullstate_child154`
- `al_17co1_main`
- `ca_northcoast_main`

Each non-informative run failed for the same reason: a one-voxel corridor with no meaningful vertical or horizontal spread.

## Interpretation guidance

Use this baseline when you want a default that is robust enough for cross-site comparison and still conservative about ecological interpretation.

Treat runs as informative only when they satisfy the default 3D quality gate:

- `path_voxel_count >= 2`
- `z_std >= 0.05`
- `unique_xy_columns >= 2`

When a run fails the gate, do not interpret the resulting corridor as evidence of meaningful 3D connectivity. Instead, treat it as a prompt to inspect scene suitability, patch placement, and tile selection.

## Recommended usage

1. Download the preferred three baseline datasets.
2. Run the baseline config unchanged on each site.
3. Generate `three_d_summary` artifacts for each output root.
4. Compare future parameter changes against this baseline before updating defaults.

You can run all four steps in one command:

```bash
python -m vp_lcp.scripts.reproduce_recommended_baseline --output-root outputs/recommended-baseline-repro
```

## Primary artifacts

- Config: [configs/robust_default_candidate.json](../configs/robust_default_candidate.json)
- Cross-site ranking: [outputs/replacement-cross-site-strict/cross_site_summary.json](../outputs/replacement-cross-site-strict/cross_site_summary.json)
- Stress-set markdown summary: [outputs/recommended-baseline/three_d_summary.md](../outputs/recommended-baseline/three_d_summary.md)
- Stress-set JSON summary: [outputs/recommended-baseline/three_d_summary.json](../outputs/recommended-baseline/three_d_summary.json)
- One-command repro script: [src/vp_lcp/scripts/reproduce_recommended_baseline.py](../src/vp_lcp/scripts/reproduce_recommended_baseline.py)