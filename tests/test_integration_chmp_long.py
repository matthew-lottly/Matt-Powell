import os
import sys
import pytest

sys.path.insert(0, os.path.abspath("_strata_temp/src"))
from hetero_conformal.experiment import run_experiment, ExperimentConfig


@pytest.mark.skipif(os.environ.get('RUN_LONG_TESTS') != '1', reason='Long integration tests disabled')
def test_chmp_integration_long():
    seeds = list(range(100, 110))
    covs = []
    for s in seeds:
        cfg = ExperimentConfig(seed=s, epochs=50, patience=10, device='cpu')
        result = run_experiment(cfg, verbose=False)
        covs.append(result.marginal_cov)

    mean_cov = sum(covs) / len(covs)
    assert mean_cov >= 0.85
