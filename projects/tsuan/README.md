# TSUAN: Temporal-Spatial Uncertainty-Aware Attention Network

**Uncertainty-aware attention for irregularly sampled geospatial time series.**

TSUAN performs cloud removal on Sentinel-2 L2A multispectral imagery by fusing optical data with Sentinel-1 SAR through uncertainty-weighted attention mechanisms. The architecture produces calibrated, hierarchical uncertainty estimates alongside reconstructed cloud-free images.

## Review Artifacts

- Example output: [EXAMPLE_OUTPUT.md](EXAMPLE_OUTPUT.md)
- Data-flow diagram: [docs/data-flow.md](docs/data-flow.md)
- Runbook: [docs/runbook.md](docs/runbook.md)

## Architecture

```
Sentinel-2 (optical) ──► Optical Encoder ──┐
                                           ├──► Uncertainty-Weighted   ──► Decoder ──► x̂ (reconstructed)
Sentinel-1 (SAR) ──────► SAR Encoder ──────┘    Attention Block              │
                                           │                                 ├──► σ²_pixel
Cloud Mask ──► Uncertainty Encoder ────────┘                                 ├──► σ²_patch
                                                                             └──► σ²_region
```

### Key Components

| Module | Description | Equation |
|--------|-------------|----------|
| Dual-Stream Encoder | Parallel CNN encoders for optical + SAR | $h = E(x)$ |
| Uncertainty Encoder | MLP encoding cloud probability masks | $u_{enc} = \text{MLP}(u_{mask})$ |
| Dynamic Temperature | Per-pixel attention temperature | $\lambda = \text{Softplus}(\text{MLP}(h, u_{enc}))$ |
| Intra-Modal Attention | Self-attention with uncertainty penalty | $\text{score}(i,j) = \frac{q_i \cdot k_j}{\sqrt{D}} - \lambda_j \cdot u_j$ |
| Cross-Modal Attention | SAR→optical with physical violation penalty | $\text{score} = \frac{q_{opt} \cdot k_{sar}}{\sqrt{D}} - \gamma \cdot P_{viol}$ |
| Hierarchical Uncertainty | Pixel (1×1), patch (3×3+pool), region (GAP) heads | $\sigma^2$ at three spatial scales |
| TTA Inference | Test-time augmentation with variance fusion | $\sigma^2 = \sigma^2_{model} + \eta \cdot \text{Var}(\hat{x}_{aug})$ |

### Loss Function

$$\mathcal{L} = \mathcal{L}_{recon} + \alpha_1 \mathcal{L}_{unc} + \alpha_2 \mathcal{L}_{phys} + \alpha_3 \mathcal{L}_{smooth} + \alpha_4 \mathcal{L}_{aux}$$

- **L_recon**: L1 reconstruction on clear pixels
- **L_unc**: NLL uncertainty calibration
- **L_phys**: NDVI/EVI physical plausibility constraints
- **L_smooth**: Temporal smoothness
- **L_aux**: Auxiliary cloud segmentation

Curriculum learning linearly ramps auxiliary loss weights over configurable epochs.

## Installation

```bash
pip install -e .

# With training dependencies
pip install -e ".[train]"

# With ONNX export
pip install -e ".[deploy]"

# Full development
pip install -e ".[dev,train,deploy]"
```

## Quick Start

```python
import torch
from tsuan.model import TSUAN
from tsuan.config import TSUANConfig

cfg = TSUANConfig()
model = TSUAN(cfg)

# Sentinel-2 optical (B, T, 13, H, W)
x_opt = torch.randn(1, 12, 13, 256, 256)
# Sentinel-1 SAR (B, T, 2, H, W)
x_sar = torch.randn(1, 12, 2, 256, 256)
# Cloud probability mask (B, T, 1, H, W)
u_mask = torch.rand(1, 12, 1, 256, 256)

out = model(x_opt, x_sar, u_mask)
print(out["x_hat"].shape)       # (1, 12, 13, 256, 256)
print(out["sigma_pixel"].shape) # (1, 12, 1, 16, 16)
```

### Inference with TTA

```python
from tsuan.inference import load_checkpoint, predict_with_tta

model = load_checkpoint("checkpoints/best.pt", device="cuda")
result = predict_with_tta(model, x_opt, x_sar, u_mask, n_augments=8)
```

### Training

```python
from tsuan.config import TSUANConfig
from tsuan.train import Trainer

cfg = TSUANConfig()
cfg.data.data_root = "path/to/sentinel_data"
trainer = Trainer(cfg)
trainer.train()
```

## Data Format

Expected directory structure:

```
data_root/
├── optical/       # .npy files, shape (T, 13, H, W)
├── sar/           # .npy files, shape (T, 2, H, W)
├── cloud_mask/    # .npy files, shape (T, 1, H, W)
└── splits/
    ├── train.txt  # patch IDs, one per line
    ├── val.txt
    └── test.txt
```

## Target Benchmarks

| Metric | Target |
|--------|--------|
| PSNR | ≥2 dB over UnCRtainTS |
| ECE | < 0.05 |
| Physical plausibility | < 5% violations |
| Inference latency | < 1 sec / 256×256 patch (CPU) |

## Project Structure

```
src/tsuan/
├── __init__.py       # Package metadata
├── config.py         # Dataclass-based configuration
├── encoder.py        # Dual-stream CNN encoder
├── attention.py      # Uncertainty-weighted attention
├── uncertainty.py    # Hierarchical uncertainty heads
├── decoder.py        # Symmetric upsampling decoder
├── model.py          # Full TSUAN model + EMA
├── losses.py         # All loss components
├── data.py           # Dataset and DataLoader
├── train.py          # Training loop with curriculum
└── inference.py      # TTA inference + ONNX export
```

## License

MIT
