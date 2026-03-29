from __future__ import annotations

import numpy as np
import pandas as pd


def generate_synthetic_observational_data(
    rows: int = 600,
    seed: int = 42,
    treatment_effect: float = 2.0,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    age = rng.normal(loc=50.0, scale=12.0, size=rows)
    severity = rng.normal(loc=0.0, scale=1.0, size=rows)
    baseline = rng.normal(loc=10.0, scale=2.5, size=rows)
    propensity_linear = -1.2 + 0.025 * age + 0.9 * severity + 0.08 * baseline
    propensity = 1.0 / (1.0 + np.exp(-propensity_linear))
    treatment = rng.binomial(n=1, p=np.clip(propensity, 0.05, 0.95))
    noise = rng.normal(loc=0.0, scale=1.0, size=rows)
    outcome = 5.0 + 0.35 * age + 1.4 * severity + 0.55 * baseline + treatment_effect * treatment + noise
    return pd.DataFrame(
        {
            "age": age,
            "severity": severity,
            "baseline_score": baseline,
            "treatment": treatment.astype(int),
            "outcome": outcome,
        }
    )
