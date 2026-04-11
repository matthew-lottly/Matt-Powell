"""Weight normalization strategies for geoprompt (items 64-66)."""

from __future__ import annotations

import math
from typing import Sequence

from .exceptions import ValidationError


def normalize_min_max(values: Sequence[float]) -> list[float]:
    """Min-max normalization to [0, 1]."""
    if not values:
        return []
    min_val = min(values)
    max_val = max(values)
    if min_val == max_val:
        return [0.5 for _ in values]
    return [(v - min_val) / (max_val - min_val) for v in values]


def normalize_z_score(values: Sequence[float]) -> list[float]:
    """Z-score standardization (mean=0, std=1)."""
    if not values:
        return []
    n = len(values)
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / n
    std = math.sqrt(variance) if variance > 0 else 1.0
    return [(v - mean) / std for v in values]


def normalize_robust(values: Sequence[float]) -> list[float]:
    """Item 65: Robust scaling using median and IQR for outlier-heavy inputs."""
    if not values:
        return []
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    median = sorted_vals[n // 2] if n % 2 else (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2
    q1_idx = n // 4
    q3_idx = 3 * n // 4
    q1 = sorted_vals[q1_idx]
    q3 = sorted_vals[q3_idx]
    iqr = q3 - q1
    if iqr == 0:
        return [0.0 for _ in values]
    return [(v - median) / iqr for v in values]


def apply_negative_weight_policy(values: Sequence[float], policy: str = "reject") -> list[float]:
    """Item 66: Handle negative weights based on policy."""
    result = list(values)
    if policy == "allow":
        return result
    for i, v in enumerate(result):
        if v < 0:
            if policy == "reject":
                raise ValidationError(f"Negative weight at index {i}: {v}. Set negative_weight_policy='clip' or 'allow'.")
            elif policy == "clip":
                result[i] = 0.0
    return result


NORMALIZATION_METHODS = {
    "none": lambda values: list(values),
    "min_max": normalize_min_max,
    "z_score": normalize_z_score,
    "robust": normalize_robust,
}


def normalize(values: Sequence[float], method: str = "none") -> list[float]:
    """Apply a named normalization strategy."""
    if method not in NORMALIZATION_METHODS:
        raise ValidationError(f"Unknown normalization method: '{method}'. Available: {list(NORMALIZATION_METHODS)}")
    return NORMALIZATION_METHODS[method](values)


__all__ = [
    "NORMALIZATION_METHODS",
    "apply_negative_weight_policy",
    "normalize",
    "normalize_min_max",
    "normalize_robust",
    "normalize_z_score",
]
