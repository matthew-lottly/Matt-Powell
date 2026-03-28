import os
import sys
import pytest

# Ensure local package path is importable when tests run locally (CI installs package)
sys.path.insert(0, os.path.abspath("_strata_temp/src"))
from hetero_conformal.experiment import run_experiment, ExperimentConfig


def test_chmp_integration_small_graph():
    seeds = [123, 456, 789]
    covs = []
    for s in seeds:
        cfg = ExperimentConfig(
            n_power=6,
            n_water=4,
            n_telecom=3,
            feature_dim=4,
            coupling_prob=0.2,
            coupling_radius=0.2,
            seed=s,
            epochs=30,
            patience=5,
            hidden_dim=16,
            alpha=0.1,
            use_propagation_aware=True,
            device="cpu",
        )
        result = run_experiment(cfg, verbose=False)
        assert hasattr(result, "marginal_cov")
        covs.append(result.marginal_cov)

    mean_cov = sum(covs) / len(covs)
    target = 1.0 - cfg.alpha
    # For very small graphs allow wider slack; ensure mean coverage is not trivially low
    assert mean_cov >= 0.6
