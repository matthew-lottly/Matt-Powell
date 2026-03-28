"""Hyperparameter search harness for STRATA experiments.

Supports grid search and random search over ExperimentConfig parameters
with cross-validation or holdout evaluation.
"""

from __future__ import annotations

import itertools
from dataclasses import asdict, fields
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .experiment import ExperimentConfig, run_experiment


def grid_search(
    param_grid: Dict[str, List[Any]],
    base_config: Optional[ExperimentConfig] = None,
    n_seeds: int = 3,
    base_seed: int = 42,
    metric: str = "coverage",
    verbose: bool = True,
) -> Dict[str, Any]:
    """Grid search over hyperparameters.

    Parameters
    ----------
    param_grid : dict
        Mapping from ExperimentConfig field names to lists of values.
        E.g. {"hidden_dim": [32, 64, 128], "num_layers": [2, 3, 4]}
    base_config : ExperimentConfig, optional
        Base configuration to override. Defaults to ExperimentConfig().
    n_seeds : int
        Number of random seeds per configuration.
    metric : str
        Metric to optimize: 'coverage', 'width', 'ece', or 'combined'.
        'combined' minimizes width while maintaining coverage >= 1-alpha-0.02.
    verbose : bool
        Print progress.

    Returns
    -------
    dict with 'best_config', 'best_score', 'all_results'.
    """
    if base_config is None:
        base_config = ExperimentConfig()

    valid_fields = {f.name for f in fields(ExperimentConfig)}
    for key in param_grid:
        if key not in valid_fields:
            raise ValueError(f"Unknown config field: {key}. Valid: {valid_fields}")

    keys = list(param_grid.keys())
    values = list(param_grid.values())
    combos = list(itertools.product(*values))

    all_results: List[Dict[str, Any]] = []
    best_score = float("inf") if metric in ("width", "ece") else float("-inf")
    best_config: Optional[Dict[str, Any]] = None

    for i, combo in enumerate(combos):
        overrides = dict(zip(keys, combo))
        config_dict = asdict(base_config)
        config_dict.update(overrides)
        config = ExperimentConfig(**config_dict)

        seed_metrics: List[Dict[str, float]] = []
        for s in range(n_seeds):
            seed = base_seed + s * 1000
            try:
                # run_experiment does not accept a `seed` kwarg; set on config instead
                config.seed = int(seed)
                result = run_experiment(config=config, verbose=False)
                # ExperimentResult does not expose `metrics` attribute; extract known fields
                seed_metrics.append(
                    {
                        "marginal_coverage": float(getattr(result, "marginal_cov", 0.0) or 0.0),
                        "mean_width": float(getattr(result, "mean_width", 0.0) or 0.0),
                        "ece": float(getattr(result, "ece", 0.0) or 0.0),
                    }
                )
            except Exception as e:
                if verbose:
                    print(f"  Config {i+1}/{len(combos)} seed {s}: FAILED ({e})")
                continue

        if not seed_metrics:
            continue

        avg_coverage = float(np.mean([m.get("marginal_coverage", 0.0) for m in seed_metrics]))
        avg_width = float(np.mean([m.get("mean_width", float("inf")) for m in seed_metrics]))
        avg_ece = float(np.mean([m.get("ece", float("inf")) for m in seed_metrics]))

        entry = {
            "config": overrides,
            "avg_coverage": avg_coverage,
            "avg_width": avg_width,
            "avg_ece": avg_ece,
            "n_seeds": len(seed_metrics),
        }
        all_results.append(entry)

        score = _compute_score(metric, avg_coverage, avg_width, avg_ece, config.alpha)
        is_better = (
            score < best_score if metric in ("width", "ece", "combined")
            else score > best_score
        )
        if is_better:
            best_score = score
            best_config = overrides

        if verbose:
            print(f"  [{i+1}/{len(combos)}] {overrides} → cov={avg_coverage:.3f} "
                  f"width={avg_width:.3f} ece={avg_ece:.4f}")

    return {
        "best_config": best_config,
        "best_score": best_score,
        "all_results": all_results,
        "metric": metric,
    }


