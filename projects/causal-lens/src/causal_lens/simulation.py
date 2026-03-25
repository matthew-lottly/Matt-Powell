"""Monte Carlo simulation study for CausalLens estimators.

Evaluates bias, coverage, RMSE, and mean absolute error across many
replications from known data-generating processes (DGPs). This is the
formal simulation evidence required for a methods paper.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from causal_lens.estimators import (
    CrossFittedDREstimator,
    DoublyRobustEstimator,
    FlexibleDoublyRobustEstimator,
    IPWEstimator,
    PropensityMatcher,
    RegressionAdjustmentEstimator,
)


# ---------------------------------------------------------------------------
# Data-generating processes
# ---------------------------------------------------------------------------

def _dgp_linear(
    n: int, rng: np.random.Generator, treatment_effect: float,
) -> pd.DataFrame:
    """Linear confounding, correct specification for all estimators."""
    x1 = rng.normal(0, 1, n)
    x2 = rng.normal(0, 1, n)
    prop = 1.0 / (1.0 + np.exp(-(0.5 * x1 + 0.3 * x2)))
    treatment = rng.binomial(1, np.clip(prop, 0.05, 0.95), n)
    outcome = 1.0 + 0.8 * x1 + 0.6 * x2 + treatment_effect * treatment + rng.normal(0, 1, n)
    return pd.DataFrame({"x1": x1, "x2": x2, "treatment": treatment, "outcome": outcome})


def _dgp_nonlinear_outcome(
    n: int, rng: np.random.Generator, treatment_effect: float,
) -> pd.DataFrame:
    """Nonlinear outcome model but linear propensity — stresses linear outcome models."""
    x1 = rng.normal(0, 1, n)
    x2 = rng.normal(0, 1, n)
    prop = 1.0 / (1.0 + np.exp(-(0.5 * x1 + 0.3 * x2)))
    treatment = rng.binomial(1, np.clip(prop, 0.05, 0.95), n)
    outcome = 1.0 + 0.5 * x1**2 + np.sin(x2) + treatment_effect * treatment + rng.normal(0, 0.5, n)
    return pd.DataFrame({"x1": x1, "x2": x2, "treatment": treatment, "outcome": outcome})


def _dgp_nonlinear_propensity(
    n: int, rng: np.random.Generator, treatment_effect: float,
) -> pd.DataFrame:
    """Nonlinear propensity model but linear outcome — stresses propensity models."""
    x1 = rng.normal(0, 1, n)
    x2 = rng.normal(0, 1, n)
    prop = 1.0 / (1.0 + np.exp(-(0.3 * x1**2 - 0.5 * x1 * x2 + 0.2 * x2)))
    treatment = rng.binomial(1, np.clip(prop, 0.05, 0.95), n)
    outcome = 1.0 + 0.8 * x1 + 0.6 * x2 + treatment_effect * treatment + rng.normal(0, 1, n)
    return pd.DataFrame({"x1": x1, "x2": x2, "treatment": treatment, "outcome": outcome})


def _dgp_double_nonlinear(
    n: int, rng: np.random.Generator, treatment_effect: float,
) -> pd.DataFrame:
    """Both outcome and propensity are nonlinear — worst case for parametric models."""
    x1 = rng.normal(0, 1, n)
    x2 = rng.normal(0, 1, n)
    prop = 1.0 / (1.0 + np.exp(-(0.3 * x1**2 - 0.5 * x1 * x2 + 0.2 * x2)))
    treatment = rng.binomial(1, np.clip(prop, 0.05, 0.95), n)
    outcome = 1.0 + 0.5 * x1**2 + np.sin(x2) + treatment_effect * treatment + rng.normal(0, 0.5, n)
    return pd.DataFrame({"x1": x1, "x2": x2, "treatment": treatment, "outcome": outcome})


def _dgp_strong_confounding(
    n: int, rng: np.random.Generator, treatment_effect: float,
) -> pd.DataFrame:
    """Strong confounding with near-violation of positivity."""
    x1 = rng.normal(0, 1, n)
    x2 = rng.normal(0, 1, n)
    prop = 1.0 / (1.0 + np.exp(-(1.5 * x1 + 1.2 * x2)))
    treatment = rng.binomial(1, np.clip(prop, 0.02, 0.98), n)
    outcome = 1.0 + 1.5 * x1 + 1.2 * x2 + treatment_effect * treatment + rng.normal(0, 1, n)
    return pd.DataFrame({"x1": x1, "x2": x2, "treatment": treatment, "outcome": outcome})


DGP_REGISTRY: dict[str, Any] = {
    "linear": _dgp_linear,
    "nonlinear_outcome": _dgp_nonlinear_outcome,
    "nonlinear_propensity": _dgp_nonlinear_propensity,
    "double_nonlinear": _dgp_double_nonlinear,
    "strong_confounding": _dgp_strong_confounding,
}


# ---------------------------------------------------------------------------
# RDD and Bunching DGPs (cross-design simulation)
# ---------------------------------------------------------------------------

def _dgp_sharp_rdd(
    n: int, rng: np.random.Generator, treatment_effect: float,
) -> pd.DataFrame:
    """Sharp RD with polynomial outcome and known cutoff effect."""
    running = rng.uniform(-1.0, 1.0, n)
    outcome = (
        1.5 + treatment_effect * (running >= 0.0)
        + 1.5 * running + 0.8 * running ** 2
        + rng.normal(0, 0.5, n)
    )
    return pd.DataFrame({"running": running, "outcome": outcome})


def _dgp_fuzzy_rdd(
    n: int, rng: np.random.Generator, treatment_effect: float,
) -> pd.DataFrame:
    """Fuzzy RD where treatment jumps at cutoff but isn't deterministic."""
    running = rng.uniform(-1.0, 1.0, n)
    treat_prob = np.clip(0.2 + 0.5 * (running >= 0.0) + 0.1 * running, 0.05, 0.95)
    treatment = rng.binomial(1, treat_prob, n).astype(float)
    outcome = 1.0 + treatment_effect * treatment + 1.2 * running + rng.normal(0, 0.6, n)
    return pd.DataFrame({"running": running, "outcome": outcome, "treatment": treatment})


