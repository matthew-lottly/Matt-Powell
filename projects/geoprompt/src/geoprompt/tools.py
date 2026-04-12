from __future__ import annotations

import math
import random
import statistics
import time
from typing import Any, Callable, Sequence

from .equations import (
    exponential_decay,
    gaussian_decay,
    prompt_decay,
)

try:
    import numpy as _np
except ImportError:  # pragma: no cover - optional dependency
    _np = None


def _validate_observed_pairs(observed_pairs: Sequence[tuple[float, float]]) -> tuple[list[float], list[float]]:
    if not observed_pairs:
        raise ValueError("observed_pairs must not be empty")

    distances: list[float] = []
    observed: list[float] = []
    for distance, value in observed_pairs:
        distance_float = float(distance)
        value_float = float(value)
        if distance_float < 0:
            raise ValueError("observed distances must be zero or greater")
        if math.isnan(distance_float) or math.isnan(value_float):
            raise ValueError("observed_pairs must not contain NaN values")
        distances.append(distance_float)
        observed.append(value_float)
    return distances, observed


def _rmse(predicted: list[float], observed: list[float]) -> float:
    mse = sum((p - o) ** 2 for p, o in zip(predicted, observed)) / len(observed)
    return mse ** 0.5


def _predict_decay_values(
    distances: Sequence[float],
    method: str,
    *,
    scale: float = 1.0,
    power: float = 2.0,
    rate: float = 1.0,
    sigma: float = 1.0,
) -> list[float]:
    if method == "power":
        return [prompt_decay(distance, scale=scale, power=power) for distance in distances]
    if method == "exponential":
        return [exponential_decay(distance, rate=rate) for distance in distances]
    if method == "gaussian":
        return [gaussian_decay(distance, sigma=sigma) for distance in distances]
    raise ValueError("method must be one of: power, exponential, gaussian")


def calibrate_decay_parameters(
    observed_pairs: Sequence[tuple[float, float]],
    method: str = "power",
    scale_candidates: Sequence[float] | None = None,
    power_candidates: Sequence[float] | None = None,
    rate_candidates: Sequence[float] | None = None,
    sigma_candidates: Sequence[float] | None = None,
) -> dict[str, float]:
    """Grid-search calibration for decay models using RMSE."""
    distances, observed = _validate_observed_pairs(observed_pairs)

    scale_grid = list(scale_candidates or [0.1, 0.25, 0.5, 1.0, 2.0, 5.0])
    power_grid = list(power_candidates or [1.0, 1.5, 2.0, 2.5, 3.0])
    rate_grid = list(rate_candidates or [0.1, 0.25, 0.5, 1.0, 2.0])
    sigma_grid = list(sigma_candidates or [0.1, 0.25, 0.5, 1.0, 2.0])

    best_rmse = float("inf")
    best: dict[str, float] = {"rmse": best_rmse}

    if method == "power":
        for scale in scale_grid:
            for power in power_grid:
                preds = _predict_decay_values(distances, method, scale=scale, power=power)
                rmse = _rmse(preds, observed)
                if rmse < best_rmse:
                    best_rmse = rmse
                    best = {"rmse": rmse, "scale": float(scale), "power": float(power)}
    elif method == "exponential":
        for rate in rate_grid:
            preds = _predict_decay_values(distances, method, rate=rate)
            rmse = _rmse(preds, observed)
            if rmse < best_rmse:
                best_rmse = rmse
                best = {"rmse": rmse, "rate": float(rate)}
    elif method == "gaussian":
        for sigma in sigma_grid:
            preds = _predict_decay_values(distances, method, sigma=sigma)
            rmse = _rmse(preds, observed)
            if rmse < best_rmse:
                best_rmse = rmse
                best = {"rmse": rmse, "sigma": float(sigma)}
    else:
        raise ValueError("method must be one of: power, exponential, gaussian")

    return best


