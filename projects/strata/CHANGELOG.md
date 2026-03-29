# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-12-01

### Added

- Heterogeneous GNN with per-edge-type message passing (`HeteroGNN`, `HeteroMessagePassingLayer`)
- Synthetic infrastructure graph generator (`generate_synthetic_infrastructure`)
- Split conformal calibration with Mondrian per-type guarantees (`HeteroConformalCalibrator`)
- Propagation-aware calibration via CHMP (`PropagationAwareCalibrator`)
- MetaCalibrator: learned per-node normalization via heteroscedastic MLP
- AttentionCalibrator: attention-weighted neighbor difficulty aggregation
- LearnableLambdaCalibrator: per-type grid-search for optimal λ
- CQRCalibrator: conformalized quantile regression with propagation awareness
- EnsembleHeteroGNN and EnsembleCalibrator for epistemic uncertainty decomposition
- Metrics suite: marginal/type-conditional coverage, mean width, ECE, RMSE
- Diagnostics: bootstrap CIs, Wilcoxon/Friedman tests, runs test, Moran's I
- Geoprompt integration: spatial weights, kriging surfaces, Gi* hotspots
- Real-world data loader for ACTIVSg200 200-bus power grid (`load_activsg200`)
- Full benchmark script with 9-stage evaluation pipeline
- 73 tests across 6 test files

### Fixed

- `floor_sigma` logic: floor now applies to neighbor contribution before mixing (was no-op when σ ≥ 1.0)
- CQR quantile head stability: reparameterized upper bound with softplus, increased epochs to 200
