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


def coordinate_distance(origin: Coordinate, destination: Coordinate, method: DistanceMethod | str = "euclidean") -> float:
    normalized_method = method.lower().replace("-", "_")
    if normalized_method == "euclidean":
        return euclidean_distance(origin, destination)
    if normalized_method == "haversine":
        return haversine_distance(origin, destination)
    raise ValueError(f"unsupported distance method: {method}")


def prompt_decay(distance_value: float, scale: float = 1.0, power: float = 2.0) -> float:
    if distance_value < 0:
        raise ValueError("distance_value must be zero or greater")
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
    """Shannon entropy (natural log) for a list of proportions.

    Proportions should sum to ~1.  Zero or negative entries are skipped.
    """
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


def clamp(value: float, lo: float, hi: float) -> float:
    """Clamp *value* to the closed interval [lo, hi]."""
    return max(lo, min(hi, value))


def min_max_scale(value: float, min_val: float, max_val: float) -> float:
    """Linearly scale *value* using observed min/max. Returns 0 when range is zero."""
    rng = max_val - min_val
    if rng <= 0:
        return 0.0
    return (value - min_val) / rng


def thin_plate_spline_basis(r: float) -> float:
    """Thin-plate spline radial basis: r^2 * ln(r), returning 0 when r ~ 0."""
    if r <= 1e-12:
        return 0.0
    return r * r * math.log(r)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two equal-length vectors.  Returns 0 on zero-norm."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    denom = norm_a * norm_b
    if denom < 1e-15:
        return 0.0
    return dot / denom


def manhattan_distance_2d(origin: Coordinate, destination: Coordinate) -> float:
    """Manhattan (L1) distance between two 2-D coordinates."""
    return abs(destination[0] - origin[0]) + abs(destination[1] - origin[1])


def linear_interpolate(a: float, b: float, t: float) -> float:
    """Linear interpolation: (1 - t) * a + t * b."""
    return (1.0 - t) * a + t * b


def log_likelihood_ratio(observed: float, expected: float) -> float:
    """Single-term log-likelihood ratio: observed * ln(observed / expected).

    Returns 0 when *observed* is zero or *expected* is non-positive.
    """
    if observed <= 0 or expected <= 0:
        return 0.0
    return observed * math.log(observed / expected)


def variogram_spherical(h: float, nugget: float, sill: float, range_param: float) -> float:
    """Spherical variogram model γ(h) = nugget + sill * [1.5(h/a) - 0.5(h/a)^3] for h <= a."""
    if h <= 0:
        return 0.0
    if range_param <= 0:
        return nugget + sill
    if h >= range_param:
        return nugget + sill
    ratio = h / range_param
    return nugget + sill * (1.5 * ratio - 0.5 * ratio ** 3)


def variogram_exponential(h: float, nugget: float, sill: float, range_param: float) -> float:
    """Exponential variogram model γ(h) = nugget + sill * [1 - exp(-3h/a)]."""
    if h <= 0:
        return 0.0
    if range_param <= 0:
        return nugget + sill
    return nugget + sill * (1.0 - math.exp(-3.0 * h / range_param))


def variogram_gaussian_model(h: float, nugget: float, sill: float, range_param: float) -> float:
    """Gaussian variogram model γ(h) = nugget + sill * [1 - exp(-3(h/a)^2)]."""
    if h <= 0:
        return 0.0
    if range_param <= 0:
        return nugget + sill
    return nugget + sill * (1.0 - math.exp(-3.0 * (h / range_param) ** 2))


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
    if friction <= 0:
        raise ValueError("friction must be greater than zero")
    effective_distance = max(distance_value, min_distance)
    if effective_distance == 0:
        return float("inf") if origin_weight > 0 and destination_weight > 0 else 0.0
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
    "clamp",
    "coordinate_distance",
    "corridor_strength",
    "cosine_similarity",
    "directional_alignment",
    "directional_bearing",
    "euclidean_distance",
    "exponential_kernel",
    "gaussian_kernel",
    "gravity_model",
    "haversine_distance",
    "inverse_distance_weight",
    "linear_interpolate",
    "log_likelihood_ratio",
    "manhattan_distance_2d",
    "min_max_scale",
    "prompt_decay",
    "prompt_influence",
    "prompt_interaction",
    "row_normalize",
    "semivariance",
    "shannon_entropy",
    "sigmoid",
    "thin_plate_spline_basis",
    "variogram_exponential",
    "variogram_gaussian_model",
    "variogram_spherical",
]