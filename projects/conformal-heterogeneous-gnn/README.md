# Conformalized Message Passing on Heterogeneous Infrastructure Graphs

**Coverage Guarantees for Interdependent Utility Networks**

## Abstract

This project introduces *Conformalized Heterogeneous Message Passing* (CHMP), a framework that combines heterogeneous graph neural networks with split conformal prediction to produce uncertainty-quantified risk predictions across coupled infrastructure systems (power, water, telecom). Unlike existing conformal prediction methods for graphs—which assume homogeneous node/edge types—CHMP provides Mondrian-style per-type coverage guarantees on heterogeneous graphs, and introduces a propagation-aware calibration scheme that accounts for multi-hop error propagation across utility boundaries.

## Key Contributions

1. **Heterogeneous conformal calibration**: Mondrian grouping by infrastructure type yields per-type coverage guarantees (Theorem 1).
2. **Propagation-aware nonconformity scores**: Neighborhood-aggregated residuals account for how message passing propagates errors across coupled layers, producing tighter intervals while maintaining coverage.
3. **Synthetic benchmark**: A configurable generator for coupled power/water/telecom networks with realistic topologies (tree, grid-mesh, star-hub) and cascading failure simulation.
4. **Geoprompt integration**: Spatial data preparation, `spatial_weights_matrix`, `network_build`, conformal kriging surfaces, and hotspot detection via the [`geoprompt`](https://pypi.org/project/geoprompt/) package.

## Installation

```bash
pip install -e ".[dev]"
```

Requires Python 3.10+ and PyTorch 2.0+.

## Project Structure

```
src/hetero_conformal/
├── graph.py           # HeteroInfraGraph, synthetic infrastructure generator
├── model.py           # HeteroGNN with typed message passing layers
├── conformal.py       # Split conformal calibration + propagation-aware variant
├── metrics.py         # Coverage, efficiency, calibration error metrics
├── geo_integration.py # Geoprompt hooks: spatial layouts, kriging, hotspots
└── experiment.py      # Train/calibrate/test pipeline and ablation runner

tests/
├── test_graph.py
├── test_model.py
├── test_conformal.py
└── test_metrics.py
```

## Quick Start

```python
from hetero_conformal.experiment import run_experiment, ExperimentConfig

# Run with defaults (90% coverage target)
result = run_experiment()

# Custom configuration
config = ExperimentConfig(
    n_power=300, n_water=200, n_telecom=150,
    hidden_dim=64, num_layers=3,
    alpha=0.1, use_propagation_aware=True,
)
result = run_experiment(config)

print(f"Marginal coverage: {result.marginal_cov:.4f}")
print(f"Per-type coverage: {result.type_cov}")
print(f"Mean interval width: {result.mean_width:.4f}")
```

## Running Tests

```bash
pytest tests/ -v
```

## Ablation Study

```python
from hetero_conformal.experiment import run_ablation_study

results = run_ablation_study(
    alphas=[0.05, 0.1, 0.15, 0.2],
    seeds=[42, 123, 456],
)
```

## Geoprompt Integration

```python
from hetero_conformal.graph import generate_synthetic_infrastructure
from hetero_conformal.geo_integration import (
    build_spatial_layout,
    compute_spatial_weights,
    generate_risk_surface,
    compute_hotspots,
)

graph = generate_synthetic_infrastructure()

# GeoJSON feature collections for each utility layer
layouts = build_spatial_layout(graph)

# Geoprompt spatial weights for neighborhood structure diagnostics
weights = compute_spatial_weights(graph, "power", k=6)

# Conformally-calibrated risk surface via kriging
risk_surface = generate_risk_surface(graph, "power", alpha=0.1)

# Getis-Ord Gi* hotspot detection
hotspots = compute_hotspots(graph, "water")
```

## Method Overview

### Heterogeneous Message Passing

Each message-passing layer applies type-specific weight matrices:

$$h_v^{(l+1)} = \sigma\!\left(W_{\text{self}}^{t_v} h_v^{(l)} + \sum_{(u,r,v) \in \mathcal{E}} \frac{1}{|\mathcal{N}_r(v)|} W_r h_u^{(l)}\right)$$

where $W_r$ is the weight matrix for edge type $r$ and $t_v$ is the node type of $v$.

### Conformal Coverage Guarantee

For each node type $t$ and significance level $\alpha$:

$$\mathbb{P}\!\left(Y_i \in C_t(X_i)\right) \geq 1 - \alpha$$

where $C_t$ uses the finite-sample corrected quantile:

$$\hat{q}_t = \text{Quantile}\!\left(\{s_i\}_{i \in \mathcal{D}_{\text{cal}}^t},\; \frac{\lceil(n_t+1)(1-\alpha)\rceil}{n_t}\right)$$

### Propagation-Aware Calibration

The implemented method uses normalized conformal scores with a frozen neighborhood difficulty term derived from training residuals:

$$s_i = \frac{|y_i - \hat{y}_i|}{\sigma_i}, \quad \sigma_i = 1 + \lambda \cdot \bar{r}_{\mathcal{N}(i)}$$

where $\bar{r}_{\mathcal{N}(i)}$ is the average residual over the training-set neighbors of node $i$. The resulting interval is:

$$C_i = [\hat{y}_i - \hat{q}\,\sigma_i,\; \hat{y}_i + \hat{q}\,\sigma_i]$$

## Citation

```bibtex
@article{powell2025chmp,
  title={Conformalized Message Passing on Heterogeneous Infrastructure Graphs:
         Coverage Guarantees for Interdependent Utility Networks},
  author={Powell, Matthew A.},
  year={2025}
}
```

## License

MIT