def optimize_decay_parameters(
    observed_pairs: Sequence[tuple[float, float]],
    method: str = "power",
    refinement_steps: int = 12,
) -> dict[str, float]:
    """Refine decay parameters beyond the coarse grid search.

    Uses a small coordinate-descent style local search so it stays dependency-free.
    """
    if refinement_steps <= 0:
        raise ValueError("refinement_steps must be greater than zero")

    distances, observed = _validate_observed_pairs(observed_pairs)
    current = calibrate_decay_parameters(observed_pairs, method=method)

    if method == "power":
        scale = float(current["scale"])
        power = float(current["power"])
        scale_step = max(0.01, scale * 0.5)
        power_step = max(0.05, power * 0.5)
        best_rmse = float(current["rmse"])
        for _ in range(refinement_steps):
            scale_candidates = [max(1e-6, scale + scale_step * offset / 3.0) for offset in range(-3, 4)]
            power_candidates = [max(1e-6, power + power_step * offset / 3.0) for offset in range(-3, 4)]
            improved = False
            for candidate_scale in scale_candidates:
                for candidate_power in power_candidates:
                    if candidate_scale == scale and candidate_power == power:
                        continue
                    preds = _predict_decay_values(distances, method, scale=candidate_scale, power=candidate_power)
                    rmse = _rmse(preds, observed)
                    if rmse < best_rmse:
                        scale = candidate_scale
                        power = candidate_power
                        best_rmse = rmse
                        improved = True
            if not improved:
                scale_step *= 0.5
                power_step *= 0.5
            else:
                scale_step *= 0.8
                power_step *= 0.8
            if scale_step < 1e-6 and power_step < 1e-6:
                break
        return {"rmse": best_rmse, "scale": scale, "power": power}

    if method == "exponential":
        rate = float(current["rate"])
        rate_step = max(0.01, rate * 0.5)
        best_rmse = float(current["rmse"])
        for _ in range(refinement_steps):
            candidates = [max(1e-6, rate + rate_step * offset / 3.0) for offset in range(-3, 4)]
            improved = False
            for candidate_rate in candidates:
                if candidate_rate == rate:
                    continue
                preds = _predict_decay_values(distances, method, rate=candidate_rate)
                rmse = _rmse(preds, observed)
                if rmse < best_rmse:
                    rate = candidate_rate
                    best_rmse = rmse
                    improved = True
            rate_step *= 0.5 if not improved else 0.8
            if rate_step < 1e-6:
                break
        return {"rmse": best_rmse, "rate": rate}

    if method == "gaussian":
        sigma = float(current["sigma"])
        sigma_step = max(0.01, sigma * 0.5)
        best_rmse = float(current["rmse"])
        for _ in range(refinement_steps):
            candidates = [max(1e-6, sigma + sigma_step * offset / 3.0) for offset in range(-3, 4)]
            improved = False
            for candidate_sigma in candidates:
                if candidate_sigma == sigma:
                    continue
                preds = _predict_decay_values(distances, method, sigma=candidate_sigma)
                rmse = _rmse(preds, observed)
                if rmse < best_rmse:
                    sigma = candidate_sigma
                    best_rmse = rmse
                    improved = True
            sigma_step *= 0.5 if not improved else 0.8
            if sigma_step < 1e-6:
                break
        return {"rmse": best_rmse, "sigma": sigma}

    raise ValueError("method must be one of: power, exponential, gaussian")


def compare_scenarios(
    baseline_metrics: dict[str, float],
    candidate_metrics: dict[str, float],
    higher_is_better: Sequence[str] | None = None,
) -> dict[str, dict[str, float | str]]:
    """Compute absolute and percent deltas for scenario metrics."""
    preferred = set(higher_is_better or [])
    keys = sorted(set(baseline_metrics) | set(candidate_metrics))
    results: dict[str, dict[str, float | str]] = {}

    for key in keys:
        baseline = float(baseline_metrics.get(key, 0.0))
        candidate = float(candidate_metrics.get(key, 0.0))
        delta = candidate - baseline
        pct = 0.0 if baseline == 0 else (delta / abs(baseline)) * 100.0
        if key in preferred:
            direction = "improved" if delta >= 0 else "worsened"
        else:
            direction = "improved" if delta <= 0 else "worsened"
        results[key] = {
            "baseline": baseline,
            "candidate": candidate,
            "delta": delta,
            "delta_percent": pct,
            "direction": direction,
        }

    return results


