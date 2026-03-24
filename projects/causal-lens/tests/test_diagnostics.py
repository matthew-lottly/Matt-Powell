from __future__ import annotations

import numpy as np

from causal_lens.diagnostics import standardized_mean_difference, summarize_overlap
from causal_lens.synthetic import generate_synthetic_observational_data


def test_standardized_mean_difference_returns_covariate_keys() -> None:
    dataset = generate_synthetic_observational_data(rows=200, seed=5)
    summary = standardized_mean_difference(
        dataset,
        treatment_col="treatment",
        covariates=["age", "severity", "baseline_score"],
    )
    assert set(summary) == {"age", "severity", "baseline_score"}


def test_overlap_summary_flags_overlap() -> None:
    propensity = np.array([0.2, 0.4, 0.6, 0.8], dtype=float)
    treatment = np.array([0, 1, 0, 1], dtype=int)
    summary = summarize_overlap(propensity, treatment)
    assert summary["overlap_ok"] is True
    assert summary["propensity_min"] == 0.2
