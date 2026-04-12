from __future__ import annotations

import random
import statistics
import time
from typing import Any, Callable, Sequence

from .equations import (
    exponential_decay,
    gaussian_decay,
    prompt_decay,
)


def calibrate_decay_parameters(
    observed_pairs: Sequence[tuple[float, float]],
    method: str = "power",
    scale_candidates: Sequence[float] | None = None,
    power_candidates: Sequence[float] | None = None,
    rate_candidates: Sequence[float] | None = None,
    sigma_candidates: Sequence[float] | None = None,
) -> dict[str, float]:
    """Grid-search calibration for decay models using RMSE."""
    if not observed_pairs:
        raise ValueError("observed_pairs must not be empty")

    scale_grid = list(scale_candidates or [0.1, 0.25, 0.5, 1.0, 2.0, 5.0])
    power_grid = list(power_candidates or [1.0, 1.5, 2.0, 2.5, 3.0])
    rate_grid = list(rate_candidates or [0.1, 0.25, 0.5, 1.0, 2.0])
    sigma_grid = list(sigma_candidates or [0.1, 0.25, 0.5, 1.0, 2.0])

    best_rmse = float("inf")
    best: dict[str, float] = {"rmse": best_rmse}

    def _rmse(predicted: list[float], observed: list[float]) -> float:
        mse = sum((p - o) ** 2 for p, o in zip(predicted, observed)) / len(observed)
        return mse ** 0.5

    distances = [float(distance) for distance, _ in observed_pairs]
    observed = [float(value) for _, value in observed_pairs]

    if method == "power":
        for scale in scale_grid:
            for power in power_grid:
                preds = [prompt_decay(distance, scale=scale, power=power) for distance in distances]
                rmse = _rmse(preds, observed)
                if rmse < best_rmse:
                    best_rmse = rmse
                    best = {"rmse": rmse, "scale": float(scale), "power": float(power)}
    elif method == "exponential":
        for rate in rate_grid:
            preds = [exponential_decay(distance, rate=rate) for distance in distances]
            rmse = _rmse(preds, observed)
            if rmse < best_rmse:
                best_rmse = rmse
                best = {"rmse": rmse, "rate": float(rate)}
    elif method == "gaussian":
        for sigma in sigma_grid:
            preds = [gaussian_decay(distance, sigma=sigma) for distance in distances]
            rmse = _rmse(preds, observed)
            if rmse < best_rmse:
                best_rmse = rmse
                best = {"rmse": rmse, "sigma": float(sigma)}
    else:
        raise ValueError("method must be one of: power, exponential, gaussian")

    return best


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
) -> list[dict[str, float]]:
    """One-at-a-time sensitivity analysis around a baseline parameter set."""
    if variation_fraction <= 0:
        raise ValueError("variation_fraction must be greater than zero")

    baseline_value = float(model(**base_parameters))
    rows: list[dict[str, float]] = []

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
    "calibrate_decay_parameters",
    "compare_scenarios",
    "monte_carlo_interval",
    "normalize_units",
    "sensitivity_analysis",
]
