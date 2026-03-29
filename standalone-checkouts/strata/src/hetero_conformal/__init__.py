"""STRATA: Structured Type-Aware Risk Assessment Through Adaptive Calibration."""

from hetero_conformal.graph import HeteroInfraGraph, generate_synthetic_infrastructure
from hetero_conformal.real_data import load_activsg200, load_ieee118
from hetero_conformal.model import HeteroGNN
from hetero_conformal.conformal import HeteroConformalCalibrator, PropagationAwareCalibrator, ConformalResult
from hetero_conformal.metrics import (
    marginal_coverage,
    type_conditional_coverage,
    prediction_set_efficiency,
    mean_interval_width,
    calibration_error,
    rmse_per_type,
    per_type_ece,
)
from hetero_conformal.meta_calibrator import MetaCalibrator
from hetero_conformal.advanced_calibrators import (
    LearnableLambdaCalibrator,
    AttentionCalibrator,
    CQRCalibrator,
)
from hetero_conformal.ensemble import EnsembleHeteroGNN, EnsembleCalibrator
from hetero_conformal.diagnostics import (
    sigma_vs_hitrate,
    conditional_coverage_by_width_decile,
    conditional_coverage_by_degree,
    bootstrap_ci,
    bootstrap_width_ci,
    paired_wilcoxon_test,
    paired_t_test,
    multi_method_friedman_test,
    nonexchangeability_test,
    spatial_autocorrelation_test,
    full_diagnostic_report,
)
from hetero_conformal.streaming import (
    StreamingConformalCalibrator,
    AdaptiveConformalCalibrator,
)
from hetero_conformal.explainability import (
    interval_decomposition,
    calibration_curve_data,
    uncertainty_attribution,
    coverage_by_feature_bin,
)
from hetero_conformal.hyperparam_search import grid_search, random_search

__all__ = [
    # Core data structures
    "HeteroInfraGraph",
    "generate_synthetic_infrastructure",
    "load_activsg200",
    "load_ieee118",
    "HeteroGNN",
    "ConformalResult",
    # Calibrators
    "HeteroConformalCalibrator",
    "PropagationAwareCalibrator",
    "MetaCalibrator",
    "LearnableLambdaCalibrator",
    "AttentionCalibrator",
    "CQRCalibrator",
    "EnsembleHeteroGNN",
    "EnsembleCalibrator",
    # Metrics
    "marginal_coverage",
    "type_conditional_coverage",
    "prediction_set_efficiency",
    "mean_interval_width",
    "calibration_error",
    "rmse_per_type",
    "per_type_ece",
    # Diagnostics
    "sigma_vs_hitrate",
    "conditional_coverage_by_width_decile",
    "conditional_coverage_by_degree",
    "bootstrap_ci",
    "bootstrap_width_ci",
    "paired_wilcoxon_test",
    "paired_t_test",
    "multi_method_friedman_test",
    "nonexchangeability_test",
    "spatial_autocorrelation_test",
    "full_diagnostic_report",
    # Streaming / Online
    "StreamingConformalCalibrator",
    "AdaptiveConformalCalibrator",
    # Explainability
    "interval_decomposition",
    "calibration_curve_data",
    "uncertainty_attribution",
    "coverage_by_feature_bin",
    # Hyperparameter search
    "grid_search",
    "random_search",
]