def random_search(
    param_distributions: Dict[str, Any],
    base_config: Optional[ExperimentConfig] = None,
    n_iter: int = 20,
    n_seeds: int = 3,
    base_seed: int = 42,
    metric: str = "combined",
    verbose: bool = True,
) -> Dict[str, Any]:
    """Random search over hyperparameters.

    Parameters
    ----------
    param_distributions : dict
        Mapping from field names to either:
        - list of values (sampled uniformly)
        - tuple (low, high) for uniform float sampling
        - tuple (low, high, 'int') for uniform int sampling
        - tuple (low, high, 'log') for log-uniform float sampling
    n_iter : int
        Number of random configurations to try.
    """
    if base_config is None:
        base_config = ExperimentConfig()

    rng = np.random.default_rng(base_seed)
    all_results: List[Dict[str, Any]] = []
    best_score = float("inf") if metric in ("width", "ece", "combined") else float("-inf")
    best_config: Optional[Dict[str, Any]] = None

    for i in range(n_iter):
        overrides = {}
        for key, dist in param_distributions.items():
            if isinstance(dist, list):
                overrides[key] = dist[rng.integers(len(dist))]
            elif isinstance(dist, tuple):
                if len(dist) == 3 and dist[2] == "int":
                    overrides[key] = int(rng.integers(dist[0], dist[1] + 1))
                elif len(dist) == 3 and dist[2] == "log":
                    overrides[key] = float(np.exp(rng.uniform(np.log(dist[0]), np.log(dist[1]))))
                else:
                    overrides[key] = float(rng.uniform(dist[0], dist[1]))

        config_dict = asdict(base_config)
        config_dict.update(overrides)
        config = ExperimentConfig(**config_dict)

        seed_metrics: List[Dict[str, float]] = []
        for s in range(n_seeds):
            seed = base_seed + s * 1000
            try:
                config.seed = int(seed)
                result = run_experiment(config=config, verbose=False)
                seed_metrics.append(
                    {
                        "marginal_coverage": float(getattr(result, "marginal_cov", 0.0) or 0.0),
                        "mean_width": float(getattr(result, "mean_width", 0.0) or 0.0),
                        "ece": float(getattr(result, "ece", 0.0) or 0.0),
                    }
                )
            except Exception:
                continue

        if not seed_metrics:
            continue

        avg_coverage = float(np.mean([m.get("marginal_coverage", 0.0) for m in seed_metrics]))
        avg_width = float(np.mean([m.get("mean_width", float("inf")) for m in seed_metrics]))
        avg_ece = float(np.mean([m.get("ece", float("inf")) for m in seed_metrics]))

        entry = {
            "config": overrides,
            "avg_coverage": avg_coverage,
            "avg_width": avg_width,
            "avg_ece": avg_ece,
            "n_seeds": len(seed_metrics),
        }
        all_results.append(entry)

        score = _compute_score(metric, avg_coverage, avg_width, avg_ece, config.alpha)
        is_better = (
            score < best_score if metric in ("width", "ece", "combined")
            else score > best_score
        )
        if is_better:
            best_score = score
            best_config = overrides

        if verbose:
            print(f"  [{i+1}/{n_iter}] {overrides} → cov={avg_coverage:.3f} "
                  f"width={avg_width:.3f} ece={avg_ece:.4f}")

    return {
        "best_config": best_config,
        "best_score": best_score,
        "all_results": all_results,
        "metric": metric,
    }


def _compute_score(
    metric: str,
    coverage: float,
    width: float,
    ece: float,
    alpha: float,
) -> float:
    """Compute optimization score (lower is better for width/ece/combined)."""
    if metric == "coverage":
        return coverage
    elif metric == "width":
        return width
    elif metric == "ece":
        return ece
    elif metric == "combined":
        target = 1 - alpha
        if coverage < target - 0.02:
            return float("inf")
        return width + 10 * ece
    else:
        raise ValueError(f"Unknown metric: {metric}")
