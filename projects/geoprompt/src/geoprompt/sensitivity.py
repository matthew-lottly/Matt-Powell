"""Sensitivity analysis and parameter sweep support (items 68-70)."""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Any, Callable, Sequence


@dataclass
class SweepResult:
    """Result of a single parameter combination in a sensitivity sweep."""
    parameters: dict[str, float]
    metric_values: list[float]
    metric_summary: dict[str, float] = field(default_factory=dict)


def parameter_sweep(
    compute_fn: Callable[..., list[float]],
    parameter_grid: dict[str, Sequence[float]],
    **fixed_kwargs: Any,
) -> list[SweepResult]:
    """Item 68: Run a sensitivity analysis by sweeping parameter combinations.

    Args:
        compute_fn: Function that returns a list of metric values.
        parameter_grid: Dict mapping parameter names to lists of values to try.
        **fixed_kwargs: Additional fixed keyword arguments to pass to compute_fn.

    Returns:
        List of SweepResult for each parameter combination.
    """
    param_names = list(parameter_grid.keys())
    param_values = list(parameter_grid.values())
    results: list[SweepResult] = []

    for combination in itertools.product(*param_values):
        params = dict(zip(param_names, combination, strict=True))
        merged = {**fixed_kwargs, **params}
        values = compute_fn(**merged)
        summary = _summarize_values(values)
        results.append(SweepResult(parameters=params, metric_values=values, metric_summary=summary))

    return results


def _summarize_values(values: list[float]) -> dict[str, float]:
    """Compute basic summary statistics for a list of values."""
    if not values:
        return {"count": 0, "mean": 0.0, "min": 0.0, "max": 0.0, "range": 0.0}
    n = len(values)
    mean = sum(values) / n
    return {
        "count": float(n),
        "mean": mean,
        "min": min(values),
        "max": max(values),
        "range": max(values) - min(values),
        "variance": sum((v - mean) ** 2 for v in values) / n,
    }


def confidence_score(interaction_value: float, max_value: float) -> float:
    """Item 70: Compute a confidence score for an interaction relative to the max."""
    if max_value <= 0:
        return 0.0
    return min(1.0, interaction_value / max_value)


def rank_with_confidence(interactions: list[dict[str, Any]], metric_key: str = "interaction") -> list[dict[str, Any]]:
    """Item 70: Annotate a ranked interaction list with confidence scores."""
    if not interactions:
        return []
    max_val = max(float(item[metric_key]) for item in interactions)
    result = []
    for rank, item in enumerate(interactions, start=1):
        enriched = dict(item)
        enriched["rank"] = rank
        enriched["confidence"] = confidence_score(float(item[metric_key]), max_val)
        result.append(enriched)
    return result


__all__ = [
    "SweepResult",
    "confidence_score",
    "parameter_sweep",
    "rank_with_confidence",
]
