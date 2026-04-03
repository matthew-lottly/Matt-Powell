# STRATA

**Structured Type-Aware Risk Assessment Through Adaptive Calibration on Heterogeneous Infrastructure Graphs**

## Review Artifacts

- Example output: [EXAMPLE_OUTPUT.md](EXAMPLE_OUTPUT.md)
- Data-flow diagram: [docs/data-flow.md](docs/data-flow.md)
- Runbook: [docs/runbook.md](docs/runbook.md)

## Abstract

STRATA introduces *Conformalized Heterogeneous Message Passing* (CHMP), a framework that combines heterogeneous graph neural networks with split conformal prediction to produce uncertainty-quantified risk predictions across coupled infrastructure systems (power, water, telecom). Unlike existing conformal prediction methods for graphs—which assume homogeneous node/edge types—CHMP provides Mondrian-style per-type coverage guarantees on heterogeneous graphs, and introduces a suite of propagation-aware calibration schemes that account for multi-hop error propagation across utility boundaries.

The reviewer-facing story is therefore not just predictive accuracy. It is whether the method produces calibrated uncertainty that remains interpretable when the graph contains multiple infrastructure types with different failure behavior and coupling patterns.

## Key Contributions

1. **Heterogeneous conformal calibration**: Mondrian grouping by infrastructure type yields per-type coverage guarantees (Theorem 1).
2. **Propagation-aware nonconformity scores**: Neighborhood-aggregated residuals account for how message passing propagates errors across coupled layers, producing tighter intervals while maintaining coverage.
3. **Meta-calibrator**: A learned per-node σ_i via MLP trained with heteroscedastic Gaussian NLL, achieving data-driven calibration factors that adapt to local graph structure.
4. **Advanced calibrator variants**: Learnable per-type λ, attention-weighted neighbor difficulty aggregation, and conformalized quantile regression (CQR) with propagation.
5. **Ensemble uncertainty decomposition**: Epistemic uncertainty via prediction variance across an ensemble of GNN model members.
6. **Comprehensive diagnostics**: Bootstrap confidence intervals, Wilcoxon/Friedman significance tests, non-exchangeability detection (runs test), Moran's I spatial autocorrelation, and conditional coverage analysis.
7. **Synthetic benchmark**: A configurable generator for coupled power/water/telecom networks with realistic topologies (tree, grid-mesh, star-hub) and cascading failure simulation.
8. **Geoprompt integration**: Spatial data preparation, `spatial_weights_matrix`, `network_build`, conformal kriging surfaces, and hotspot detection via the [`geoprompt`](https://pypi.org/project/geoprompt/) package.

## Installation

```bash
pip install -e ".[dev]"
```

Requires Python 3.10+ and PyTorch 2.0+.

## Project Structure

```
src/hetero_conformal/
├── graph.py               # HeteroInfraGraph, synthetic infrastructure generator
├── model.py               # HeteroGNN with typed message passing layers
├── conformal.py           # Split conformal calibration + propagation-aware variant
├── meta_calibrator.py     # MetaCalibrator: learned per-node σ_i via MLP
├── advanced_calibrators.py# Learnable λ, attention, CQR calibrators
├── ensemble.py            # Ensemble GNN + variance-based calibration
├── metrics.py             # Coverage, efficiency, calibration error metrics
├── diagnostics.py         # Bootstrap CIs, statistical tests, non-exchangeability
├── geo_integration.py     # Geoprompt hooks: spatial layouts, kriging, hotspots
├── real_data.py           # ACTIVSg200 real power-grid loader + adapter
└── experiment.py          # Train/calibrate/test pipeline and ablation runner

scripts/
├── run_benchmark.py       # Full 9-step benchmark suite
├── run_lambda_only.py     # Lambda sensitivity sweep
└── plot_paper_figures.py  # Publication-ready figures (PDF/SVG)

tests/
├── test_graph.py
├── test_model.py
├── test_conformal.py
├── test_metrics.py
├── test_advanced.py       # Advanced calibrator tests
└── test_real_data.py      # Real data integration tests

data/
└── case_ACTIVSg200.m      # Illinois 200-bus synthetic grid (MATPOWER format)
```

## Quick Start

```python
from hetero_conformal.experiment import run_experiment, ExperimentConfig

Reproducibility notes:
- Put benchmark CSV outputs into `projects/strata/outputs/` (the workflow and paper scripts read this folder).
- The repository includes a CI workflow that runs tests and generates the paper tables on push/PR: see `.github/workflows/ci.yml`.

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

## Real-Data Benchmarks

STRATA now includes two public MATPOWER-derived benchmarks:

- `load_activsg200()` for the 200-bus Central Illinois case
- `load_ieee118()` for the IEEE 118-bus transmission case

Run the real-data benchmark script to compare both:

```bash
d:/GitHub/.venv/Scripts/python.exe scripts/run_real_data_benchmark.py
d:/GitHub/.venv/Scripts/python.exe scripts/run_real_method_comparison.py
```

## Fairness, Profiling, Dashboard, and API

```bash
d:/GitHub/.venv/Scripts/python.exe scripts/fairness_audit.py
d:/GitHub/.venv/Scripts/python.exe scripts/profile_benchmark.py
d:/GitHub/.venv/Scripts/python.exe scripts/run_ablations.py
d:/GitHub/.venv/Scripts/python.exe scripts/build_submission_bundle.py
```

Optional extras:

```bash
pip install -e ".[dashboard,api,release]"
streamlit run dashboard/app.py
d:/GitHub/.venv/Scripts/python.exe scripts/serve_api.py
python -m build
python -m twine check dist/*
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
@article{powell2025strata,
  title={STRATA: Structured Type-Aware Risk Assessment Through Adaptive
         Calibration on Heterogeneous Infrastructure Graphs},
  author={Powell, Matthew A.},
  year={2025}
}
```

## License

MIT

## Deployment Notes

See [docs/deployment-guide.md](docs/deployment-guide.md) for the current deployment assumptions, GPU expectations, and packaging path for a reviewable STRATA environment.