def sensitivity_analysis(
    model: Callable[..., float],
    base_parameters: dict[str, float],
    variation_fraction: float = 0.2,
) -> list[dict[str, float | str]]:
    """One-at-a-time sensitivity analysis around a baseline parameter set."""
    if variation_fraction <= 0:
        raise ValueError("variation_fraction must be greater than zero")

    baseline_value = float(model(**base_parameters))
    rows: list[dict[str, float | str]] = []

    for key, value in base_parameters.items():
        value = float(value)
        lower = value * (1.0 - variation_fraction)
        upper = value * (1.0 + variation_fraction)

        params_low = dict(base_parameters)
        params_high = dict(base_parameters)
        params_low[key] = lower
        params_high[key] = upper

        low_value = float(model(**params_low))
        high_value = float(model(**params_high))
        rows.append(
            {
                "parameter": key,
                "baseline_output": baseline_value,
                "low_output": low_value,
                "high_output": high_value,
                "sensitivity_span": abs(high_value - low_value),
            }
        )

    rows.sort(key=lambda item: -float(item["sensitivity_span"]))
    return rows


def monte_carlo_interval(
    model: Callable[..., float],
    parameter_bounds: dict[str, tuple[float, float]],
    iterations: int = 1000,
    seed: int = 42,
) -> dict[str, float]:
    """Monte Carlo simulation returning percentile intervals for model output."""
    if iterations <= 0:
        raise ValueError("iterations must be greater than zero")
    if not parameter_bounds:
        raise ValueError("parameter_bounds must not be empty")

    rng = random.Random(seed)
    values: list[float] = []

    for _ in range(iterations):
        params: dict[str, float] = {}
        for name, (low, high) in parameter_bounds.items():
            if high < low:
                raise ValueError(f"invalid bounds for {name}: high must be >= low")
            params[name] = rng.uniform(float(low), float(high))
        values.append(float(model(**params)))

    values.sort()
    p10_index = int(0.10 * (len(values) - 1))
    p50_index = int(0.50 * (len(values) - 1))
    p90_index = int(0.90 * (len(values) - 1))

    return {
        "mean": float(statistics.fmean(values)),
        "p10": float(values[p10_index]),
        "p50": float(values[p50_index]),
        "p90": float(values[p90_index]),
        "min": float(values[0]),
        "max": float(values[-1]),
    }


def bootstrap_confidence_interval(
    values: Sequence[float],
    confidence_level: float = 0.95,
    iterations: int = 1000,
    statistic: Callable[[Sequence[float]], float] | None = None,
    seed: int = 42,
) -> dict[str, float]:
    """Bootstrap confidence interval for a sample statistic."""
    if not values:
        raise ValueError("values must not be empty")
    if iterations <= 0:
        raise ValueError("iterations must be greater than zero")
    if not 0.0 < confidence_level < 1.0:
        raise ValueError("confidence_level must be in (0, 1)")

    stat_func = statistic or (lambda sample: float(statistics.fmean(sample)))
    cleaned = [float(value) for value in values]
    rng = random.Random(seed)
    stats: list[float] = []
    for _ in range(iterations):
        sample = [cleaned[rng.randrange(len(cleaned))] for _ in range(len(cleaned))]
        stats.append(float(stat_func(sample)))
    stats.sort()

    alpha = (1.0 - confidence_level) / 2.0
    lower_index = int(alpha * (len(stats) - 1))
    upper_index = int((1.0 - alpha) * (len(stats) - 1))
    observed = float(stat_func(cleaned))
    return {
        "observed": observed,
        "lower": float(stats[lower_index]),
        "upper": float(stats[upper_index]),
        "confidence_level": confidence_level,
    }


