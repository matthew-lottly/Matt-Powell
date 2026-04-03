# 3D-VP-LCP

**3-D Vertical Permeability Least-Cost Path** — a LiDAR-driven framework for landscape connectivity analysis.

## What it does

Traditional connectivity models flatten the landscape into a 2-D resistance surface. 3D-VP-LCP preserves the full 3-D structure of vegetation captured by LiDAR point clouds:

1. **Voxelizes** the point cloud into a sparse 3-D grid.
2. Computes **vertical gap fraction (VGF)** per voxel — how open each height level is.
3. Builds a **resistance surface** that combines VGF, vegetation density, slope, and land-cover.
4. Applies **species-specific morphology filters** (height band, clearance, corridor width).
5. Constructs a **3-D graph** and routes a least-cost path (Dijkstra / A*) between habitat patches.

The output is a set of 3-D corridors that show exactly at which heights and through which gaps a species is most likely to travel.

## Why it matters

Many animals move through specific height bands — ground, understory, mid-story, or canopy — and require a minimum vertical gap and horizontal width to pass. Standard 2-D resistance surfaces ignore this vertical structure. 3D-VP-LCP is the first open-source tool to fuse full 3-D voxel LiDAR, vertical gap fraction resistance, organism morphology filters, and 3-D least-cost-path routing into a single framework.

## Quick start

```bash
pip install -e ".[dev,viz]"
```

Generate the sample LiDAR file:

```bash
python -m vp_lcp.scripts.generate_sample_data
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
  lidar_io.py          LAS/LAZ loading and height normalization
  voxelizer.py         Sparse voxelization of point clouds
  vertical_gap.py      Vertical gap fraction computation
  resistance.py        Multi-factor resistance surface
  species_filter.py    Height, clearance, and width filtering
  graph3d.py           3-D graph construction and Dijkstra routing
  visualization.py     2-D cost surface and corridor rendering
  cli.py               Command-line entry point
  scripts/
    generate_sample_data.py
tests/
  test_pipeline.py     12 unit tests covering every pipeline stage
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

## Status

Research prototype. The core pipeline is functional and tested. Planned extensions include circuit-theory integration, multi-scale LiDAR fusion, and temporal change analysis.

## License

MIT
