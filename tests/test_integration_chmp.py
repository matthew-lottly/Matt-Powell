import os
import sys
import pytest

# Ensure local package path is importable when tests run locally (CI installs package)
sys.path.insert(0, os.path.abspath("_strata_temp/src"))
from hetero_conformal.experiment import run_experiment, ExperimentConfig


def test_chmp_integration_small_graph():
    cfg = ExperimentConfig(
        n_power=6,
        n_water=4,
        n_telecom=3,
        feature_dim=4,
        coupling_prob=0.2,
        coupling_radius=0.2,
        seed=123,
        epochs=30,
        patience=5,
        hidden_dim=16,
        alpha=0.1,
        use_propagation_aware=True,
        device="cpu",
    )

    result = run_experiment(cfg, verbose=False)
    assert hasattr(result, "marginal_cov")
    # Conformal validity: marginal coverage should be near target (1-alpha).
    target = 1.0 - cfg.alpha
    assert 0.7 <= result.marginal_cov <= 1.0