def build_scenario_report(
    baseline_metrics: dict[str, float],
    candidate_metrics: dict[str, float],
    *,
    baseline_name: str = "baseline",
    candidate_name: str = "candidate",
    higher_is_better: Sequence[str] | None = None,
    uncertainty: dict[str, dict[str, float]] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a compact machine-friendly scenario comparison report."""
    metric_comparison = compare_scenarios(
        baseline_metrics,
        candidate_metrics,
        higher_is_better=higher_is_better,
    )
    improved = [name for name, item in metric_comparison.items() if item["direction"] == "improved"]
    worsened = [name for name, item in metric_comparison.items() if item["direction"] == "worsened"]
    return {
        "baseline_name": baseline_name,
        "candidate_name": candidate_name,
        "metadata": dict(metadata or {}),
        "summary": {
            "metric_count": len(metric_comparison),
            "improved_metrics": improved,
            "worsened_metrics": worsened,
        },
        "metrics": metric_comparison,
        "uncertainty": dict(uncertainty or {}),
    }


def vectorized_decay(
    distance_values: Sequence[float],
    method: str = "power",
    *,
    scale: float = 1.0,
    power: float = 2.0,
    rate: float = 1.0,
    sigma: float = 1.0,
) -> list[float]:
    """Evaluate decay over many distances, using NumPy when available."""
    cleaned = [float(value) for value in distance_values]
    if any(value < 0 for value in cleaned):
        raise ValueError("distance_values must be zero or greater")

    if _np is None:
        return _predict_decay_values(cleaned, method, scale=scale, power=power, rate=rate, sigma=sigma)

    arr = _np.asarray(cleaned, dtype=float)
    if method == "power":
        if scale <= 0 or power <= 0:
            raise ValueError("scale and power must be greater than zero")
        return [float(value) for value in _np.power(1.0 + arr / scale, -power).tolist()]
    if method == "exponential":
        if rate <= 0:
            raise ValueError("rate must be greater than zero")
        return [float(value) for value in _np.exp(-rate * arr).tolist()]
    if method == "gaussian":
        if sigma <= 0:
            raise ValueError("sigma must be greater than zero")
        return [float(value) for value in _np.exp(-(arr**2) / (2.0 * sigma**2)).tolist()]
    raise ValueError("method must be one of: power, exponential, gaussian")


def validate_numeric_series(
    values: Sequence[float],
    *,
    name: str = "values",
    min_value: float | None = None,
    max_value: float | None = None,
    allow_nan: bool = False,
) -> list[float]:
    """Validate numeric sequences for downstream modeling and reporting."""
    cleaned: list[float] = []
    for raw in values:
        value = float(raw)
        if math.isnan(value):
            if allow_nan:
                cleaned.append(value)
                continue
            raise ValueError(f"{name} must not contain NaN values")
        if min_value is not None and value < min_value:
            raise ValueError(f"{name} values must be >= {min_value}")
        if max_value is not None and value > max_value:
            raise ValueError(f"{name} values must be <= {max_value}")
        cleaned.append(value)
    return cleaned


_DISTANCE_FACTORS: dict[tuple[str, str], float] = {
    ("m", "km"): 0.001,
    ("km", "m"): 1000.0,
    ("m", "mi"): 1.0 / 1609.344,
    ("mi", "m"): 1609.344,
    ("km", "mi"): 1.0 / 1.609344,
    ("mi", "km"): 1.609344,
}

_FLOW_FACTORS: dict[tuple[str, str], float] = {
    ("gpm", "lps"): 0.0630902,
    ("lps", "gpm"): 1.0 / 0.0630902,
    ("m3s", "lps"): 1000.0,
    ("lps", "m3s"): 0.001,
}


def normalize_units(value: float, from_unit: str, to_unit: str, quantity: str = "distance") -> float:
    """Normalize values across supported distance and flow units."""
    if from_unit == to_unit:
        return float(value)

    if quantity == "distance":
        factor = _DISTANCE_FACTORS.get((from_unit, to_unit))
    elif quantity == "flow":
        factor = _FLOW_FACTORS.get((from_unit, to_unit))
    else:
        raise ValueError("quantity must be 'distance' or 'flow'")

    if factor is None:
        raise ValueError(f"unsupported conversion: {quantity} {from_unit} -> {to_unit}")

    return float(value) * factor


def benchmark_function(
    func: Callable[..., Any],
    *args: Any,
    repeats: int = 5,
    **kwargs: Any,
) -> dict[str, float]:
    """Small benchmark helper returning min/max/mean runtime in seconds."""
    if repeats <= 0:
        raise ValueError("repeats must be greater than zero")

    durations: list[float] = []
    for _ in range(repeats):
        started = time.perf_counter()
        func(*args, **kwargs)
        durations.append(time.perf_counter() - started)

    return {
        "runs": float(repeats),
        "min_seconds": min(durations),
        "max_seconds": max(durations),
        "mean_seconds": float(statistics.fmean(durations)),
    }


__all__ = [
    "benchmark_function",
    "bootstrap_confidence_interval",
    "build_scenario_report",
    "calibrate_decay_parameters",
    "compare_scenarios",
    "monte_carlo_interval",
    "normalize_units",
    "optimize_decay_parameters",
    "sensitivity_analysis",
    "validate_numeric_series",
    "vectorized_decay",
]
