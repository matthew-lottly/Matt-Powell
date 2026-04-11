# Deployment Guide

Deployment assumptions and operational guidance for STRATA.

## Prerequisites

- Python 3.10+
- PyTorch 2.0+
- NumPy, SciPy
- Geoprompt >= 0.1.7 (for spatial data preparation)

## Installation

```bash
pip install -e .[dev]
```

For GPU acceleration:

```bash
pip install torch --index-url https://download.pytorch.org/whl/cu121
pip install -e .[dev]
```

## Running the Pipeline

Build and evaluate the conformal prediction framework:

```bash
python -m strata.pipeline
```

This runs:
1. Synthetic benchmark generation (heterogeneous infrastructure graph)
2. GNN training with heterogeneous message passing
3. Split conformal calibration with Mondrian per-type coverage
4. Meta-calibrator fitting
5. Evaluation and diagnostic export

## Docker Deployment

```bash
docker build -t strata .
docker run --rm strata python -m strata.pipeline
```

For GPU passthrough:

```bash
docker run --rm --gpus all strata python -m strata.pipeline
```

## Configuration

Key configuration is managed through the pipeline module. Adjustable parameters:

- Graph topology (node types, edge types, connectivity)
- GNN architecture (layers, hidden dimensions, attention heads)
- Conformal calibration (coverage target, score function)
- Meta-calibrator (MLP architecture, training epochs)

## Deployment Assumptions

- The current implementation is a research prototype, not a production service
- The synthetic benchmark demonstrates the methodology — real deployment requires domain-specific graph data
- Conformal coverage guarantees hold under exchangeability assumptions
- GPU is recommended for graphs with more than 1000 nodes

## Monitoring

After deployment, monitor:
- Per-type coverage rates (should meet the target, e.g., 90%)
- Prediction interval widths (narrower is better, conditional on coverage)
- Calibration drift if the graph topology evolves over time
