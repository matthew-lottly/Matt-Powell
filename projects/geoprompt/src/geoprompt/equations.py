from __future__ import annotations

import math
from typing import Literal


Coordinate = tuple[float, float]
DistanceMethod = Literal["euclidean", "haversine"]


EARTH_RADIUS_KM = 6371.0088


def euclidean_distance(origin: Coordinate, destination: Coordinate) -> float:
    dx = destination[0] - origin[0]
    dy = destination[1] - origin[1]
    return math.hypot(dx, dy)


def haversine_distance(origin: Coordinate, destination: Coordinate, radius_km: float = EARTH_RADIUS_KM) -> float:
    if radius_km <= 0:
        raise ValueError("radius_km must be greater than zero")

    origin_lon = math.radians(origin[0])
    origin_lat = math.radians(origin[1])
    destination_lon = math.radians(destination[0])
    destination_lat = math.radians(destination[1])

    delta_lon = destination_lon - origin_lon
    delta_lat = destination_lat - origin_lat
    half_chord = (
        math.sin(delta_lat / 2.0) ** 2
        + math.cos(origin_lat) * math.cos(destination_lat) * math.sin(delta_lon / 2.0) ** 2
    )
    angular_distance = 2.0 * math.atan2(math.sqrt(half_chord), math.sqrt(1.0 - half_chord))
    return radius_km * angular_distance


def coordinate_distance(origin: Coordinate, destination: Coordinate, method: DistanceMethod = "euclidean") -> float:
    if method == "euclidean":
        return euclidean_distance(origin, destination)
    if method == "haversine":
        return haversine_distance(origin, destination)
    raise ValueError(f"unsupported distance method: {method}")


def prompt_decay(distance_value: float, scale: float = 1.0, power: float = 2.0) -> float:
    if scale <= 0:
        raise ValueError("scale must be greater than zero")
    if power <= 0:
        raise ValueError("power must be greater than zero")
    return 1.0 / math.pow(1.0 + (distance_value / scale), power)


def prompt_influence(weight: float, distance_value: float, scale: float = 1.0, power: float = 2.0) -> float:
    return float(weight) * prompt_decay(distance_value=distance_value, scale=scale, power=power)


def prompt_interaction(
    origin_weight: float,
    destination_weight: float,
    distance_value: float,
    scale: float = 1.0,
    power: float = 2.0,
) -> float:
    return float(origin_weight) * float(destination_weight) * prompt_decay(
        distance_value=distance_value,
        scale=scale,
        power=power,
    )


def inverse_distance_weight(
    distance_value: float,
    power: float = 1.0,
    min_distance: float = 1e-12,
    offset: float = 0.0,
) -> float:
    if distance_value < 0:
        raise ValueError("distance_value must be zero or greater")
    if power <= 0:
        raise ValueError("power must be greater than zero")
    if min_distance < 0:
        raise ValueError("min_distance must be zero or greater")
    if offset < 0:
        raise ValueError("offset must be zero or greater")
    effective_distance = max(distance_value, min_distance) + offset
    return 1.0 / math.pow(effective_distance, power)


def gaussian_kernel(distance_value: float, bandwidth: float = 1.0) -> float:
    if distance_value < 0:
        raise ValueError("distance_value must be zero or greater")
    if bandwidth <= 0:
        raise ValueError("bandwidth must be greater than zero")
    return math.exp(-0.5 * math.pow(distance_value / bandwidth, 2))


def exponential_kernel(distance_value: float, scale: float = 1.0) -> float:
    if distance_value < 0:
        raise ValueError("distance_value must be zero or greater")
    if scale <= 0:
        raise ValueError("scale must be greater than zero")
    return math.exp(-distance_value / scale)


def sigmoid(x: float) -> float:
    """Standard logistic sigmoid: 1 / (1 + exp(-x)), clamped to avoid overflow."""
    x_clamped = max(-500.0, min(500.0, x))
    return 1.0 / (1.0 + math.exp(-x_clamped))