def _dgp_bunching_kink(
    n: int, rng: np.random.Generator, _treatment_effect: float,
) -> pd.DataFrame:
    """Income distribution with bunching at a kink point for elasticity recovery.

    True elasticity is 0.25 with a kink at 50000.
    """
    zstar = 50000.0
    elasticity = 0.25
    t1, t2 = 0.15, 0.25
    ntr = (t2 - t1) / (1.0 - t1)
    dz = elasticity * zstar * ntr

    z0 = rng.uniform(30000, 70000, n)
    z_obs = z0.copy()
    in_region = (z0 > zstar) & (z0 <= zstar + dz)
    z_obs[in_region] = zstar + rng.uniform(-25, 25, int(in_region.sum()))
    z_obs += rng.normal(0, 200, n)

    return pd.DataFrame({"income": z_obs})


RDD_DGP_REGISTRY: dict[str, Any] = {
    "sharp_rdd": _dgp_sharp_rdd,
    "fuzzy_rdd": _dgp_fuzzy_rdd,
    "bunching_kink": _dgp_bunching_kink,
}


def run_rdd_simulation(
    n_replications: int = 100,
    sample_sizes: tuple[int, ...] = (500, 2000),
    true_effect: float = 2.75,
    seed: int = 42,
) -> pd.DataFrame:
    """Monte Carlo simulation for RDD and bunching estimators."""
    from causal_lens.rdd import BunchingEstimator, RegressionDiscontinuity

    rng = np.random.default_rng(seed)
    rows: list[dict] = []

    for dgp_name in ("sharp_rdd", "fuzzy_rdd"):
        dgp_fn = RDD_DGP_REGISTRY[dgp_name]
        for n in sample_sizes:
            for rep in range(n_replications):
                data = dgp_fn(n, rng, true_effect)
                try:
                    if dgp_name == "sharp_rdd":
                        est = RegressionDiscontinuity("running", "outcome", cutoff=0.0, bandwidth=0.4)
                    else:
                        est = RegressionDiscontinuity(
                            "running", "outcome", cutoff=0.0, bandwidth=0.4,
                            treatment_col="treatment",
                        )
                    result = est.fit(data)

                    # Use conventional for sharp, Wald for fuzzy
                    eff = result.effect
                    se = result.se
                    ci_lo = result.ci_low
                    ci_hi = result.ci_high

                    covered = (
                        ci_lo is not None and ci_hi is not None
                        and ci_lo <= true_effect <= ci_hi
                    )

                    # Also record bias-corrected
                    bc_eff = result.bias_corrected_effect
                    r_se = result.robust_se
                    r_lo = result.robust_ci_low
                    r_hi = result.robust_ci_high
                    bc_covered = (
                        r_lo is not None and r_hi is not None
                        and r_lo <= true_effect <= r_hi
                    )

                    rows.append({
                        "dgp": dgp_name, "n": n, "replication": rep,
                        "estimator": "RD_conventional",
                        "estimate": eff, "se": se,
                        "ci_low": ci_lo, "ci_high": ci_hi,
                        "covered": covered, "true_effect": true_effect,
                    })
                    rows.append({
                        "dgp": dgp_name, "n": n, "replication": rep,
                        "estimator": "RD_bias_corrected",
                        "estimate": bc_eff, "se": r_se,
                        "ci_low": r_lo, "ci_high": r_hi,
                        "covered": bc_covered, "true_effect": true_effect,
                    })
                except Exception:
                    for est_name in ("RD_conventional", "RD_bias_corrected"):
                        rows.append({
                            "dgp": dgp_name, "n": n, "replication": rep,
                            "estimator": est_name,
                            "estimate": np.nan, "se": np.nan,
                            "ci_low": np.nan, "ci_high": np.nan,
                            "covered": np.nan, "true_effect": true_effect,
                        })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Estimator factory
