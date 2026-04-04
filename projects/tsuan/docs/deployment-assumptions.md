# Deployment Assumptions

Deployment context and operational notes for TSUAN.

## Prerequisites

- Python 3.10+
- PyTorch 2.1+, torchvision 0.16+
- rasterio 1.3+ (for Sentinel-2 and SAR I/O)
- xarray 2023.6+ (for temporal data management)
- NumPy, SciPy, matplotlib

## Installation

```bash
pip install -e .[dev]
```

For GPU acceleration:

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install -e .[dev]
```

## Expected Input Data

| Input | Source | Resolution |
| --- | --- | --- |
| Sentinel-2 L2A | Copernicus Open Access Hub | 10m multispectral |
| Sentinel-1 GRD | Copernicus Open Access Hub | 10m SAR (VV, VH) |
| Cloud mask | Sentinel-2 SCL band or external | Binary cloud/no-cloud |

## Running Inference

```bash
python -m tsuan.predict --optical path/to/s2_stack.tif --sar path/to/s1_stack.tif --output reconstructed.tif
```

The model produces:
- Cloud-free reconstructed multispectral image
- Pixel-level uncertainty map
- Patch-level and region-level uncertainty estimates

## Deployment Assumptions

- The current implementation is a research prototype demonstrating the architecture
- Training requires paired cloudy/cloud-free Sentinel-2 scenes with co-registered SAR
- Inference runs on single-scene inputs (temporal stacking is handled internally)
- GPU strongly recommended for full-resolution Sentinel-2 tiles (10980×10980 pixels)
- Memory requirement: ~8GB VRAM for a standard tile at 10m resolution

## Benchmark Context

The architecture is evaluated on:

- **PSNR** (Peak Signal-to-Noise Ratio): reconstruction quality
- **SSIM** (Structural Similarity Index): perceptual quality
- **Uncertainty calibration**: coverage of prediction intervals at specified confidence levels
- **AUCRC** (Area Under the Risk-Coverage Curve): uncertainty-aware quality

## Limitations

- Training data is synthetic or curated for demonstration purposes
- The dual-stream architecture requires co-registered optical and SAR pairs
- Physical plausibility constraints assume standard reflectance ranges
- Test-time augmentation increases inference time by a factor proportional to the augmentation count