def semivariance(value_a: float, value_b: float) -> float:
    """Classical semivariance between two observations: 0.5 * (a - b)^2."""
    return 0.5 * (value_a - value_b) ** 2


def shannon_entropy(proportions: list[float]) -> float:
    """Shannon entropy (natural log) for a list of proportions that sum to ~1."""
    total = 0.0
    for p in proportions:
        if p > 0:
            total -= p * math.log(p)
    return total


def row_normalize(values: list[float]) -> list[float]:
    """Normalize a list so its elements sum to 1. Returns zeros if sum is 0."""
    total = sum(values)
    if total == 0:
        return [0.0] * len(values)
    return [v / total for v in values]


def corridor_strength(
    weight: float,
    corridor_length: float,
    distance_value: float,
    scale: float = 1.0,
    power: float = 2.0,
) -> float:
    if corridor_length < 0:
        raise ValueError("corridor_length must be zero or greater")
    corridor_factor = math.log1p(corridor_length)
    return float(weight) * corridor_factor * prompt_decay(distance_value=distance_value, scale=scale, power=power)


def area_similarity(
    origin_area: float,
    destination_area: float,
    distance_value: float,
    scale: float = 1.0,
    power: float = 1.0,
) -> float:
    if origin_area < 0 or destination_area < 0:
        raise ValueError("areas must be zero or greater")
    if origin_area == 0 and destination_area == 0:
        size_ratio = 1.0
    else:
        size_ratio = min(origin_area, destination_area) / max(origin_area, destination_area)
    return size_ratio * prompt_decay(distance_value=distance_value, scale=scale, power=power)


def directional_bearing(origin: Coordinate, destination: Coordinate) -> float:
    dx = destination[0] - origin[0]
    dy = destination[1] - origin[1]
    bearing = math.degrees(math.atan2(dx, dy))
    return (bearing + 360.0) % 360.0


def directional_alignment(origin: Coordinate, destination: Coordinate, preferred_bearing: float) -> float:
    observed_bearing = directional_bearing(origin=origin, destination=destination)
    delta = math.radians(observed_bearing - preferred_bearing)
    return math.cos(delta)


def gravity_model(
    origin_weight: float,
    destination_weight: float,
    distance_value: float,
    friction: float = 2.0,
    min_distance: float = 0.0,
) -> float:
    if distance_value < 0:
        raise ValueError("distance_value must be zero or greater")
    effective_distance = max(distance_value, min_distance)
    if effective_distance == 0:
        return float("inf") if origin_weight > 0 and destination_weight > 0 else 0.0
    if friction <= 0:
        raise ValueError("friction must be greater than zero")
    return float(origin_weight) * float(destination_weight) / math.pow(effective_distance, friction)


def accessibility_index(
    weights: list[float],
    distances: list[float],
    friction: float = 2.0,
    min_distance: float = 0.0,
) -> float:
    if len(weights) != len(distances):
        raise ValueError("weights and distances must have the same length")
    if friction <= 0:
        raise ValueError("friction must be greater than zero")
    total = 0.0
    for weight, distance_value in zip(weights, distances, strict=True):
        if distance_value < 0:
            raise ValueError("distances must be zero or greater")
        effective_distance = max(distance_value, min_distance)
        if effective_distance == 0:
            if float(weight) > 0:
                return float("inf")
            continue
        else:
            total += float(weight) / math.pow(effective_distance, friction)
    return total


__all__ = [
    "Coordinate",
    "DistanceMethod",
    "EARTH_RADIUS_KM",
    "accessibility_index",
    "area_similarity",
    "coordinate_distance",
    "corridor_strength",
    "directional_alignment",
    "directional_bearing",
    "euclidean_distance",
    "exponential_kernel",
    "gaussian_kernel",
    "gravity_model",
    "haversine_distance",
    "inverse_distance_weight",
    "prompt_decay",
    "prompt_influence",
    "prompt_interaction",
    "row_normalize",
    "semivariance",
    "shannon_entropy",
    "sigmoid",
]