# ---------------------------------------------------------------------------

def _build_estimators(confounders: list[str], bootstrap_repeats: int) -> list[tuple[str, Any]]:
    """Build all estimators for a simulation run."""
    return [
        ("Regression", RegressionAdjustmentEstimator(
            "treatment", "outcome", confounders, bootstrap_repeats=bootstrap_repeats,
        )),
        ("Matching", PropensityMatcher(
            "treatment", "outcome", confounders, caliper=0.2, bootstrap_repeats=bootstrap_repeats,
        )),
        ("IPW", IPWEstimator(
            "treatment", "outcome", confounders, bootstrap_repeats=bootstrap_repeats,
        )),
        ("DR", DoublyRobustEstimator(
            "treatment", "outcome", confounders, bootstrap_repeats=bootstrap_repeats,
        )),
        ("CrossFitDR", CrossFittedDREstimator(
            "treatment", "outcome", confounders, bootstrap_repeats=bootstrap_repeats,
        )),
        ("FlexibleDR", FlexibleDoublyRobustEstimator(
            "treatment", "outcome", confounders, bootstrap_repeats=bootstrap_repeats,
        )),
    ]


# ---------------------------------------------------------------------------
# Core simulation runner
# ---------------------------------------------------------------------------

@dataclass
class SimulationConfig:
    """Configuration for a Monte Carlo simulation run."""
    n_replications: int = 500
    sample_sizes: tuple[int, ...] = (200, 500, 1000)
    true_effect: float = 2.0
    bootstrap_repeats: int = 20
    confounders: tuple[str, ...] = ("x1", "x2")
    dgp_names: tuple[str, ...] | None = None
    seed: int = 42


