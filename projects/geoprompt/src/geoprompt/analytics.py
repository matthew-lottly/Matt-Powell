"""Extended analytics: alternative similarity, corridor variants, and filtering (items 71-80)."""

from __future__ import annotations

import math
from typing import Any, Sequence

from .equations import coordinate_distance, prompt_decay
from .geometry import Coordinate, Geometry, geometry_area, geometry_centroid


def jaccard_area_similarity(
    origin_area: float,
    destination_area: float,
    distance_value: float,
    scale: float = 1.0,
    power: float = 1.0,
) -> float:
    """Item 71: Jaccard-like area similarity: intersection / union estimate."""
    if origin_area == 0 and destination_area == 0:
        return prompt_decay(distance_value, scale, power)
    min_area = min(origin_area, destination_area)
    max_area = max(origin_area, destination_area)
    overlap_estimate = min_area
    union_estimate = origin_area + destination_area - overlap_estimate
    if union_estimate == 0:
        return 0.0
    return (overlap_estimate / union_estimate) * prompt_decay(distance_value, scale, power)


def overlap_ratio_similarity(
    origin_area: float,
    destination_area: float,
    distance_value: float,
    scale: float = 1.0,
    power: float = 1.0,
) -> float:
    """Item 71: Overlap ratio: min(a,b) / max(a,b) * decay."""
    if origin_area == 0 and destination_area == 0:
        return prompt_decay(distance_value, scale, power)
    return (min(origin_area, destination_area) / max(origin_area, destination_area)) * prompt_decay(distance_value, scale, power)


def directional_corridor_accessibility(
    weight: float,
    corridor_length: float,
    distance_value: float,
    bearing_alignment: float,
    scale: float = 1.0,
    power: float = 2.0,
) -> float:
    """Item 72: Corridor accessibility with directional bias."""
    if corridor_length < 0:
        raise ValueError("corridor_length must be zero or greater")
    corridor_factor = math.log1p(corridor_length)
    alignment_factor = max(0.0, bearing_alignment)
    decay = prompt_decay(distance_value, scale, power)
    return weight * corridor_factor * alignment_factor * decay


def anisotropic_distance(
    origin: Coordinate,
    destination: Coordinate,
    preferred_bearing: float,
    stretch_factor: float = 2.0,
) -> float:
    """Item 79: Anisotropic distance with directional stretching."""
    dx = destination[0] - origin[0]
    dy = destination[1] - origin[1]
    angle = math.radians(preferred_bearing)
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    rotated_x = dx * cos_a + dy * sin_a
    rotated_y = -dx * sin_a + dy * cos_a
    return math.sqrt((rotated_x / stretch_factor) ** 2 + rotated_y ** 2)


def filter_by_threshold(
    interactions: list[dict[str, Any]],
    metric_key: str,
    min_threshold: float,
) -> list[dict[str, Any]]:
    """Item 77: Threshold-based filtering of low-signal interactions."""
    return [item for item in interactions if float(item[metric_key]) >= min_threshold]


def filter_by_distance_cutoff(
    interactions: list[dict[str, Any]],
    distance_key: str = "distance",
    max_distance: float | None = None,
) -> list[dict[str, Any]]:
    """Item 78: Optional distance cutoff to limit noise."""
    if max_distance is None:
        return interactions
    return [item for item in interactions if float(item[distance_key]) <= max_distance]


def add_ranking_explanation(
    interactions: list[dict[str, Any]],
    metric_key: str,
) -> list[dict[str, Any]]:
    """Item 76: Add ranking explanation metadata for each top result."""
    if not interactions:
        return []
    max_val = max(float(item[metric_key]) for item in interactions)
    min_val = min(float(item[metric_key]) for item in interactions)
    result = []
    for rank, item in enumerate(interactions, start=1):
        enriched = dict(item)
        val = float(item[metric_key])
        enriched["rank"] = rank
        enriched["percentile"] = ((val - min_val) / (max_val - min_val) * 100) if max_val != min_val else 50.0
        enriched["rank_explanation"] = f"Rank {rank}: {metric_key}={val:.4f} ({enriched['percentile']:.1f}th percentile)"
        result.append(enriched)
    return result


def deterministic_tie_break(
    items: list[dict[str, Any]],
    metric_key: str,
    tie_break_key: str = "origin",
    reverse: bool = True,
) -> list[dict[str, Any]]:
    """Item 80: Deterministic tie-breaking with priority key."""
    return sorted(items, key=lambda x: (-float(x[metric_key]) if reverse else float(x[metric_key]), str(x.get(tie_break_key, ""))))


__all__ = [
    "add_ranking_explanation",
    "anisotropic_distance",
    "deterministic_tie_break",
    "directional_corridor_accessibility",
    "filter_by_distance_cutoff",
    "filter_by_threshold",
    "jaccard_area_similarity",
    "overlap_ratio_similarity",
]
