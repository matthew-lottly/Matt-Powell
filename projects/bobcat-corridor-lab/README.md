# Bobcat Corridor Lab

Python-first portfolio project for designing and evaluating bobcat-focused wildlife corridors.

This project provides a reproducible analysis scaffold that mirrors your workflow:

1. Habitat patch setup from occurrence logic
2. Habitat suitability weighted overlay
3. Resistance surface assembly with barrier costs
4. Least-cost path and corridor delineation
5. Quick connectivity-style evaluation metrics

The current implementation is a practical starter that runs on synthetic rasters, then cleanly maps to real QGIS or ArcGIS datasets.

You can also run the full workflow without QGIS by preparing GeoTIFF inputs directly in Python.

## Why this project

- Focuses on medium-carnivore corridor design with bobcat-specific assumptions.
- Keeps methods explicit and testable in code.
- Produces artifacts you can carry into desktop GIS workflows.

## Quick Start

```bash
pip install -e ".[dev]"
bobcat-corridor init-config --output configs/local_scenario.json
bobcat-corridor run-demo --config configs/default_scenario.json --output-dir outputs/latest-run
bobcat-corridor evaluate --cost-raster outputs/latest-run/cumulative_cost.npy --quantile 0.1
```

## CLI Commands

- `bobcat-corridor init-config`
  - Writes a starter JSON scenario file.
- `bobcat-corridor run-demo`
  - Runs a full synthetic workflow and writes outputs.
- `bobcat-corridor run-real`
  - Runs the same workflow using prepared real raster and barrier-mask inputs.
- `bobcat-corridor prep-raster-stack`
  - Aligns GeoTIFF layers to a reference raster and exports `.npy` arrays.
- `bobcat-corridor run-multipatch`
  - Runs all pairwise corridors between habitat patch IDs in a patch raster.
- `bobcat-corridor render-preview`
  - Generates a quick PNG corridor preview from workflow outputs.
- `bobcat-corridor run-from-manifest`
  - One-command run from `stack_manifest.json` (auto single or multipatch).
- `bobcat-corridor run-pipeline`
  - One-shot pipeline: prepare stack, run analysis, optionally render preview.
- `bobcat-corridor evaluate`
  - Computes corridor mask area and simple cost statistics from an existing cumulative cost raster.

## Real Data Run Example

Inputs can be `.npy`, `.npz`, or GeoTIFF (`.tif`/`.tiff`).

```bash
bobcat-corridor run-real \
  --config configs/default_scenario.json \
  --land-cover data/processed/land_cover_suitability.npy \
  --water-distance data/processed/water_suitability.npy \
  --slope data/processed/slope_suitability.npy \
  --human-footprint data/processed/human_suitability.npy \
  --prey data/processed/prey_suitability.npy \
  --road-mask data/processed/road_mask.npy \
  --urban-mask data/processed/urban_mask.npy \
  --ag-mask data/processed/ag_mask.npy \
  --source 240,125 \
  --target 912,744 \
  --output-dir outputs/houston-run
```

GeoTIFF support is optional:

```bash
pip install -e ".[dev,geo]"
```

Preview PNG export is optional:

```bash
pip install -e ".[dev,viz]"
```

## No-QGIS Pipeline Example

1) Align and convert all GeoTIFF inputs to `.npy` using one reference raster:

```bash
bobcat-corridor prep-raster-stack \
  --reference data/raw/houston_ref.tif \
  --land-cover data/raw/land_cover.tif \
  --water-distance data/raw/water_distance.tif \
  --slope data/raw/slope.tif \
  --human-footprint data/raw/human_footprint.tif \
  --road-mask data/raw/road_mask.tif \
  --urban-mask data/raw/urban_mask.tif \
  --ag-mask data/raw/ag_mask.tif \
  --patches data/raw/patch_ids.tif \
  --output-dir data/processed/stack
```

2) Run pairwise corridor analysis across all patch IDs:

```bash
bobcat-corridor run-multipatch \
  --config configs/default_scenario.json \
  --land-cover data/processed/stack/land_cover.npy \
  --water-distance data/processed/stack/water_distance.npy \
  --slope data/processed/stack/slope.npy \
  --human-footprint data/processed/stack/human_footprint.npy \
  --road-mask data/processed/stack/road_mask.npy \
  --urban-mask data/processed/stack/urban_mask.npy \
  --ag-mask data/processed/stack/ag_mask.npy \
  --patch-raster data/processed/stack/patches.npy \
  --output-dir outputs/multipatch-houston
```

Or run directly from the generated manifest:

```bash
bobcat-corridor run-from-manifest \
  --config configs/default_scenario.json \
  --manifest data/processed/stack/stack_manifest.json \
  --mode auto \
  --output-dir outputs/manifest-houston
```

If your manifest has no `patches` entry, use single mode with explicit source and target:

```bash
bobcat-corridor run-from-manifest \
  --config configs/default_scenario.json \
  --manifest data/processed/stack/stack_manifest.json \
  --mode single \
  --source 240,125 \
  --target 912,744 \
  --output-dir outputs/single-houston
```

## One-Shot Pipeline Example

Run the full workflow in one command (no intermediate manual step):

```bash
bobcat-corridor run-pipeline \
  --config configs/default_scenario.json \
  --reference data/raw/houston_ref.tif \
  --land-cover data/raw/land_cover.tif \
  --water-distance data/raw/water_distance.tif \
  --slope data/raw/slope.tif \
  --human-footprint data/raw/human_footprint.tif \
  --road-mask data/raw/road_mask.tif \
  --urban-mask data/raw/urban_mask.tif \
  --ag-mask data/raw/ag_mask.tif \
  --source 240,125 \
  --target 912,744 \
  --mode single \
  --stack-dir data/processed/stack \
  --output-dir outputs/pipeline-houston \
  --render-preview
```

For multipatch auto mode, pass `--patches data/raw/patch_ids.tif` and keep `--mode auto`.

3) Render a quick PNG for any pair result:

```bash
bobcat-corridor render-preview \
  --suitability outputs/multipatch-houston/patch_1_to_2/suitability.npy \
  --corridor-mask outputs/multipatch-houston/patch_1_to_2/corridor_mask.npy \
  --path-csv outputs/multipatch-houston/patch_1_to_2/least_cost_path.csv \
  --output-png outputs/multipatch-houston/patch_1_to_2/preview.png
```

## Project Layout

```text
bobcat-corridor-lab/
  configs/
    default_scenario.json
  data/
    raw/
    processed/
  outputs/
  src/
    bobcat_corridor_lab/
      cli.py
      config.py
      corridor.py
      raster_ops.py
      workflow.py
  tests/
```

## Mapping to Real Data (QGIS/ArcGIS)

Replace synthetic layers with real rasters and vectors:

- Land cover: NLCD reclass raster
- Water proximity: distance-to-stream/wetland raster
- Slope: DEM-derived slope raster
- Human footprint: pop + road density raster
- Optional prey index raster
- Road/urban/agriculture barrier masks for resistance penalties

Then run the same weighted and cost logic from this package.

### Layer Preparation Guidance

- Ensure all rasters and masks are aligned to the same CRS, extent, pixel size, and shape.
- Suitability layers should be continuous values where larger numbers are more suitable.
- Barrier masks should be binary (0/1) where `1` means barrier present.
- If prey data is unavailable, omit `--prey`; the model will use a zero-valued prey layer.

## Notes

- This code intentionally avoids heavyweight geospatial dependencies in the base install.
- Use it as a robust analysis core, then connect outputs to QGIS/ArcGIS map products.