def run_simulation(config: SimulationConfig | None = None) -> pd.DataFrame:
    """Run the full Monte Carlo simulation study.

    For each DGP × sample size × replication, fits all estimators and
    records the point estimate, SE, CI, and whether the CI covers the
    true effect.
    """
    if config is None:
        config = SimulationConfig()

    dgp_names = list(config.dgp_names) if config.dgp_names else list(DGP_REGISTRY.keys())
    confounders = list(config.confounders)
    rng = np.random.default_rng(config.seed)
    rows: list[dict] = []

    for dgp_name in dgp_names:
        dgp_fn = DGP_REGISTRY[dgp_name]
        for n in config.sample_sizes:
            for rep in range(config.n_replications):
                data = dgp_fn(n, rng, config.true_effect)
                estimators = _build_estimators(confounders, config.bootstrap_repeats)
                for est_name, est in estimators:
                    try:
                        result = est.fit(data)
                        covered = (
                            result.ci_low is not None
                            and result.ci_high is not None
                            and result.ci_low <= config.true_effect <= result.ci_high
                        )
                        rows.append({
                            "dgp": dgp_name,
                            "n": n,
                            "replication": rep,
                            "estimator": est_name,
                            "estimate": result.effect,
                            "se": result.se,
                            "ci_low": result.ci_low,
                            "ci_high": result.ci_high,
                            "covered": covered,
                            "true_effect": config.true_effect,
                        })
                    except Exception:
                        rows.append({
                            "dgp": dgp_name,
                            "n": n,
                            "replication": rep,
                            "estimator": est_name,
                            "estimate": np.nan,
                            "se": np.nan,
                            "ci_low": np.nan,
                            "ci_high": np.nan,
                            "covered": np.nan,
                            "true_effect": config.true_effect,
                        })

    return pd.DataFrame(rows)


def summarize_simulation(raw: pd.DataFrame) -> pd.DataFrame:
    """Summarize Monte Carlo results: bias, RMSE, coverage, MAE."""
    raw = raw.dropna(subset=["estimate"])
    raw = raw.copy()
    raw["bias"] = raw["estimate"] - raw["true_effect"]
    raw["sq_error"] = raw["bias"] ** 2
    raw["abs_error"] = raw["bias"].abs()

    summary = raw.groupby(["dgp", "n", "estimator"]).agg(
        mean_estimate=("estimate", "mean"),
        bias=("bias", "mean"),
        rmse=("sq_error", lambda x: float(np.sqrt(x.mean()))),
        mae=("abs_error", "mean"),
        coverage=("covered", "mean"),
        mean_se=("se", "mean"),
        empirical_se=("estimate", "std"),
        n_reps=("estimate", "count"),
    ).reset_index()

    # SE calibration ratio: mean reported SE / empirical SE
    summary["se_ratio"] = summary["mean_se"] / summary["empirical_se"]

    return summary


def export_simulation_artifacts(
    output_dir: Path,
    config: SimulationConfig | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run simulation and export raw + summary CSV files."""
    tables_dir = output_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)

    raw = run_simulation(config)
    raw.to_csv(tables_dir / "monte_carlo_raw.csv", index=False)

    summary = summarize_simulation(raw)
    summary.to_csv(tables_dir / "monte_carlo_summary.csv", index=False)

    return raw, summary


def run_quick_simulation() -> pd.DataFrame:
    """Run a fast simulation with fewer reps for testing."""
    config = SimulationConfig(
        n_replications=20,
        sample_sizes=(200, 500),
        bootstrap_repeats=10,
        dgp_names=("linear", "nonlinear_outcome"),
    )
    return run_simulation(config)


def main() -> None:
    output_dir = Path(__file__).resolve().parents[2] / "outputs"
    print("Running Monte Carlo simulation study...")
    print("This will take a while with default settings.")
    print("Use SimulationConfig(n_replications=50) for a faster run.\n")

    config = SimulationConfig(n_replications=200, bootstrap_repeats=15)
    raw, summary = export_simulation_artifacts(output_dir, config)

    print("=== Monte Carlo Summary ===\n")
    for dgp in summary["dgp"].unique():
        print(f"--- DGP: {dgp} ---")
        sub = summary[summary["dgp"] == dgp]
        for _, row in sub.iterrows():
            print(
                f"  n={int(row['n']):>5d}  {row['estimator']:15s}  "
                f"bias={row['bias']:>7.3f}  RMSE={row['rmse']:>6.3f}  "
                f"coverage={row['coverage']:>5.1%}  SE_ratio={row['se_ratio']:>5.2f}"
            )
        print()

    print(f"Raw results: {output_dir / 'tables' / 'monte_carlo_raw.csv'}")
    print(f"Summary:     {output_dir / 'tables' / 'monte_carlo_summary.csv'}")


if __name__ == "__main__":
    main()
